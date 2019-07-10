from rest_framework.pagination import PageNumberPagination


class PNPagination(PageNumberPagination):
    page_size = 10
    page_query_param = 'page'
    page_size_query_param = "page_size"