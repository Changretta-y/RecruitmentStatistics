from django.core.paginator import InvalidPage, Page
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError


class JobApplicationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    allowed_page_sizes = frozenset({10, 20, 50, 100})

    def _validation_error(self, field, message):
        raise ValidationError(
            {
                "code": "VALIDATION_ERROR",
                "details": {field: [message]},
            }
        )

    def get_page_size(self, request):
        raw_page_size = request.query_params.get(self.page_size_query_param)
        if raw_page_size is None:
            return self.page_size

        try:
            page_size = int(raw_page_size)
        except (TypeError, ValueError):
            self._validation_error(
                "page_size",
                "page_size must be one of 10, 20, 50, or 100.",
            )

        if page_size not in self.allowed_page_sizes:
            self._validation_error(
                "page_size",
                "page_size must be one of 10, 20, 50, or 100.",
            )
        return page_size

    def paginate_queryset(self, queryset, request, view=None):
        page_size = self.get_page_size(request)
        if page_size is None:
            return None

        self.request = request
        paginator = self.django_paginator_class(queryset, page_size)
        raw_page = request.query_params.get(self.page_query_param, "1")
        try:
            page_number = int(raw_page)
        except (TypeError, ValueError):
            self._validation_error("page", "page must be an integer greater than or equal to 1.")
        if page_number < 1:
            self._validation_error("page", "page must be an integer greater than or equal to 1.")

        try:
            self.page = paginator.page(page_number)
        except InvalidPage:
            self.page = Page([], page_number, paginator)

        return list(self.page)

    def get_paginated_response(self, data):
        total = self.page.paginator.count
        return Response(
            {
                "count": total,
                "page": self.page.number,
                "page_size": self.page.paginator.per_page,
                "total_pages": self.page.paginator.num_pages if total else 0,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
