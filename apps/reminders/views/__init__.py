"""
Views برای یادآوری تمدید
+ ارسال یادآوری (فاز ۱)
"""
import logging
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.reminders.models import RenewalReminder
from apps.reminders.serializers import RenewalReminderSerializer

logger = logging.getLogger(__name__)


class RenewalReminderListView(APIView, StandardResponseMixin):
    """لیست یادآوری‌های تمدید برای کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page', type=int, required=False),
            OpenApiParameter(
                name='days_remaining_max',
                type=int,
                required=False,
                description='حداکثر روزهای باقی‌مانده',
            ),
        ],
        responses={200: RenewalReminderSerializer(many=True)},
        tags=['Reminders'],
        summary='لیست یادآوری‌های تمدید',
    )
    def get(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        queryset = RenewalReminder.objects.filter(
            business=business,
        ).select_related(
            'customer', 'service',
        ).order_by('days_remaining')

        days_max = request.query_params.get('days_remaining_max')
        if days_max:
            try:
                queryset = queryset.filter(days_remaining__lte=int(days_max))
            except (ValueError, TypeError):
                pass

        pagination = StandardResultsSetPagination()
        page = pagination.paginate_queryset(queryset, request)
        if page is not None:
            serializer = RenewalReminderSerializer(page, many=True)
            return pagination.get_paginated_response(serializer.data)

        serializer = RenewalReminderSerializer(queryset, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': queryset.count()},
        )


class CustomerRenewalReminderListView(APIView, StandardResponseMixin):
    """لیست یادآوری‌های تمدید برای مشتری"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Reminders'],
        summary='یادآوری‌های تمدید من',
    )
    def get(self, request):
        reminders = RenewalReminder.objects.filter(
            customer=request.user,
        ).select_related(
            'business', 'service',
        ).order_by('days_remaining')

        serializer = RenewalReminderSerializer(reminders, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': reminders.count()},
        )


# ═══════════════════════════════════════════════════════
#   🆕 فاز ۱: ارسال یادآوری تمدید
# ═══════════════════════════════════════════════════════

class SendRenewalReminderView(APIView, StandardResponseMixin):
    """
    ارسال پیام یادآوری تمدید به مشتریان

    POST /reminders/send/
    Body: { "reminder_ids": [1, 2, 3] }

    قوانین:
    - فقط کسب‌وکارهای تایید شده
    - هر یادآوری فقط یک‌بار ارسال می‌شود
    - پس از ارسال، reminder_sent = True
    - اگر مشتری بعداً رزرو جدید بزند، has_new_booking_after_send = True
      و امکان ارسال مجدد فراهم می‌شود
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Reminders'],
        summary='ارسال یادآوری تمدید',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'reminder_ids': {
                        'type': 'array',
                        'items': {'type': 'integer'},
                        'description': 'لیست شناسه یادآوری‌ها',
                    },
                },
                'required': ['reminder_ids'],
            },
        },
    )
    def post(self, request):
        reminder_ids = request.data.get('reminder_ids', [])

        if not reminder_ids:
            return self.error_response(
                message='لیست یادآوری‌ها نمی‌تواند خالی باشد',
                code='EMPTY_REMINDER_LIST',
            )

        if len(reminder_ids) > 50:
            return self.error_response(
                message='حداکثر ۵۰ یادآوری در هر ارسال مجاز است',
                code='TOO_MANY_REMINDERS',
            )

        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            return self.error_response(
                message='کسب‌وکار تایید شده یافت نشد',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )

        import jdatetime

        today = jdatetime.date.today()
        today_key = f'{today.jyear}/{today.jmonth:02d}/{today.jday:02d}'

        sent_count = 0
        skipped_count = 0
        errors = []

        for reminder_id in reminder_ids:
            try:
                reminder = RenewalReminder.objects.select_related(
                    'customer', 'service', 'business',
                ).get(
                    id=reminder_id,
                    business=business,
                )

                # بررسی امکان ارسال
                if reminder.reminder_sent and not reminder.has_new_booking_after_send:
                    skipped_count += 1
                    continue

                # ارسال نوتیفیکیشن
                try:
                    from apps.notifications.services import NotificationService

                    NotificationService.send(
                        user=reminder.customer,
                        type='booking_reminder',
                        title='یادآوری تمدید خدمت ⏰',
                        body=(
                            f'زمان تمدید {reminder.service.name} '
                            f'در {reminder.business.name} فرا رسیده است. '
                            f'همین حالا نوبت خود را رزرو کنید.'
                        ),
                        data={
                            'reminder_id': reminder.id,
                            'service_id': reminder.service.id,
                            'business_id': reminder.business.id,
                        },
                        channels=['in_app', 'sms'],
                    )
                except Exception as e:
                    logger.error(f"Failed to send reminder notification: {e}")

                # بروزرسانی وضعیت یادآوری
                reminder.reminder_sent = True
                reminder.sent_date = today_key
                reminder.has_new_booking_after_send = False
                reminder.save(update_fields=[
                    'reminder_sent', 'sent_date', 'has_new_booking_after_send',
                ])

                sent_count += 1

            except RenewalReminder.DoesNotExist:
                errors.append(f'یادآوری با شناسه {reminder_id} یافت نشد')
            except Exception as e:
                errors.append(f'خطا در ارسال یادآوری {reminder_id}: {str(e)}')

        response_data = {
            'sent_count': sent_count,
            'skipped_count': skipped_count,
            'total_requested': len(reminder_ids),
        }

        if errors:
            response_data['errors'] = errors

        return self.success_response(
            data=response_data,
            message=f'{sent_count} یادآوری با موفقیت ارسال شد',
        )