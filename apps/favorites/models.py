"""
علاقه‌مندی‌ها
"""
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel


class FavoriteBusiness(BaseModel):
    """علاقه‌مندی به کسب‌وکار"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_businesses',
        verbose_name='کاربر',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='کسب‌وکار',
    )

    class Meta:
        db_table = 'favorite_businesses'
        verbose_name = '❤️ علاقه‌مندی به کسب‌وکار'
        verbose_name_plural = '❤️ علاقه‌مندی‌ها به کسب‌وکارها'
        unique_together = ['user', 'business']

    def __str__(self):
        return f'{self.user.phone} ❤️ {self.business.name}'


