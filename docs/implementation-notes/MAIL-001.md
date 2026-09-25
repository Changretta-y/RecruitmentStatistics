# MAIL-001 实现说明

- 状态：`READY_FOR_TEST`
- 修改范围：新增 `backend/apps/notifications/`（模型、API、迁移）；更新 `backend/config/settings.py` 与 `backend/config/urls.py`；新增本说明。
- 已实现行为：认证用户可读取和修改自己的邮箱、北京时间发送时刻及开关；默认设置关闭且邮箱未验证。仅严格 `HH:mm` 时间和合法邮箱可保存。启用时要求当前地址已验证且发送时间完整。修改邮箱会清除验证状态、关闭推送并停用旧验证令牌。
- 验证处理：申请接口发送 24 小时有效的链接令牌，数据库仅保存 SHA-256 摘要；令牌绑定用户和地址、成功后一次性消费。相同用户和地址一小时最多生成三次申请记录，包含发送失败的尝试。无收件邮箱返回字段错误，限流返回 `429`，SMTP 主机为空或邮件后端发送失败时返回通用 `503`，不改变地址验证状态，也不向响应或日志回显令牌和凭据。
- 数据库迁移：新增 `notifications.0001_initial`，创建一对一用户通知设置表和验证令牌表；不修改投递记录及 APP-008 迁移。
- 配置变化：通过 `EMAIL_HOST`、`EMAIL_PORT`、`EMAIL_HOST_USER`、`EMAIL_HOST_PASSWORD`、`EMAIL_USE_TLS`、`EMAIL_USE_SSL`、`DEFAULT_FROM_EMAIL` 配置平台 SMTP；`EMAIL_HOST` 默认为 Django 本地开发约定的 `localhost`，显式空值会关闭发送。部署环境需设置平台 SMTP 主机、凭据、加密方式和发件地址。`FRONTEND_BASE_URL` 可设置验证页面的站点前缀；邮件链接路径为 `/notification-settings/verify?token=...`。
- 已知限制：`last_delivery` 暂返回 `null`，由 MAIL-002 的每日发送功能产生记录后接入；实际 SMTP 可用性取决于部署环境配置。
- 自检结果：Windows；Python 3.11.13；uv 0.7.21。使用 MAIL 专用本机 PostgreSQL 测试数据库、临时 `SECRET_KEY`，邮件均由测试后端替身接管，未连接真实 SMTP。`uv run --group test pytest tests/test_mail_001.py --tb=no -q`：9 passed；`uv run --group test python manage.py check`：通过；`uv run --group test python manage.py makemigrations --check --dry-run`：无模型/迁移差异。
- 建议复测命令：在 `backend/` 中配置独立 PostgreSQL `DATABASE_URL`、临时 `SECRET_KEY` 后运行 `uv run --group test pytest tests/test_mail_001.py --tb=no -q`。
- 测试完整性声明：未修改测试、断言或质量门槛；上述运行只用于实现自检，独立复测由测试 Agent 完成。
