"""
مدل‌های نظرات و امتیازات
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class ReviewTag(models.Model):
    """تگ‌های آماده برای نظرات"""

    label = models.CharField('عنوان تگ', max_length=50, unique=True)
    icon = models.CharField('آیکون', max_length=50, default='check_circle')
    is_active = models.BooleanField('فعال', default=True)
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = '🏷️ تگ نظر'
        verbose_name_plural = '🏷️ تگ‌های نظر'
        ordering = ['order']

    def __str__(self):
        return self.label


class Review(models.Model):
    """نظر و امتیاز مشتری"""

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='مشتری',
    )
    appointment = models.OneToOneField(
        'bookings.Appointment',
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='نوبت',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        'businesses.Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name='خدمت',
    )

    # ─── امتیاز ───
    rating = models.PositiveSmallIntegerField(
        'امتیاز',
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    # ─── تگ‌ها ───
    tags = models.ManyToManyField(
        ReviewTag,
        related_name='reviews',
        verbose_name='تگ‌ها',
        blank=True,
    )

    # ─── متن نظر ───
    comment = models.TextField(
        'متن نظر',
        blank=True,
        default='',
        max_length=500,
    )

    # ─── وضعیت ───
    is_approved = models.BooleanField('تایید شده', default=True)
    is_hidden = models.BooleanField('مخفی', default=False)

    # ─── تاریخ‌ها ───
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین ویرایش', auto_now=True)

    class Meta:
        verbose_name = '⭐ نظر'
        verbose_name_plural = '⭐ نظرات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business', 'rating']),
            models.Index(fields=['customer']),
            models.Index(fields=['is_approved', 'is_hidden']),
        ]

    def __str__(self):
        return f'{self.customer.phone} - {self.business.name} ({self.rating}★)'


class ReviewResponse(models.Model):
    """پاسخ کسب‌وکار به نظر"""

    review = models.OneToOneField(
        Review,
        on_delete=models.CASCADE,
        related_name='response',
        verbose_name='نظر',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='review_responses',
        verbose_name='کسب‌وکار',
    )
    text = models.TextField('متن پاسخ', max_length=500)
    created_at = models.DateTimeField('تاریخ پاسخ', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین ویرایش', auto_now=True)

    class Meta:
        verbose_name = '💬 پاسخ نظر'
        verbose_name_plural = '💬 پاسخ‌های نظر'
        ordering = ['-created_at']

    def __str__(self):
        return f'پاسخ به نظر {self.review.id}'