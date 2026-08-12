"""
Views برای یادآوری تمدید
"""
import logging
from rest_framework import permissions
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
            OpenApiParameter(
                name='page',
                type=int,
                required=False,
            ),
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

        # فیلتر روزهای باقی‌مانده
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