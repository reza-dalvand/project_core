"""
Views برای نمونه‌کارها
"""
import logging
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.portfolios.models import Portfolio
from apps.portfolios.serializers import (
    PortfolioListSerializer,
    PortfolioDetailSerializer,
    PortfolioCreateSerializer,
    PortfolioUpdateSerializer,
)

logger = logging.getLogger(__name__)


# apps/portfolios/views/__init__.py — فقط متد get

class PortfolioListView(APIView, StandardResponseMixin):
    """لیست عمومی نمونه‌کارها — برای ویترین"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: PortfolioListSerializer(many=True)},
        tags=['Portfolios'],
        summary='لیست نمونه‌کارها (ویترین)',
    )
    def get(self, request):
        import random

        queryset = Portfolio.objects.filter(
            business__status='approved',
            business__is_active=True,
            is_active=True,
        ).select_related(
            'business', 'business__city',
            'category', 'sub_service',
        ).prefetch_related('images').order_by('-created_at')

        # فیلتر دسته‌بندی
        category_id = request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # فیلتر کسب‌وکار خاص
        business_id = request.query_params.get('business_id')
        if business_id:
            queryset = queryset.filter(business_id=business_id)

        # Pagination
        pagination = StandardResultsSetPagination()
        page = pagination.paginate_queryset(queryset, request)

        # ✅ شافل رندوم
        if page is not None:
            shuffled = list(page)
            random.shuffle(shuffled)
            serializer = PortfolioListSerializer(
                shuffled, many=True, context={'request': request}
            )
            return pagination.get_paginated_response(serializer.data)

        shuffled = list(queryset)
        random.shuffle(shuffled)
        serializer = PortfolioListSerializer(
            shuffled, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': queryset.count()},
        )

class PortfolioDetailView(APIView, StandardResponseMixin):
    """جزئیات نمونه‌کار"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: PortfolioDetailSerializer},
        tags=['Portfolios'],
        summary='جزئیات نمونه‌کار',
    )
    def get(self, request, pk):
        portfolio = get_object_or_404(
            Portfolio.objects.select_related(
                'business', 'category', 'sub_service'
            ).prefetch_related('images'),
            id=pk,
            business__status='approved',
            business__is_active=True,
        )
        serializer = PortfolioDetailSerializer(
            portfolio, context={'request': request}
        )
        return self.success_response(data=serializer.data)


class BusinessPortfolioCreateView(APIView, StandardResponseMixin):
    """ایجاد نمونه‌کار توسط کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=PortfolioCreateSerializer,
        responses={201: PortfolioDetailSerializer},
        tags=['Portfolios'],
        summary='ایجاد نمونه‌کار',
    )
    def post(self, request):
        serializer = PortfolioCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            portfolio = serializer.save()
            return self.success_response(
                data=PortfolioDetailSerializer(
                    portfolio, context={'request': request}
                ).data,
                message='نمونه‌کار با موفقیت ایجاد شد',
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Create portfolio error: {e}", exc_info=True)
            return self.error_response(
                message='خطا در ایجاد نمونه‌کار',
                code='CREATE_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BusinessPortfolioListView(APIView, StandardResponseMixin):
    """لیست نمونه‌کارهای کسب‌وکار من"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Portfolios'],
        summary='نمونه‌کارهای کسب‌وکار من',
    )
    def get(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        portfolios = Portfolio.objects.filter(
            business=business,
        ).select_related('category', 'sub_service').prefetch_related(
            'images'
        ).order_by('-created_at')

        serializer = PortfolioListSerializer(
            portfolios, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': portfolios.count()},
        )


class BusinessPortfolioUpdateView(APIView, StandardResponseMixin):
    """ویرایش نمونه‌کار"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser] 

    @extend_schema(
        request=PortfolioUpdateSerializer,
        responses={200: PortfolioDetailSerializer},
        tags=['Portfolios'],
        summary='ویرایش نمونه‌کار',
    )
    def put(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        if not business:
            return self.error_response(
                message='کسب‌وکار تایید شده یافت نشد',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            portfolio = Portfolio.objects.prefetch_related('images').get(
                id=pk, business=business
            )
        except Portfolio.DoesNotExist:
            return self.error_response(
                message='نمونه‌کار یافت نشد',
                code='PORTFOLIO_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PortfolioUpdateSerializer(
            portfolio,
            data=request.data,
            partial=True,
            context={'request': request},
        )

        if not serializer.is_valid():
            return self.error_response(
                message='خطا در اعتبارسنجی داده‌ها',
                code='VALIDATION_ERROR',
                details=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated = serializer.save()
            return self.success_response(
                data=PortfolioDetailSerializer(
                    updated, context={'request': request}
                ).data,
                message='نمونه‌کار با موفقیت ویرایش شد',
            )
        except Exception as e:
            logger.error(f"Update portfolio error: {e}", exc_info=True)
            return self.error_response(
                message='خطا در ویرایش نمونه‌کار',
                code='UPDATE_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BusinessPortfolioDeleteView(APIView, StandardResponseMixin):
    """حذف نمونه‌کار"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Portfolios'],
        summary='حذف نمونه‌کار',
    )
    def delete(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        try:
            portfolio = Portfolio.objects.get(id=pk, business=business)
            portfolio.delete()
            return self.success_response(message='نمونه‌کار حذف شد')
        except Portfolio.DoesNotExist:
            return self.error_response(
                message='نمونه‌کار یافت نشد',
                code='PORTFOLIO_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )