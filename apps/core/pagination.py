"""
Pagination classes استاندارد برای DRF
"""
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """Pagination استاندارد - پیش‌فرض ۲۰ آیتم"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'pagination': {
                'count': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'results': data,
        })


class SmallResultsSetPagination(PageNumberPagination):
    """برای لیست‌های کوچک - ۱۰ آیتم"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class LargeResultsSetPagination(PageNumberPagination):
    """برای لیست‌های بزرگ - ۵۰ آیتم"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class FlexibleLimitOffsetPagination(LimitOffsetPagination):
    """Limit/Offset pagination"""
    default_limit = 20
    max_limit = 200

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'pagination': {
                'count': self.count,
                'limit': self.limit,
                'offset': self.offset,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'results': data,
        })