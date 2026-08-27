"""
Views برای پشتیبانی و FAQ
"""
import logging
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.core.pagination import StandardResultsSetPagination
from apps.support.models import FAQ, SupportTicket
from apps.support.serializers import (
    FAQSerializer,
    SupportTicketCreateSerializer,
    SupportTicketListSerializer,
    SupportTicketDetailSerializer,
)

logger = logging.getLogger(__name__)


class FAQListView(APIView, StandardResponseMixin):
    """لیست سوالات متداول"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='category',
                type=str,
                required=False,
                description='فیلتر دسته‌بندی',
            ),
        ],
        responses={200: FAQSerializer(many=True)},
        tags=['Support'],
        summary='لیست سوالات متداول',
    )
    def get(self, request):
        queryset = FAQ.objects.filter(
            is_active=True,
        ).order_by('sort_order')

        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        serializer = FAQSerializer(queryset, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': queryset.count()},
        )


class SupportTicketCreateView(APIView, StandardResponseMixin):
    """ایجاد تیکت پشتیبانی"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=SupportTicketCreateSerializer,
        responses={201: SupportTicketDetailSerializer},
        tags=['Support'],
        summary='ایجاد تیکت پشتیبانی',
    )
    def post(self, request):
        serializer = SupportTicketCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        try:
            ticket = serializer.save()
            return self.success_response(
                data=SupportTicketDetailSerializer(ticket).data,
                message='تیکت پشتیبانی ایجاد شد. در اسرع وقت پاسخ داده می‌شود.',
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Create support ticket error: {e}")
            return self.error_response(
                message='خطا در ایجاد تیکت',
                code='CREATE_ERROR',
            )


class SupportTicketListView(APIView, StandardResponseMixin):
    """لیست تیکت‌های کاربر"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Support'],
        summary='تیکت‌های من',
    )
    def get(self, request):
        tickets = SupportTicket.objects.filter(
            user=request.user,
        ).order_by('-created_at')

        serializer = SupportTicketListSerializer(tickets, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': tickets.count()},
        )


class SupportTicketDetailView(APIView, StandardResponseMixin):
    """جزئیات تیکت"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: SupportTicketDetailSerializer},
        tags=['Support'],
        summary='جزئیات تیکت',
    )
    def get(self, request, pk):
        try:
            ticket = SupportTicket.objects.get(
                id=pk, user=request.user
            )
            serializer = SupportTicketDetailSerializer(ticket)
            return self.success_response(data=serializer.data)
        except SupportTicket.DoesNotExist:
            return self.error_response(
                message='تیکت یافت نشد',
                code='TICKET_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )