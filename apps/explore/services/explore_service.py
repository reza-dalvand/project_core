"""
سرویس ویترین / اکسپلور
"""
import logging
from django.db.models import Q

from apps.explore.models import ExplorePost, PostImage

logger = logging.getLogger(__name__)


class ExploreService:
    """سرویس مدیریت پست‌های ویترین"""

    @classmethod
    def get_explore_posts(
        cls,
        category_id=None,
        business_id=None,
        limit=20,
        offset=0,
    ):
        """دریافت پست‌های ویترین"""
        qs = ExplorePost.objects.filter(
            business__status='approved',
            business__is_active=True,
        ).select_related(
            'business', 'main_category', 'sub_category',
        ).prefetch_related('images').order_by('-is_pinned', '-created_at')

        if category_id:
            qs = qs.filter(main_category_id=category_id)

        if business_id:
            qs = qs.filter(business_id=business_id)

        return qs[offset:offset + limit]

    @classmethod
    def get_post_detail(cls, post_id: int):
        """دریافت جزئیات پست"""
        try:
            return ExplorePost.objects.select_related(
                'business', 'main_category', 'sub_category',
            ).prefetch_related('images').get(id=post_id)
        except ExplorePost.DoesNotExist:
            return None

    @classmethod
    def create_post(
        cls,
        business,
        caption: str,
        main_category_id=None,
        sub_category_id=None,
        source='business',
    ) -> ExplorePost:
        """ایجاد پست جدید"""
        post = ExplorePost.objects.create(
            business=business,
            caption=caption,
            main_category_id=main_category_id,
            sub_category_id=sub_category_id,
            source=source,
        )
        return post

    @classmethod
    def add_post_image(cls, post, image, sort_order=0) -> PostImage:
        """افزودن تصویر به پست"""
        return PostImage.objects.create(
            post=post,
            image=image,
            sort_order=sort_order,
        )