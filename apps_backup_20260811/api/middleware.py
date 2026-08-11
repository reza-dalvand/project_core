"""
Middleware های سفارشی
"""
import logging
from django.utils import timezone
from apps.core.utils import get_client_ip

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """لاگ‌گیری تمام درخواست‌های API"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = timezone.now()
        ip = get_client_ip(request)

        # فقط API ها را لاگ کن
        if request.path.startswith('/api/'):
            logger.info(
                f"[API] {request.method} {request.path} | IP: {ip} | "
                f"User: {getattr(request.user, 'phone', 'anon')}"
            )

        response = self.get_response(request)

        if request.path.startswith('/api/'):
            duration = (timezone.now() - start_time).total_seconds()
            logger.info(
                f"[API] {request.method} {request.path} | "
                f"Status: {response.status_code} | Duration: {duration:.3f}s"
            )

        return response


class DeviceInfoMiddleware:
    """استخراج اطلاعات دستگاه و اضافه کردن به request"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from apps.core.utils import get_device_info
        request.device_info = get_device_info(request)
        request.client_ip = get_client_ip(request)
        return self.get_response(request)