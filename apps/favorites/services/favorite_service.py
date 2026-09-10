"""
سرویس مدیریت علاقه‌مندی‌ها
"""
from django.db import transaction
from apps.favorites.models import FavoriteBusiness


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

        return {'is_favorited': False, 'message': 'نوع نامعتبر'}

    @classmethod
    def is_favorited(cls, user, favorite_type: str, object_id: int) -> bool:
        """بررسی علاقه‌مندی"""
        if favorite_type == 'business':
            return FavoriteBusiness.objects.filter(
                user=user,
                business_id=object_id,
            ).exists()
        return False

    @classmethod
    def get_user_favorites(cls, user, favorite_type=None, limit=50):
        """دریافت علاقه‌مندی‌های کاربر"""
        if favorite_type == 'business' or favorite_type is None:
            return FavoriteBusiness.objects.filter(
                user=user
            ).select_related('business')[:limit]
        return []

    @classmethod
    def get_favorites_count(cls, user, favorite_type=None) -> int:
        """تعداد علاقه‌مندی‌ها"""
        if favorite_type == 'business':
            return FavoriteBusiness.objects.filter(user=user).count()
        return FavoriteBusiness.objects.filter(user=user).count()