"""
سرویس جستجوی یکپارچه
با پشتیبانی از PostgreSQL (pg_trgm) و SQLite
"""
import logging
from django.db import connection
from django.db.models import Q
from apps.businesses.models import Business
from apps.services.models import Service
from apps.search.models import SearchHistory

logger = logging.getLogger(__name__)


def _is_postgres():
    """بررسی اینکه دیتابیس PostgreSQL است یا نه"""
    return connection.vendor == 'postgresql'


def _pg_trgm_available():
    """بررسی اینکه extension pg_trgm فعال است یا نه"""
    if not _is_postgres():
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"
            )
            return cursor.fetchone() is not None
    except Exception:
        return False


class SearchService:
    """سرویس جستجوی یکپارچه"""

    MAX_HISTORY_PER_USER = 50
    MIN_QUERY_LENGTH = 2

    @classmethod
    def search_businesses(cls, query, province_id=None, city_id=None,
                          category_id=None, min_rating=0, has_discount=False,
                          limit=20):
        """
        جستجو در کسب‌وکارها
        
        Args:
            query: عبارت جستجو
            province_id: فیلتر استان
            city_id: فیلتر شهر
            category_id: فیلتر دسته‌بندی
            min_rating: حداقل امتیاز
            has_discount: فقط کسب‌وکارهای دارای تخفیف
            limit: حداکثر تعداد نتایج
            
        Returns:
            QuerySet از کسب‌وکارهای یافت شده
        """
        qs = Business.objects.filter(status=Business.Status.APPROVED)

        if province_id:
            qs = qs.filter(province_id=province_id)
        if city_id:
            qs = qs.filter(city_id=city_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if min_rating:
            qs = qs.filter(rating__gte=min_rating)
        if has_discount:
            qs = qs.filter(services__discount_percent__gt=0).distinct()

        if query and len(query) >= cls.MIN_QUERY_LENGTH:
            # تلاش برای استفاده از TrigramSimilarity (فقط PostgreSQL با pg_trgm)
            if _is_postgres() and _pg_trgm_available():
                try:
                    from django.contrib.postgres.search import TrigramSimilarity
                    qs = qs.annotate(
                        similarity=TrigramSimilarity('name', query)
                    ).filter(similarity__gt=0.1).order_by('-similarity')
                except Exception as e:
                    logger.warning(
                        f"TrigramSimilarity failed, falling back to icontains: {e}"
                    )
                    # Fallback به جستجوی عادی
                    qs = qs.filter(
                        Q(name__icontains=query) | Q(about__icontains=query)
                    ).order_by('-rating', '-created_at')
            else:
                # جستجوی عادی برای SQLite و PostgreSQL بدون pg_trgm
                qs = qs.filter(
                    Q(name__icontains=query) | Q(about__icontains=query)
                ).order_by('-rating', '-created_at')
        else:
            qs = qs.order_by('-rating', '-created_at')

        return qs.select_related(
            'category', 'province', 'city', 'owner'
        )[:limit]

    @classmethod
    def search_services(cls, query, business_id=None, category_id=None,
                        min_price=0, max_price=None, has_discount=False,
                        limit=20):
        """
        جستجو در خدمات
        
        Args:
            query: عبارت جستجو
            business_id: فیلتر کسب‌وکار
            category_id: فیلتر دسته‌بندی
            min_price: حداقل قیمت
            max_price: حداکثر قیمت
            has_discount: فقط خدمات دارای تخفیف
            limit: حداکثر تعداد نتایج
            
        Returns:
            QuerySet از خدمات یافت شده
        """
        qs = Service.objects.filter(is_active=True)

        if business_id:
            qs = qs.filter(business_id=business_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if min_price:
            qs = qs.filter(original_price__gte=min_price)
        if max_price:
            qs = qs.filter(original_price__lte=max_price)
        if has_discount:
            qs = qs.filter(discount_percent__gt=0)

        if query and len(query) >= cls.MIN_QUERY_LENGTH:
            # تلاش برای استفاده از TrigramSimilarity
            if _is_postgres() and _pg_trgm_available():
                try:
                    from django.contrib.postgres.search import TrigramSimilarity
                    qs = qs.annotate(
                        similarity=TrigramSimilarity('name', query)
                    ).filter(similarity__gt=0.1).order_by('-similarity')
                except Exception as e:
                    logger.warning(
                        f"TrigramSimilarity failed, falling back to icontains: {e}"
                    )
                    qs = qs.filter(
                        Q(name__icontains=query) | Q(description__icontains=query)
                    ).order_by('-created_at')
            else:
                qs = qs.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).order_by('-created_at')
        else:
            qs = qs.order_by('-created_at')

        return qs.select_related('business', 'category')[:limit]

    @classmethod
    def global_search(cls, query, user=None, limit_per_type=5):
        """
        جستجوی کلی در کسب‌وکارها و خدمات
        
        Args:
            query: عبارت جستجو
            user: کاربر (برای ذخیره تاریخچه)
            limit_per_type: حداکثر تعداد نتایج برای هر نوع
            
        Returns:
            dict با کلیدهای businesses, services, total
        """
        if not query or len(query) < cls.MIN_QUERY_LENGTH:
            return {'businesses': [], 'services': [], 'total': 0}

        businesses = list(cls.search_businesses(query, limit=limit_per_type))
        services = list(cls.search_services(query, limit=limit_per_type))

        if user:
            cls._save_history(user, query, len(businesses) + len(services))

        return {
            'businesses': businesses,
            'services': services,
            'total': len(businesses) + len(services),
        }

    @classmethod
    def get_suggestions(cls, query, user=None, limit=10):
        """
        پیشنهادات جستجو (Autocomplete)
        
        Args:
            query: عبارت جستجو
            user: کاربر (برای نمایش تاریخچه)
            limit: حداکثر تعداد پیشنهادات
            
        Returns:
            list از پیشنهادات
        """
        if not query or len(query) < cls.MIN_QUERY_LENGTH:
            return []

        suggestions = set()

        # کسب‌وکارهای مشابه
        businesses = Business.objects.filter(
            status=Business.Status.APPROVED,
            name__icontains=query,
        ).values_list('name', flat=True)[:5]
        suggestions.update(businesses)

        # خدمات مشابه
        services = Service.objects.filter(
            is_active=True,
            name__icontains=query,
        ).values_list('name', flat=True)[:5]
        suggestions.update(services)

        # تاریخچه جستجوی کاربر
        if user:
            history = cls.get_user_history(user, limit=5)
            for h in history:
                if query.lower() in h['query'].lower():
                    suggestions.add(h['query'])

        return list(suggestions)[:limit]

    @classmethod
    def _save_history(cls, user, query, result_count):
        """
        ذخیره تاریخچه جستجو
        
        Args:
            user: کاربر
            query: عبارت جستجو
            result_count: تعداد نتایج
        """
        # حذف جستجوهای قبلی با همان عبارت (برای جلوگیری از تکرار)
        SearchHistory.objects.filter(
            user=user,
            query__iexact=query,
        ).delete()

        # ایجاد رکورد جدید
        SearchHistory.objects.create(
            user=user,
            query=query,
            result_count=result_count,
        )

        # حذف رکوردهای اضافی (حفظ حداکثر MAX_HISTORY_PER_USER)
        keep_ids = list(
            SearchHistory.objects.filter(user=user)
            .order_by('-created_at')
            .values_list('id', flat=True)[:cls.MAX_HISTORY_PER_USER]
        )
        if keep_ids:
            SearchHistory.objects.filter(user=user).exclude(
                id__in=keep_ids
            ).delete()

    @classmethod
    def get_user_history(cls, user, limit=20):
        """
        دریافت تاریخچه جستجوی کاربر
        
        Args:
            user: کاربر
            limit: حداکثر تعداد رکوردها
            
        Returns:
            list از تاریخچه جستجوها
        """
        return list(
            SearchHistory.objects.filter(user=user)
            .order_by('-created_at')
            .values('id', 'query', 'result_count', 'created_at')[:limit]
        )

    @classmethod
    def clear_user_history(cls, user):
        """
        پاک کردن کل تاریخچه جستجوی کاربر
        
        Args:
            user: کاربر
            
        Returns:
            tuple: (تعداد حذف شده, dict)
        """
        return SearchHistory.objects.filter(user=user).delete()

    @classmethod
    def search_nearby(cls, lat, lng, radius_km=10, category_id=None):
        """
        جستجوی ترکیبی نزدیک‌ترین‌ها
        
        کسب‌وکارها + مدلینگ + لاین را همزمان برمی‌گرداند
        
        Args:
            lat: عرض جغرافیایی
            lng: طول جغرافیایی
            radius_km: شعاع جستجو (کیلومتر)
            category_id: فیلتر دسته‌بندی
            
        Returns:
            dict با کلیدهای businesses, model_requests, line_rentals
        """
        from django.contrib.gis.geos import Point
        from django.contrib.gis.measure import D
        from apps.ads.models import ModelRequest, LineRental

        point = Point(lng, lat, srid=4326)
        distance_filter = D(km=radius_km)

        # کسب‌وکارها
        businesses = Business.objects.filter(
            status=Business.Status.APPROVED,
            is_active=True,
            location__distance_lte=(point, distance_filter),
        ).distance(point).order_by('distance')[:20]

        if category_id:
            businesses = businesses.filter(category_id=category_id)

        # مدلینگ‌ها
        model_requests = ModelRequest.objects.filter(
            business__status='approved',
            business__is_active=True,
            location__distance_lte=(point, distance_filter),
        ).distance(point).order_by('distance')[:10]

        # لاین‌ها
        line_rentals = LineRental.objects.filter(
            business__status='approved',
            business__is_active=True,
            location__distance_lte=(point, distance_filter),
        ).distance(point).order_by('distance')[:10]

        return {
            'businesses': list(businesses),
            'model_requests': list(model_requests),
            'line_rentals': list(line_rentals),
        }