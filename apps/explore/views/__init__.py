"""
Views برای ویترین / اکسپلور
"""
import logging
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.explore.models import ExplorePost
from apps.explore.serializers import (
    ExplorePostListSerializer,
    ExplorePostDetailSerializer,
    ExplorePostCreateSerializer,
)

logger = logging.getLogger(__name__)


class ExplorePostListView(APIView, StandardResponseMixin):
    """لیست پست‌های ویترین"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='category_id',
                type=int,
                required=False,
                description='فیلتر دسته‌بندی',
            ),
            OpenApiParameter(
                name='business_id',
                type=int,
                required=False,
                description='فیلتر کسب‌وکار',
            ),
            OpenApiParameter(
                name='page',
                type=int,
                required=False,
                description='شماره صفحه',
            ),
            OpenApiParameter(
                name='page_size',
                type=int,
                required=False,
                description='تعداد آیتم در صفحه',
            ),
        ],
        responses={200: ExplorePostListSerializer(many=True)},
        tags=['Explore'],
        summary='لیست پست‌های ویترین',
    )
    def get(self, request):
        queryset = ExplorePost.objects.filter(
            business__status='approved',
            business__is_active=True,
        ).select_related(
            'business', 'main_category', 'sub_category',
        ).prefetch_related('images').order_by('-is_pinned', '-created_at')

        # فیلتر دسته‌بندی
        category_id = request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(main_category_id=category_id)

        # فیلتر کسب‌وکار
        business_id = request.query_params.get('business_id')
        if business_id:
            queryset = queryset.filter(business_id=business_id)

        # Pagination
        pagination = StandardResultsSetPagination()
        page = pagination.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ExplorePostListSerializer(
                page, many=True, context={'request': request}
            )
            return pagination.get_paginated_response(serializer.data)

        serializer = ExplorePostListSerializer(
            queryset, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': queryset.count()},
        )


class ExplorePostDetailView(APIView, StandardResponseMixin):
    """جزئیات پست ویترین"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: ExplorePostDetailSerializer},
        tags=['Explore'],
        summary='جزئیات پست',
    )
    def get(self, request, pk):
        post = get_object_or_404(
            ExplorePost.objects.select_related(
                'business', 'business__city',
                'main_category', 'sub_category',
            ).prefetch_related('images'),
            id=pk,
            business__status='approved',
            business__is_active=True,
        )
        serializer = ExplorePostDetailSerializer(
            post, context={'request': request}
        )
        return self.success_response(data=serializer.data)


class BusinessPostCreateView(APIView, StandardResponseMixin):
    """ایجاد پست ویترین توسط کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=ExplorePostCreateSerializer,
        responses={201: ExplorePostDetailSerializer},
        tags=['Explore'],
        summary='ایجاد پست ویترین',
    )
    def post(self, request):
        serializer = ExplorePostCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        try:
            post = serializer.save()
            return self.success_response(
                data=ExplorePostDetailSerializer(
                    post, context={'request': request}
                ).data,
                message='پست با موفقیت ایجاد شد',
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Create explore post error: {e}")
            return self.error_response(
                message='خطا در ایجاد پست',
                code='CREATE_ERROR',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BusinessPostListView(APIView, StandardResponseMixin):
    """لیست پست‌های کسب‌وکار خودم"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Explore'],
        summary='پست‌های کسب‌وکار من',
    )
    def get(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        posts = ExplorePost.objects.filter(
            business=business,
        ).select_related(
            'main_category', 'sub_category',
        ).prefetch_related('images').order_by('-created_at')

        serializer = ExplorePostListSerializer(
            posts, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': posts.count()},
        )


class BusinessPostDeleteView(APIView, StandardResponseMixin):
    """حذف پست ویترین"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Explore'],
        summary='حذف پست',
    )
    def delete(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        try:
            post = ExplorePost.objects.get(id=pk, business=business)
            post.delete()
            return self.success_response(message='پست حذف شد')
        except ExplorePost.DoesNotExist:
            return self.error_response(
                message='پست یافت نشد',
                code='POST_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )