"""
Views علاقه‌مندی‌ها
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.advanced.services.favorite_service import FavoriteService
from apps.advanced.serializers import (
    FavoriteToggleSerializer,
    FavoriteSerializer,
    FavoriteCheckSerializer,
    FavoriteCheckResponseSerializer,
)


class FavoriteToggleView(APIView, StandardResponseMixin):
    """اضافه/حذف علاقه‌مندی"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=FavoriteToggleSerializer,
        tags=['Favorites'],
        summary='تغییر وضعیت علاقه‌مندی',
        description='اضافه یا حذف یک آیتم از علاقه‌مندی‌ها',
    )
    def post(self, request):
        serializer = FavoriteToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = FavoriteService.toggle_favorite(
            user=request.user,
            favorite_type=serializer.validated_data['favorite_type'],
            object_id=serializer.validated_data['object_id'],
        )

        return self.success_response(
            data=result,
            message=result['message'],
        )


class FavoriteListView(APIView, StandardResponseMixin):
    """لیست علاقه‌مندی‌ها"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            {
                'name': 'type',
                'type': str,
                'required': False,
                'enum': ['business', 'service', 'post', 'model_request', 'line_rental'],
            },
        ],
        responses=FavoriteSerializer(many=True),
        tags=['Favorites'],
        summary='لیست علاقه‌مندی‌ها',
    )
    def get(self, request):
        favorite_type = request.query_params.get('type')

        favorites = FavoriteService.get_user_favorites(
            user=request.user,
            favorite_type=favorite_type,
        )

        return self.success_response(
            data=FavoriteSerializer(favorites, many=True).data,
            meta={
                'total': FavoriteService.get_favorites_count(
                    request.user, favorite_type
                ),
            },
        )


class FavoriteCheckView(APIView, StandardResponseMixin):
    """بررسی وضعیت علاقه‌مندی"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=FavoriteCheckSerializer,
        responses=FavoriteCheckResponseSerializer,
        tags=['Favorites'],
        summary='بررسی علاقه‌مندی',
    )
    def post(self, request):
        serializer = FavoriteCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_fav = FavoriteService.is_favorited(
            user=request.user,
            favorite_type=serializer.validated_data['favorite_type'],
            object_id=serializer.validated_data['object_id'],
        )

        return self.success_response(
            data={'is_favorited': is_fav}
        )


class FavoriteCountView(APIView, StandardResponseMixin):
    """تعداد علاقه‌مندی‌ها"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Favorites'],
        summary='تعداد علاقه‌مندی‌ها',
    )
    def get(self, request):
        from apps.advanced.models import Favorite

        counts = {}
        for type_choice in Favorite.Type.choices:
            counts[type_choice[0]] = FavoriteService.get_favorites_count(
                request.user, type_choice[0]
            )

        counts['total'] = sum(counts.values())

        return self.success_response(data=counts)