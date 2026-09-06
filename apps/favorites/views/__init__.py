# apps/favorites/views/__init__.py
# اصلاح فرمت پاسخ برای تطبیق با Frontend

"""
Views برای علاقه‌مندی‌ها
"""
import logging
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.core.mixins import StandardResponseMixin
from apps.favorites.models import FavoriteBusiness
from apps.favorites.serializers import FavoriteBusinessSerializer
from apps.explore.models import ExplorePost

logger = logging.getLogger(__name__)


class FavoriteListView(APIView, StandardResponseMixin):
    """
    لیست علاقه‌مندی‌ها
    فرمت پاسخ مطابق انتظار Frontend:
    {
        businesses: [...],
        posts: [...]
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Favorites'],
        summary='لیست علاقه‌مندی‌ها',
    )
    def get(self, request):
        favorite_type = request.query_params.get('type')

        businesses_data = []
        posts_data = []

        if favorite_type in (None, 'business'):
            fav_businesses = FavoriteBusiness.objects.filter(
                user=request.user,
                business__is_active=True,
            ).select_related(
                'business', 'business__category', 'business__city'
            )
            serializer = FavoriteBusinessSerializer(
                fav_businesses, many=True, context={'request': request}
            )
            businesses_data = serializer.data

        if favorite_type in (None, 'post'):
            # FavoritePost حذف شده — لیست خالی برمی‌گردانیم
            posts_data = []

        return self.success_response(
            data={
                'businesses': businesses_data,
                'posts': posts_data,
            },
            meta={
                'business_count': len(businesses_data),
                'post_count': len(posts_data),
            },
        )


class FavoriteToggleView(APIView, StandardResponseMixin):
    """تغییر وضعیت علاقه‌مندی"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Favorites'],
        summary='تغییر وضعیت علاقه‌مندی',
    )
    def post(self, request):
        favorite_type = request.data.get('favorite_type')
        object_id = request.data.get('object_id')

        if not favorite_type or not object_id:
            return self.error_response(
                message='favorite_type و object_id الزامی هستند',
                code='MISSING_PARAMS',
            )

        if favorite_type == 'business':
            from apps.businesses.models import Business
            try:
                business = Business.objects.get(id=object_id)
            except Business.DoesNotExist:
                return self.error_response(
                    message='کسب‌وکار یافت نشد',
                    code='BUSINESS_NOT_FOUND',
                )

            fav, created = FavoriteBusiness.objects.get_or_create(
                user=request.user,
                business=business,
            )

            if not created:
                fav.delete()
                return self.success_response(
                    data={'is_favorited': False},
                    message='از علاقه‌مندی‌ها حذف شد',
                )

            return self.success_response(
                data={'is_favorited': True},
                message='به علاقه‌مندی‌ها اضافه شد',
            )

        elif favorite_type == 'post':
            # FavoritePost حذف شده
            return self.error_response(
                message='علاقه‌مندی به پست در حال حاضر پشتیبانی نمی‌شود',
                code='NOT_SUPPORTED',
            )

        return self.error_response(
            message='نوع علاقه‌مندی نامعتبر است',
            code='INVALID_TYPE',
        )


class FavoriteCountView(APIView, StandardResponseMixin):
    """تعداد علاقه‌مندی‌ها"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Favorites'],
        summary='تعداد علاقه‌مندی‌ها',
    )
    def get(self, request):
        business_count = FavoriteBusiness.objects.filter(
            user=request.user,
        ).count()

        return self.success_response(
            data={
                'business': business_count,
                'post': 0,
                'total': business_count,
            },
        )