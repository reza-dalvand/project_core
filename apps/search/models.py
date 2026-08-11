"""
جستجوی یکپارچه
"""
from django.db import models
from django.conf import settings

from apps.core.models import BaseModel


class SearchHistory(BaseModel):
    """تاریخچه جستجوهای کاربر"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='search_history',
        verbose_name='کاربر',
    )
    query = models.CharField('عبارت جستجو', max_length=200, db_index=True)
    result_count = models.PositiveIntegerField('تعداد نتایج', default=0)
    category = models.CharField(
        'دسته‌بندی جستجو',
        max_length=50,
        blank=True,
        default='',
        help_text='مثلاً: businesses, services, posts',
    )

    class Meta:
        db_table = 'search_history'
        verbose_name = '🔍 تاریخچه جستجو'
        verbose_name_plural = '🔍 تاریخچه جستجوها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['query']),
        ]

    def __str__(self):
        return f'{self.user.phone} - "{self.query}"'