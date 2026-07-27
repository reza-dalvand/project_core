"""
سرویس مدیریت علاقه‌مندی‌ها
✅ بهینه‌شده: Atomic toggle و کاهش کوئری‌ها
"""
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from apps.advanced.models import Favorite
from apps.businesses.models import Business, Service


class FavoriteService:
    """سرویس علاقه‌مندی‌ها"""

    @classmethod
    def toggle_favorite(cls, user, favorite_type, object_id):
        """
        ✅ بهینه: Atomic toggle با get_or_create
        جلوگیری از Race Condition
        """
        content_type = cls._get_content_type(favorite_type)
        title = cls._get_object_title(favorite_type, object_id)
        business_id = cls._get_business_id(favorite_type, object_id)

        with transaction.atomic():
            favorite, created = Favorite.objects.get_or_create(
                user=user,
                favorite_type=favorite_type,
                object_id=object_id,
                defaults={
                    'content_type': content_type,
                    'business_id': business_id,
                    'title': title,
                }
            )

            if not created:
                favorite.delete()
                return {
                    'is_favorited': False,
                    'message': 'از علاقه‌مندی‌ها حذف شد',
                }

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
        """
        ✅ بهینه: استفاده از values_list به جای get()
        """
        try:
            if favorite_type == Favorite.Type.BUSINESS:
                return Business.objects.filter(id=object_id).values_list('name', flat=True).first() or ''
            elif favorite_type == Favorite.Type.SERVICE:
                return Service.objects.filter(id=object_id).values_list('name', flat=True).first() or ''
        except Exception:
            pass
        return ''

    @classmethod
    def _get_business_id(cls, favorite_type, object_id):
        """
        ✅ بهینه: استفاده از values_list به جای get()
        """
        try:
            if favorite_type == Favorite.Type.BUSINESS:
                return object_id
            elif favorite_type == Favorite.Type.SERVICE:
                return Service.objects.filter(id=object_id).values_list('business_id', flat=True).first()
        except Exception:
            pass
        return None