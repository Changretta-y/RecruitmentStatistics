from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PromptPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        total = self.page.paginator.count
        return Response({
            "count": total,
            "page": self.page.number,
            "page_size": self.page.paginator.per_page,
            "total_pages": self.page.paginator.num_pages if total else 0,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })
