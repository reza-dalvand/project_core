"""
Views برای مدیریت نمونه‌کارها
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404

from apps.businesses.models import Portfolio
from apps.businesses.serializers.portfolio import (
    PortfolioListSerializer,
    PortfolioDetailSerializer,
    PortfolioCreateSerializer,
    PortfolioUpdateSerializer,
)
from apps.core.permissions import IsApprovedBusinessOwner, IsBusinessOwnerOfObject
from apps.core.pagination import StandardResultsSetPagination
from django_filters.rest_framework import DjangoFilterBackend


class PortfolioListView(generics.ListCreateAPIView):
    """
    لیست و ایجاد نمونه‌کارها

    GET: دریافت لیست نمونه‌کارها
    POST: ایجاد نمونه‌کار جدید
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'service']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PortfolioCreateSerializer
        return PortfolioListSerializer

    def get_queryset(self):
        """دریافت نمونه‌کارهای کسب‌وکار فعلی"""
        return Portfolio.objects.filter(
            business=self.request.user.business
        ).prefetch_related('images').select_related('service').order_by('order', '-created_at')

    @extend_schema(
        summary='لیست نمونه‌کارها',
        description='دریافت لیست تمام نمونه‌کارهای کسب‌وکار شما',
        parameters=[
            OpenApiParameter(
                name='is_active',
                type=bool,
                description='فیلتر بر اساس وضعیت فعال/غیرفعال',
                required=False,
            ),
            OpenApiParameter(
                name='service',
                type=int,
                description='فیلتر بر اساس شناسه خدمت',
                required=False,
            ),
        ],
        responses={200: PortfolioListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='ایجاد نمونه‌کار جدید',
        description='ایجاد یک نمونه‌کار جدید برای کسب‌وکار شما',
        request=PortfolioCreateSerializer,
        responses={201: PortfolioDetailSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PortfolioDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    جزئیات، بروزرسانی و حذف نمونه‌کار

    GET: دریافت جزئیات نمونه‌کار
    PUT/PATCH: بروزرسانی نمونه‌کار
    DELETE: حذف نمونه‌کار
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner, IsBusinessOwnerOfObject]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'pk'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PortfolioUpdateSerializer
        return PortfolioDetailSerializer

    def get_queryset(self):
        """دریافت نمونه‌کارهای کسب‌وکار فعلی"""
        return Portfolio.objects.filter(
            business=self.request.user.business
        ).prefetch_related('images').select_related('service')

    @extend_schema(
        summary='جزئیات نمونه‌کار',
        description='دریافت جزئیات کامل یک نمونه‌کار',
        responses={200: PortfolioDetailSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی نمونه‌کار',
        description='بروزرسانی اطلاعات یک نمونه‌کار',
        request=PortfolioUpdateSerializer,
        responses={200: PortfolioDetailSerializer}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی جزئی نمونه‌کار',
        description='بروزرسانی بخشی از اطلاعات یک نمونه‌کار',
        request=PortfolioUpdateSerializer,
        responses={200: PortfolioDetailSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary='حذف نمونه‌کار',
        description='حذف یک نمونه‌کار از کسب‌وکار',
        responses={204: None}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class PortfolioToggleActiveView(APIView):
    """
    تغییر وضعیت فعال/غیرفعال نمونه‌کار
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        summary='تغییر وضعیت نمونه‌کار',
        description='فعال یا غیرفعال کردن یک نمونه‌کار',
        responses={200: PortfolioDetailSerializer}
    )
    def post(self, request, pk):
        portfolio = get_object_or_404(
            Portfolio,
            pk=pk,
            business=request.user.business
        )

        portfolio.is_active = not portfolio.is_active
        portfolio.save()

        serializer = PortfolioDetailSerializer(portfolio, context={'request': request})
        return Response({
            'success': True,
            'message': f'نمونه‌کار {portfolio.title} {"فعال" if portfolio.is_active else "غیرفعال"} شد',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class PortfolioReorderView(APIView):
    """
    تغییر ترتیب نمایش نمونه‌کارها
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        summary='تغییر ترتیب نمونه‌کارها',
        description='تغییر ترتیب نمایش نمونه‌کارها',
        request={
            'type': 'object',
            'properties': {
                'portfolio_orders': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'order': {'type': 'integer'}
                        }
                    },
                    'description': 'لیست شناسه‌ها و ترتیب جدید'
                }
            },
            'required': ['portfolio_orders']
        },
        responses={200: None}
    )
    def post(self, request):
        portfolio_orders = request.data.get('portfolio_orders', [])

        if not portfolio_orders:
            return Response({
                'success': False,
                'message': 'لیست ترتیب‌ها الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)

        # بروزرسانی ترتیب‌ها
        updated_count = 0
        for item in portfolio_orders:
            portfolio_id = item.get('id')
            new_order = item.get('order')

            if portfolio_id and new_order is not None:
                try:
                    portfolio = Portfolio.objects.get(
                        id=portfolio_id,
                        business=request.user.business
                    )
                    portfolio.order = new_order
                    portfolio.save()
                    updated_count += 1
                except Portfolio.DoesNotExist:
                    continue

        return Response({
            'success': True,
            'message': f'ترتیب {updated_count} نمونه‌کار با موفقیت بروزرسانی شد'
        }, status=status.HTTP_200_OK)