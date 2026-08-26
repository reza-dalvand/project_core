"""
ویترین / اکسپلور
"""
from django.db import models

from apps.core.models import BaseModel


class ExplorePost(BaseModel):
    """پست ویترین"""

    class Source(models.TextChoices):
        BUSINESS = 'business', 'کسب‌وکار'
        MAGAZINE = 'magazine', 'مجله بیو کلاب'

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='کسب‌وکار',
    )
    source = models.CharField(
        'منبع',
        max_length=20,
        choices=Source.choices,
        default=Source.BUSINESS,
    )
    caption = models.TextField('کپشن', max_length=500)
    main_category = models.ForeignKey(
        'categories.ServiceCategory',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='دسته‌بندی اصلی',
    )
    sub_category = models.ForeignKey(
        'categories.SubService',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='زیردسته',
    )
    is_pinned = models.BooleanField('پین شده', default=False)

    class Meta:
        db_table = 'explore_posts'
        verbose_name = '🔍 پست ویترین'
        verbose_name_plural = '🔍 پست‌های ویترین'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f'{self.business.name} - {self.caption[:50]}'


class PostImage(BaseModel):
    """تصاویر پست"""

    post = models.ForeignKey(
        ExplorePost,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='پست',
    )
    image = models.ImageField(
        'تصویر',
        upload_to='explore/posts/',
    )
    sort_order = models.IntegerField('ترتیب', default=0)

    class Meta:
        db_table = 'post_images'
        verbose_name = '🖼️ تصویر پست'
        verbose_name_plural = '🖼️ تصاویر پست'
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.post.business.name} - تصویر {self.sort_order}'