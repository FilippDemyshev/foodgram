from rest_framework.pagination import PageNumberPagination


class FoodgramPageNumberPagination(PageNumberPagination):
    """Пагинация для Foodgram с поддержкой параметров limit и page."""
    page_size_query_param = 'limit'
    page_query_param = 'page'
