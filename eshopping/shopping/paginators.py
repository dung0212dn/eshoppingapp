from requests import Response
from rest_framework import pagination


class ProductsPagination(pagination.PageNumberPagination):
    page_size = 20


class CommentPagination(pagination.PageNumberPagination):
    page_size = 10  # Số lượng comment trên mỗi trang


