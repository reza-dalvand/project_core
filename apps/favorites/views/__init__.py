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
            # ✅ FIX: لیست Portfolioها و ExplorePostهای مورد علاقه
            from apps.favorites.models import FavoritePortfolio, FavoritePost
            from apps.portfolios.models import Portfolio
            from apps.explore.models import ExplorePost
            from apps.explore.serializers import ExplorePostListSerializer
            from apps.portfolios.serializers import PortfolioListSerializer
            
            # Portfolioها
            fav_portfolios = FavoritePortfolio.objects.filter(
                user=request.user,
                portfolio__is_active=True,
            ).select_related(
                'portfolio', 'portfolio__business', 'portfolio__category'
            ).prefetch_related('portfolio__images')
            
            portfolios = [fav.portfolio for fav in fav_portfolios]
            
            if portfolios:
                portfolio_data = PortfolioListSerializer(
                    portfolios, many=True, context={'request': request}
                ).data
                
                # ✅ FIX: تبدیل به فرمت مورد انتظار فرانت با همه تصاویر
                for item in portfolio_data:
                    images_list = []
                    if item.get('images'):
                        images_list = [img.get('image_url') or img.get('image') for img in item['images']]
                    
                    posts_data.append({
                        'id': item.get('id'),
                        'caption': item.get('title', ''),
                        'businessName': item.get('business_name', ''),
                        'businessLogo': item.get('business_logo'),
                        'businessBookingSlug': item.get('business_booking_slug'),
                        'images': images_list,  # ✅ آرایه کامل تصاویر
                        'image': images_list[0] if images_list else None,  # برای backward compatibility
                    })
            
            # ExplorePostها
            fav_posts = FavoritePost.objects.filter(
                user=request.user,
                post__business__is_active=True,
            ).select_related(
                'post', 'post__business', 'post__main_category', 'post__sub_category'
            ).prefetch_related('post__images')
            
            explore_posts = [fav.post for fav in fav_posts]
            
            if explore_posts:
                post_data = ExplorePostListSerializer(
                    explore_posts, many=True, context={'request': request}
                ).data
                
                # ✅ FIX: تبدیل به فرمت مورد انتظار فرانت با همه تصاویر
                for item in post_data:
                    images_list = []
                    if item.get('images'):
                        images_list = [img.get('image_url') or img.get('image') for img in item['images']]
                    
                    posts_data.append({
                        'id': item.get('id'),
                        'caption': item.get('caption', ''),
                        'businessName': item.get('business_name', ''),
                        'businessLogo': item.get('business_logo'),
                        'businessBookingSlug': item.get('business_booking_slug'),
                        'images': images_list,  # ✅ آرایه کامل تصاویر
                        'image': images_list[0] if images_list else None,  # برای backward compatibility
                    })

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
            # ✅ FIX: ابتدا Portfolio را چک کن (ویترین از Portfolio می‌خواند)
            # اگر پیدا نشد، ExplorePost را چک کن
            from apps.portfolios.models import Portfolio
            from apps.explore.models import ExplorePost
            from apps.favorites.models import FavoritePortfolio, FavoritePost
            
            # اول Portfolio را چک کن
            try:
                portfolio = Portfolio.objects.get(id=object_id)
                fav, created = FavoritePortfolio.objects.get_or_create(
                    user=request.user,
                    portfolio=portfolio,
                )

                if not created:
                    fav.delete()
                    return self.success_response(
                        data={'is_favorited': False, 'type': 'portfolio'},
                        message='از علاقه‌مندی‌ها حذف شد',
                    )

                return self.success_response(
                    data={'is_favorited': True, 'type': 'portfolio'},
                    message='به علاقه‌مندی‌ها اضافه شد',
                )
            except Portfolio.DoesNotExist:
                pass

            # اگر Portfolio نبود، ExplorePost را چک کن
            try:
                post = ExplorePost.objects.get(id=object_id)
                fav, created = FavoritePost.objects.get_or_create(
                    user=request.user,
                    post=post,
                )

                if not created:
                    fav.delete()
                    return self.success_response(
                        data={'is_favorited': False, 'type': 'post'},
                        message='از علاقه‌مندی‌ها حذف شد',
                    )

                return self.success_response(
                    data={'is_favorited': True, 'type': 'post'},
                    message='به علاقه‌مندی‌ها اضافه شد',
                )
            except ExplorePost.DoesNotExist:
                return self.error_response(
                    message='پست یافت نشد',
                    code='POST_NOT_FOUND',
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

        # ✅ FIX: شمارش پست‌ها و نمونه‌کارها
        from apps.favorites.models import FavoritePost, FavoritePortfolio
        post_count = FavoritePost.objects.filter(
            user=request.user,
        ).count()
        portfolio_count = FavoritePortfolio.objects.filter(
            user=request.user,
        ).count()

        return self.success_response(
            data={
                'business': business_count,
                'post': post_count + portfolio_count,
                'total': business_count + post_count + portfolio_count,
            },
        )