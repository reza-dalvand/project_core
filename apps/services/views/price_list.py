"""
View لیست قیمت — نسخه نهایی
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.services.serializers.price_list import (
    PriceListSerializer,
    PriceListUpdateSerializer,
)

from rest_framework import permissions
from apps.businesses.models import Business
from apps.services.models import PriceList
from drf_spectacular.utils import extend_schema, OpenApiParameter

logger = logging.getLogger(__name__)


class PriceListView(APIView, StandardResponseMixin):
    """
    لیست قیمت کسب‌وکار
    GET  → دریافت لیست قیمت
    PUT  → بروزرسانی لیست قیمت (تم، انتشار، notes)
    """
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        responses={200: PriceListSerializer},
        tags=['Services'],
        summary='دریافت لیست قیمت',
    )
    def get(self, request):
        """دریافت لیست قیمت"""
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            return self.error_response(
                message='کسب‌وکار تایید شده یافت نشد',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )

        price_list, _ = PriceList.objects.get_or_create(business=business)
        serializer = PriceListSerializer(price_list)

        return self.success_response(data=serializer.data)

    @extend_schema(
        request=PriceListUpdateSerializer,
        responses={200: PriceListSerializer},
        tags=['Services'],
        summary='بروزرسانی لیست قیمت',
    )
    def put(self, request):
        """بروزرسانی لیست قیمت"""
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            return self.error_response(
                message='کسب‌وکار تایید شده یافت نشد',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )

        price_list, _ = PriceList.objects.get_or_create(business=business)

        serializer = PriceListUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = serializer.update(price_list, serializer.validated_data)

        return self.success_response(
            data=PriceListSerializer(updated).data,
            message='لیست قیمت با موفقیت بروزرسانی شد',
        )


class PublicPriceListView(APIView, StandardResponseMixin):
    """
    لیست قیمت عمومی کسب‌وکار — برای نمایش به مشتریان
    بدون نیاز به احراز هویت
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='business_id', type=int, required=True),
        ],
        tags=['Services'],
        summary='لیست قیمت عمومی کسب‌وکار',
    )
    def get(self, request):
        business_id = request.query_params.get('business_id')
        if not business_id:
            return self.error_response(
                message='شناسه کسب‌وکار الزامی است',
                code='BUSINESS_ID_REQUIRED',
            )

        try:
            business = Business.objects.get(
                id=business_id,
                status='approved',
                is_active=True,
            )
        except Business.DoesNotExist:
            return self.error_response(
                message='کسب‌وکار یافت نشد',
                code='BUSINESS_NOT_FOUND',
                status=404,
            )

        try:
            price_list = PriceList.objects.get(business=business)
        except PriceList.DoesNotExist:
            # اگر لیست قیمت وجود ندارد، از خدمات کسب‌وکار بساز
            services = business.services.filter(is_active=True)
            services_data = [
                {
                    'id': s.id,
                    'name': s.name,
                    'type_name': s.sub_service.name if s.sub_service else '',
                    'type_id': s.sub_service.type_id if s.sub_service else '',
                    'original_price': s.original_price,
                    'discount_percent': s.discount_percent,
                    'final_price': s.final_price,
                    'has_deposit': s.has_deposit,
                    'deposit_amount': s.deposit_amount,
                }
                for s in services
            ]
            return self.success_response(
                data={
                    'business_id': business.id,
                    'theme': 'classic',
                    'is_published': True,
                    'services': services_data,
                }
            )

        # اگر لیست قیمت منتشر نشده، نمایش نده
        if not price_list.is_published:
            return self.success_response(
                data={
                    'business_id': business.id,
                    'theme': price_list.theme,
                    'is_published': False,
                    'services': [],
                }
            )

        services = business.services.filter(is_active=True)
        services_data = [
            {
                'id': s.id,
                'name': s.name,
                'type_name': s.sub_service.name if s.sub_service else '',
                'type_id': s.sub_service.type_id if s.sub_service else '',
                'original_price': s.original_price,
                'discount_percent': s.discount_percent,
                'final_price': s.final_price,
                'has_deposit': s.has_deposit,
                'deposit_amount': s.deposit_amount,
            }
            for s in services
        ]

        notes_data = [
            {'id': n.id, 'label': n.label, 'min_value': n.min_value, 'max_value': n.max_value}
            for n in price_list.notes.all()
        ]

        return self.success_response(
            data={
                'business_id': business.id,
                'theme': price_list.theme,
                'is_published': price_list.is_published,
                'services': services_data,
                'notes': notes_data,
            }
        )