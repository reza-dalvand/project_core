"""
Mixin های مشترک برای View ها
"""
from rest_framework.response import Response


class StandardResponseMixin:
    """Mixin برای ایجاد response استاندارد"""

    def success_response(self, data=None, message=None, status=200, meta=None):
        response_data = {
            'success': True,
            'data': data,
        }
        if message:
            response_data['message'] = message
        if meta:
            response_data['meta'] = meta
        return Response(response_data, status=status)

    def error_response(self, message, code='ERROR', details=None, status=400):
        return Response(
            {
                'success': False,
                'error': {
                    'code': code,
                    'message': message,
                    'details': details or {},
                }
            },
            status=status,
        )