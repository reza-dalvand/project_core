"""
سرویس مدیریت علاقه‌مندی‌ها
"""
from django.contrib.contenttypes.models import ContentType

from apps.advanced.models import Favorite
from apps.businesses.models import Business, Service


class FavoriteService:
    """سرویس علاقه‌مندی‌ها"""

    @classmethod
    def toggle_favorite(cls, user, favorite_type, object_id):
        """
        اضافه/حذف علاقه‌مندی (toggle)
        """
        content_type = cls._get_content_type(favorite_type)
        title = cls._get_object_title(favorite_type, object_id)
        business_id = cls._get_business_id(favorite_type, object_id)

        existing = Favorite.objects.filter(
            user=user,
            favorite_type=favorite_type,
            object_id=object_id,
        ).first()

        if existing:
            existing.delete()
            return {
                'is_favorited': False,
                'message': 'از علاقه‌مندی‌ها حذف شد',
            }

        Favorite.objects.create(
            user=user,
            favorite_type=favorite_type,
            content_type=content_type,
            object_id=object_id,
            business_id=business_id,
            title=title,
        )

        return {
            'is_favorited': True,
            'message': 'به علاقه‌مندی‌ها اضافه شد',
        }

    @classmethod
    def is_favorited(cls, user, favorite_type, object_id):
        """بررسی علاقه‌مندی"""
        return Favorite.objects.filter(
            user=user,
            favorite_type=favorite_type,
            object_id=object_id,
        ).exists()

    @classmethod
    def get_user_favorites(cls, user, favorite_type=None, limit=50):
        """دریافت علاقه‌مندی‌های کاربر"""
        qs = Favorite.objects.filter(user=user)

        if favorite_type:
            qs = qs.filter(favorite_type=favorite_type)

        return qs.select_related('content_type')[:limit]

    @classmethod
    def get_favorites_count(cls, user, favorite_type=None):
        """تعداد علاقه‌مندی‌ها"""
        qs = Favorite.objects.filter(user=user)
        if favorite_type:
            qs = qs.filter(favorite_type=favorite_type)
        return qs.count()

    @classmethod
    def _get_content_type(cls, favorite_type):
        """دریافت ContentType"""
        type_model_map = {
            Favorite.Type.BUSINESS: Business,
            Favorite.Type.SERVICE: Service,
        }

        model = type_model_map.get(favorite_type)
        if model:
            return ContentType.objects.get_for_model(model)
        return None

    @classmethod
    def _get_object_title(cls, favorite_type, object_id):
        """دریافت عنوان آبجکت"""
        try:
            if favorite_type == Favorite.Type.BUSINESS:
                return Business.objects.get(id=object_id).name
            elif favorite_type == Favorite.Type.SERVICE:
                return Service.objects.get(id=object_id).name
        except Exception:
            pass
        return ''

    @classmethod
    def _get_business_id(cls, favorite_type, object_id):
        """دریافت شناسه کسب‌وکار"""
        try:
            if favorite_type == Favorite.Type.BUSINESS:
                return object_id
            elif favorite_type == Favorite.Type.SERVICE:
                return Service.objects.get(id=object_id).business_id
        except Exception:
            pass
        return None