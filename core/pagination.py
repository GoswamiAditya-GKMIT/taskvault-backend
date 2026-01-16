from rest_framework.pagination import PageNumberPagination
from core.constants import pagination_page_size
class DefaultPagination(PageNumberPagination):
    page_size = pagination_page_size

    def get_root_pagination_data(self):
        return {
            "total_count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "page": self.page.number,
        }

