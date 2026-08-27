"""
استان و شهر
"""
from django.db import models
from django.utils.text import slugify

from apps.core.models import BaseModel


class Province(BaseModel):
    """استان"""

    name = models.CharField('نام', max_length=50)
    slug = models.SlugField('اسلاگ', unique=True)

    class Meta:
        db_table = 'provinces'
        verbose_name = '📍 استان'
        verbose_name_plural = '📍 استان‌ها'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class City(BaseModel):
    """شهر"""

    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name='cities',
        verbose_name='استان',
    )
    name = models.CharField('نام', max_length=50)
    slug = models.SlugField('اسلاگ')

    class Meta:
        db_table = 'cities'
        verbose_name = '🏙️ شهر'
        verbose_name_plural = '🏙️ شهرها'
        unique_together = ['province', 'slug']

    def __str__(self):
        return f'{self.province.name} > {self.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)