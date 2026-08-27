"""
ویوهای کانفیگ اپلیکیشن
  GET /api/v1/config/app-version/
  GET /api/v1/config/maintenance-status/

بدون احراز هویت — هر کسی می‌تواند بخواند.
"""
from rest_framework import permissions
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.core.models import AppConfig


class AppVersionView(APIView, StandardResponseMixin):
    """اطلاعات نسخه اپلیکیشن"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Config'],
        summary='اطلاعات نسخه اپلیکیشن',
        description='نسخه فعلی، حداقل نسخه مورد نیاز، آپدیت اجباری و تغییرات نسخه',
    )
    def get(self, request):
        config = AppConfig.objects.first()

        if not config:
            # مقادیر پیش‌فرض وقتی رکوردی وجود ندارد
            return self.success_response(
                data={
                    'latest_version': '1.0.0',
                    'min_required_version': '1.0.0',
                    'is_force_update': False,
                    'title': 'نسخه جدید بیو کلاب منتشر شد!',
                    'update_message': 'برای تجربه بهتر، لطفاً به آخرین نسخه به‌روزرسانی کنید.',
                    'changelog': [],
                    'store_url': 'https://beauclub.ir',
                    'store_name': 'بیو کلاب وب',
                }
            )

        return self.success_response(
            data={
                'latest_version': config.latest_version,
                'min_required_version': config.min_required_version,
                'is_force_update': config.is_force_update,
                'title': config.update_title,
                'update_message': config.update_message,
                'changelog': config.changelog or [],
                'store_url': config.store_url,
                'store_name': config.store_name,
            }
        )


class MaintenanceStatusView(APIView, StandardResponseMixin):
    """وضعیت تعمیرات"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Config'],
        summary='وضعیت تعمیرات',
        description='آیا اپلیکیشن در حالت تعمیرات است یا خیر',
    )
    def get(self, request):
        config = AppConfig.objects.first()

        if not config or not config.is_maintenance:
            return self.success_response(
                data={
                    'is_maintenance': False,
                    'title': '',
                    'message': '',
                    'estimated_end': '',
                    'reason': '',
                    'support_phone': '',
                }
            )

        return self.success_response(
            data={
                'is_maintenance': config.is_maintenance,
                'title': config.maintenance_title,
                'message': config.maintenance_message,
                'estimated_end': config.maintenance_estimated_end,
                'reason': config.maintenance_reason,
                'support_phone': config.support_phone,
            }
        )