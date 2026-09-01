"""
Views برای علاقه‌مندی‌ها — نسخه نهایی
"""
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.core.mixins import StandardResponseMixin
from apps.favorites.models import FavoriteBusiness
from apps.favorites.serializers import (
    FavoriteBusinessSerializer,
    FavoriteToggleSerializer,
)


class FavoriteToggleView(APIView, StandardResponseMixin):
    """اضافه/حذف علاقه‌مندی"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=FavoriteToggleSerializer,
        tags=['Favorites'],
        summary='تغییر وضعیت علاقه‌مندی',
    )
    def post(self, request):
        serializer = FavoriteToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        favorite_type = serializer.validated_data['favorite_type']
        object_id = serializer.validated_data['object_id']

        if favorite_type == 'business':
            from apps.businesses.models import Business
            try:
                business = Business.objects.get(id=object_id)
            except Business.DoesNotExist:
                return self.error_response(
                    message='کسب‌وکار یافت نشد',
                    code='BUSINESS_NOT_FOUND',
                    status=status.HTTP_404_NOT_FOUND,
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

        # ❌ بخش 'post' حذف شد

        return self.error_response(
            message='نوع علاقه‌مندی نامعتبر است',
            code='INVALID_FAVORITE_TYPE',
            status=status.HTTP_400_BAD_REQUEST,
        )


class FavoriteListView(APIView, StandardResponseMixin):
    """لیست علاقه‌مندی‌ها"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Favorites'],
        summary='لیست علاقه‌مندی‌ها',
    )
    def get(self, request):
        favorite_type = request.query_params.get('type')

        if favorite_type == 'business' or favorite_type is None:
            favorites = FavoriteBusiness.objects.filter(
                user=request.user
            ).select_related('business', 'business__category', 'business__city')

            serializer = FavoriteBusinessSerializer(
                favorites, many=True, context={'request': request}
            )

            return self.success_response(
                data=serializer.data,
                meta={'count': len(serializer.data)},
            )

        return self.success_response(
            data=[],
            meta={'count': 0},
        )


class FavoriteCountView(APIView, StandardResponseMixin):
    """تعداد علاقه‌مندی‌ها"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Favorites'],
        summary='تعداد علاقه‌مندی‌ها',
    )
    def get(self, request):
        business_count = FavoriteBusiness.objects.filter(user=request.user).count()

        return self.success_response(
            data={
                'business': business_count,
                'total': business_count,
            }
        )