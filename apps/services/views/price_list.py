"""
View لیست قیمت — نسخه نهایی
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.services.models import PriceList
from apps.services.serializers.price_list import (
    PriceListSerializer,
    PriceListUpdateSerializer,
)

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