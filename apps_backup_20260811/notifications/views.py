"""
Views برای نوتیفیکیشن‌ها - نسخه اصلاح شده
✅ import ها به ابتدای فایل منتقل شدند
"""
from django.db import models
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.core.pagination import StandardResultsSetPagination
from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationCountSerializer,
    MarkAsReadSerializer,
)
from .services import NotificationService


class NotificationListView(ListAPIView, StandardResponseMixin):
    """لیست اعلان‌های کاربر"""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='is_read',
                type=bool,
                required=False,
                description='فیلتر خوانده/نخوانده',
            ),
            OpenApiParameter(
                name='type',
                type=str,
                required=False,
                description='فیلتر نوع اعلان',
            ),
        ],
        tags=['Notifications'],
        summary='لیست اعلان‌ها',
    )
    def get_queryset(self):
        qs = Notification.objects.filter(
            user=self.request.user,
        ).order_by('-created_at')

        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == 'true')

        notif_type = self.request.query_params.get('type')
        if notif_type:
            qs = qs.filter(type=notif_type)

        return qs


class NotificationCountView(APIView, StandardResponseMixin):
    """تعداد اعلان‌های خوانده نشده"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=NotificationCountSerializer,
        tags=['Notifications'],
        summary='تعداد اعلان‌ها',
    )
    def get(self, request):
        user = request.user
        total = Notification.objects.filter(user=user).count()
        unread = NotificationService.get_unread_count(user)

        by_type = {}
        type_counts = (
            Notification.objects.filter(user=user, is_read=False)
            .values('type')
            .annotate(count=models.Count('id'))
        )

        for item in type_counts:
            by_type[item['type']] = item['count']

        return self.success_response(
            data={
                'total': total,
                'unread': unread,
                'by_type': by_type,
            }
        )


class MarkAsReadView(APIView, StandardResponseMixin):
    """علامت‌گذاری اعلان به عنوان خوانده شده"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MarkAsReadSerializer,
        tags=['Notifications'],
        summary='خوانده شده',
    )
    def post(self, request):
        serializer = MarkAsReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notification_ids = serializer.validated_data.get('notification_ids')

        if notification_ids:
            count = Notification.objects.filter(
                user=request.user,
                id__in=notification_ids,
                is_read=False,
            ).update(
                is_read=True,
                read_at=timezone.now(),
            )
        else:
            count = NotificationService.mark_as_read(user=request.user)

        return self.success_response(
            data={'marked_count': count},
            message=f'{count} اعلان خوانده شد',
        )


class DeleteNotificationView(APIView, StandardResponseMixin):
    """حذف اعلان"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Notifications'],
        summary='حذف اعلان',
    )
    def delete(self, request, pk):
        try:
            notification = Notification.objects.get(
                id=pk,
                user=request.user,
            )
            notification.delete()
            return self.success_response(
                message='اعلان حذف شد',
            )
        except Notification.DoesNotExist:
            return self.error_response(
                message='اعلان یافت نشد',
                code='NOTIFICATION_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )


class DeleteAllNotificationsView(APIView, StandardResponseMixin):
    """حذف همه اعلان‌های خوانده شده"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Notifications'],
        summary='حذف همه اعلان‌ها',
    )
    def delete(self, request):
        count, _ = Notification.objects.filter(
            user=request.user,
            is_read=True,
        ).delete()

        return self.success_response(
            data={'deleted_count': count},
            message=f'{count} اعلان حذف شد',
        )