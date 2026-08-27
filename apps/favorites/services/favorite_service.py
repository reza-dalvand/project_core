"""
سرویس مدیریت علاقه‌مندی‌ها
"""
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from apps.favorites.models import FavoriteBusiness, FavoritePost


class FavoriteService:
    """سرویس علاقه‌مندی‌ها"""

    @classmethod
    def toggle_favorite(cls, user, favorite_type: str, object_id: int):
        """
        تغییر وضعیت علاقه‌مندی
        """
        if favorite_type == 'business':
            from apps.businesses.models import Business
            try:
                business = Business.objects.get(id=object_id)
            except Business.DoesNotExist:
                return {'is_favorited': False, 'message': 'کسب‌وکار یافت نشد'}

            with transaction.atomic():
                fav, created = FavoriteBusiness.objects.get_or_create(
                    user=user,
                    business=business,
                )
                if not created:
                    fav.delete()
                    return {
                        'is_favorited': False,
                        'message': 'از علاقه‌مندی‌ها حذف شد',
                    }
                return {
                    'is_favorited': True,
                    'message': 'به علاقه‌مندی‌ها اضافه شد',
                }

        elif favorite_type == 'post':
            from apps.explore.models import ExplorePost
            try:
                post = ExplorePost.objects.get(id=object_id)
            except ExplorePost.DoesNotExist:
                return {'is_favorited': False, 'message': 'پست یافت نشد'}

            with transaction.atomic():
                fav, created = FavoritePost.objects.get_or_create(
                    user=user,
                    post=post,
                )
                if not created:
                    fav.delete()
                    return {
                        'is_favorited': False,
                        'message': 'از علاقه‌مندی‌ها حذف شد',
                    }
                return {
                    'is_favorited': True,
                    'message': 'به علاقه‌مندی‌ها اضافه شد',
                }

        return {'is_favorited': False, 'message': 'نوع نامعتبر'}

    @classmethod
    def is_favorited(cls, user, favorite_type: str, object_id: int) -> bool:
        """بررسی علاقه‌مندی"""
        if favorite_type == 'business':
            return FavoriteBusiness.objects.filter(
                user=user,
                business_id=object_id,
            ).exists()
        elif favorite_type == 'post':
            return FavoritePost.objects.filter(
                user=user,
                post_id=object_id,
            ).exists()
        return False

    @classmethod
    def get_user_favorites(cls, user, favorite_type=None, limit=50):
        """دریافت علاقه‌مندی‌های کاربر"""
        if favorite_type == 'business':
            return FavoriteBusiness.objects.filter(
                user=user
            ).select_related('business')[:limit]
        elif favorite_type == 'post':
            return FavoritePost.objects.filter(
                user=user
            ).select_related('post')[:limit]
        return []

    @classmethod
    def get_favorites_count(cls, user, favorite_type=None) -> int:
        """تعداد علاقه‌مندی‌ها"""
        if favorite_type == 'business':
            return FavoriteBusiness.objects.filter(user=user).count()
        elif favorite_type == 'post':
            return FavoritePost.objects.filter(user=user).count()

        business_count = FavoriteBusiness.objects.filter(user=user).count()
        post_count = FavoritePost.objects.filter(user=user).count()
        return business_count + post_count