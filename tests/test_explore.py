"""
تست‌های ویترین / اکسپلور
"""
import pytest
from django.urls import reverse

from apps.explore.models import ExplorePost, PostImage


@pytest.mark.django_db
class TestExplorePosts:
    def test_create_post(self, approved_business):
        post = ExplorePost.objects.create(
            business=approved_business,
            caption='نمونه کار جدید',
        )
        assert post.is_pinned is False

    def test_post_with_images(self, approved_business):
        post = ExplorePost.objects.create(
            business=approved_business,
            caption='تست',
        )
        assert post.images.count() == 0