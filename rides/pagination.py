from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class RidePagination(PageNumberPagination):
    page_size = getattr(settings, "REST_FRAMEWORK", {}).get("PAGE_SIZE", 20)
    page_size_query_param = "page_size"
    max_page_size = 100
