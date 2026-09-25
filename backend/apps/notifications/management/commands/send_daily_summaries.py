"""Send verified users their current Beijing-day schedule summary."""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from backend.apps.applications.models import JobApplication

from ...models import DailyDelivery, NotificationSettings


logger = logging.getLogger(__name__)
BEIJING = ZoneInfo("Asia/Shanghai")
MAX_STAGE_DURATION = timedelta(minutes=1440)
RETRY_DELAY = timedelta(minutes=5)
MAX_ATTEMPTS = 4  # First delivery plus at most three retries.
SENDING_LEASE = timedelta(minutes=30)
STAGES = (
    ("ai_interview_time", "ai_interview_duration_minutes", "AI 面"),
    ("written_test_time", "written_test_duration_minutes", "笔试"),
    ("first_interview_time", "first_interview_duration_minutes", "一面"),
    ("second_interview_time", "second_interview_duration_minutes", "二面"),
    ("third_interview_time", "third_interview_duration_minutes", "三面"),
    ("hr_interview_time", "hr_interview_duration_minutes", "HR 面"),
)


class Command(BaseCommand):
    help = "发送到期用户的北京时间当日安排摘要邮件。"

    def handle(self, *args, **options):
        now = timezone.now()
        local_now = timezone.localtime(now, BEIJING)
        today = local_now.date()
        counts = {
            "accepted": 0,
            "failed_retryable": 0,
            "failed": 0,
            "unknown": 0,
            "skipped": 0,
        }

        self._expire_previous_days(today)
        has_mail_config = bool(
            settings.EMAIL_HOST.strip() and settings.DEFAULT_FROM_EMAIL.strip()
        )
        if not has_mail_config:
            logger.error("daily summary SMTP/email configuration is missing")

        due_settings = NotificationSettings.objects.filter(
            enabled=True,
            verified=True,
            daily_time__isnull=False,
        ).select_related("user")

        for notification_settings in due_settings.iterator():
            try:
                scheduled_at = timezone.make_aware(
                    datetime.combine(today, notification_settings.daily_time), BEIJING
                )
                existing = DailyDelivery.objects.filter(
                    notification_settings=notification_settings,
                    delivery_date=today,
                ).first()

                if existing is None:
                    # A setting first enabled or changed after its chosen time
                    # takes effect the following day, even during a delayed run.
                    if now < scheduled_at or notification_settings.updated_at > scheduled_at:
                        counts["skipped"] += 1
                        continue
                    delivery = self._create_daily_claim(notification_settings, today)
                    if delivery is None:
                        counts["skipped"] += 1
                        continue
                else:
                    delivery = existing

                if delivery.status == DailyDelivery.Status.SENDING:
                    if now - delivery.updated_at >= SENDING_LEASE:
                        self._update_delivery(
                            delivery.pk,
                            status=DailyDelivery.Status.UNKNOWN,
                            error_category="stale_sending_claim",
                        )
                        counts["unknown"] += 1
                        logger.warning(
                            "daily summary outcome unknown after stale claim date=%s user_id=%s",
                            today.isoformat(),
                            notification_settings.user_id,
                        )
                    else:
                        counts["skipped"] += 1
                    continue

                if delivery.status in {
                    DailyDelivery.Status.ACCEPTED,
                    DailyDelivery.Status.FAILED,
                    DailyDelivery.Status.UNKNOWN,
                }:
                    counts["skipped"] += 1
                    continue

                if delivery.status == DailyDelivery.Status.FAILED_RETRYABLE:
                    if delivery.next_attempt_at is None or now < delivery.next_attempt_at:
                        counts["skipped"] += 1
                        continue

                if not has_mail_config:
                    self._update_delivery(
                        delivery.pk,
                        status=DailyDelivery.Status.FAILED,
                        error_category="mail_configuration_missing",
                        next_attempt_at=None,
                    )
                    counts["failed"] += 1
                    logger.error(
                        "daily summary not sent: mail configuration missing date=%s user_id=%s",
                        today.isoformat(),
                        notification_settings.user_id,
                    )
                    continue

                claimed = self._claim_for_attempt(delivery.pk, now, today)
                if claimed is None:
                    counts["skipped"] += 1
                    continue

                attempt_number = claimed.attempt_count
                try:
                    message = self._build_message(notification_settings, today)
                    sent = message.send(fail_silently=False)
                except (smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError) as exc:
                    self._record_explicit_refusal(claimed.pk, attempt_number, now, today, exc)
                    current = DailyDelivery.objects.get(pk=claimed.pk)
                    counts[current.status] += 1
                    logger.warning(
                        "daily summary SMTP refusal date=%s user_id=%s status=%s category=%s",
                        today.isoformat(),
                        notification_settings.user_id,
                        current.status,
                        type(exc).__name__,
                    )
                except Exception as exc:  # noqa: BLE001 - transport outcomes may be ambiguous.
                    self._update_delivery(
                        claimed.pk,
                        status=DailyDelivery.Status.UNKNOWN,
                        error_category=type(exc).__name__[:64],
                        next_attempt_at=None,
                    )
                    counts["unknown"] += 1
                    logger.warning(
                        "daily summary transport result unknown date=%s user_id=%s category=%s",
                        today.isoformat(),
                        notification_settings.user_id,
                        type(exc).__name__,
                    )
                else:
                    if sent == 1:
                        self._update_delivery(
                            claimed.pk,
                            status=DailyDelivery.Status.ACCEPTED,
                            error_category="",
                            next_attempt_at=None,
                        )
                        counts["accepted"] += 1
                        logger.info(
                            "daily summary accepted by mail server date=%s user_id=%s",
                            today.isoformat(),
                            notification_settings.user_id,
                        )
                    else:
                        # A transport returning an unexpected count does not
                        # prove whether any recipient accepted the message.
                        self._update_delivery(
                            claimed.pk,
                            status=DailyDelivery.Status.UNKNOWN,
                            error_category="unexpected_transport_result",
                            next_attempt_at=None,
                        )
                        counts["unknown"] += 1
                        logger.warning(
                            "daily summary transport result unknown date=%s user_id=%s category=unexpected_result",
                            today.isoformat(),
                            notification_settings.user_id,
                        )
            except Exception as exc:  # One user's data or database issue must not stop later users.
                counts["failed"] += 1
                logger.error(
                    "daily summary processing failed date=%s user_id=%s category=%s",
                    today.isoformat(),
                    notification_settings.user_id,
                    type(exc).__name__,
                )

        summary = " ".join(f"{name}={count}" for name, count in counts.items())
        self.stdout.write(f"daily summaries date={today.isoformat()} {summary}")

    @staticmethod
    def _create_daily_claim(notification_settings, delivery_date):
        try:
            with transaction.atomic():
                delivery, created = DailyDelivery.objects.get_or_create(
                    notification_settings=notification_settings,
                    delivery_date=delivery_date,
                    defaults={"status": DailyDelivery.Status.PENDING},
                )
                return delivery if created or delivery.status == DailyDelivery.Status.PENDING else None
        except IntegrityError:
            # Another command created the unique user/day row at the same time.
            return None

    @staticmethod
    def _claim_for_attempt(delivery_id, now, delivery_date):
        local_end = timezone.make_aware(
            datetime.combine(delivery_date, time(23, 59, 59)), BEIJING
        )
        if now > local_end:
            DailyDelivery.objects.filter(pk=delivery_id).update(
                status=DailyDelivery.Status.FAILED,
                next_attempt_at=None,
                error_category="beijing_day_ended",
                updated_at=now,
            )
            return None

        with transaction.atomic():
            delivery = DailyDelivery.objects.select_for_update().get(pk=delivery_id)
            if delivery.status == DailyDelivery.Status.SENDING:
                return None
            if delivery.status == DailyDelivery.Status.FAILED_RETRYABLE:
                if delivery.next_attempt_at is None or now < delivery.next_attempt_at:
                    return None
            elif delivery.status != DailyDelivery.Status.PENDING:
                return None
            if delivery.attempt_count >= MAX_ATTEMPTS:
                delivery.status = DailyDelivery.Status.FAILED
                delivery.next_attempt_at = None
                delivery.error_category = "retry_limit_reached"
                delivery.save(update_fields=("status", "next_attempt_at", "error_category", "updated_at"))
                return None
            delivery.attempt_count += 1
            delivery.status = DailyDelivery.Status.SENDING
            delivery.next_attempt_at = None
            delivery.error_category = ""
            delivery.save(
                update_fields=("attempt_count", "status", "next_attempt_at", "error_category", "updated_at")
            )
            return delivery

    @staticmethod
    def _record_explicit_refusal(delivery_id, attempt_number, now, delivery_date, exc):
        end_of_day = timezone.make_aware(
            datetime.combine(delivery_date, time(23, 59, 59)), BEIJING
        )
        next_attempt = now + RETRY_DELAY
        retry_allowed = attempt_number < MAX_ATTEMPTS and next_attempt <= end_of_day
        DailyDelivery.objects.filter(pk=delivery_id).update(
            status=(
                DailyDelivery.Status.FAILED_RETRYABLE
                if retry_allowed
                else DailyDelivery.Status.FAILED
            ),
            next_attempt_at=next_attempt if retry_allowed else None,
            error_category=type(exc).__name__[:64],
            updated_at=now,
        )

    @staticmethod
    def _update_delivery(delivery_id, **fields):
        fields.setdefault("updated_at", timezone.now())
        DailyDelivery.objects.filter(pk=delivery_id).update(**fields)

    @staticmethod
    def _expire_previous_days(today):
        old_pending = DailyDelivery.objects.filter(
            delivery_date__lt=today,
            status__in=(DailyDelivery.Status.PENDING, DailyDelivery.Status.FAILED_RETRYABLE),
        )
        old_pending.update(
            status=DailyDelivery.Status.FAILED,
            next_attempt_at=None,
            error_category="beijing_day_ended",
            updated_at=timezone.now(),
        )
        # A process may have stopped while submitting to SMTP. Its outcome is
        # not known, so never retry it on another day.
        DailyDelivery.objects.filter(
            delivery_date__lt=today,
            status=DailyDelivery.Status.SENDING,
        ).update(
            status=DailyDelivery.Status.UNKNOWN,
            next_attempt_at=None,
            error_category="stale_sending_claim",
            updated_at=timezone.now(),
        )

    @staticmethod
    def _build_message(notification_settings, delivery_date):
        day_start = timezone.make_aware(
            datetime.combine(delivery_date, time.min), BEIJING
        )
        day_end = timezone.make_aware(
            datetime.combine(delivery_date + timedelta(days=1), time.min), BEIJING
        )
        possible_start = day_start - MAX_STAGE_DURATION
        candidates = Q()
        for time_field, duration_field, _label in STAGES:
            candidates |= Q(
                **{
                    f"{time_field}__gt": possible_start,
                    f"{time_field}__lt": day_end,
                    f"{duration_field}__isnull": False,
                }
            )
        applications = (
            JobApplication.objects.filter(user=notification_settings.user)
            .filter(candidates)
            .only(
                "id",
                "company_name",
                "position_name",
                *(field for time_field, duration_field, _label in STAGES for field in (time_field, duration_field)),
            )
        )

        events = []
        for application in applications:
            for time_field, duration_field, label in STAGES:
                start_at = getattr(application, time_field)
                duration_minutes = getattr(application, duration_field)
                if start_at is None or duration_minutes is None:
                    continue
                end_at = start_at + timedelta(minutes=duration_minutes)
                if start_at < day_end and end_at > day_start:
                    events.append(
                        {
                            "start": start_at,
                            "end": end_at,
                            "application_id": application.pk,
                            "company": application.company_name,
                            "position": application.position_name,
                            "stage": label,
                        }
                    )
        stage_order = {label: index for index, (_time, _duration, label) in enumerate(STAGES)}
        events.sort(
            key=lambda event: (
                event["start"],
                event["application_id"],
                stage_order[event["stage"]],
            )
        )

        lines = [
            f"{delivery_date.isoformat()} 当日安排（北京时间 / Asia/Shanghai）",
            "",
        ]
        if not events:
            lines.append("今日无安排")
        else:
            for event in events:
                local_start = timezone.localtime(event["start"], BEIJING)
                local_end = timezone.localtime(event["end"], BEIJING)
                lines.append(
                    f"{local_start:%Y-%m-%d %H:%M}–{local_end:%Y-%m-%d %H:%M}  "
                    f"{event['stage']}｜{event['company']}｜{event['position']}"
                )

        return EmailMessage(
            subject=f"校招进度管理系统：{delivery_date.isoformat()} 今日安排",
            body="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[notification_settings.recipient_email],
        )
