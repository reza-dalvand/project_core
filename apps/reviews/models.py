"""
نظرات و امتیازات — ساده‌سازی شده
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.core.models import BaseModel


class Review(BaseModel):
    """نظر مشتری"""

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        'services.Service',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviews',
        verbose_name='خدمت',
    )
    appointment = models.OneToOneField(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='نوبت',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='مشتری',
    )

    # ═══════════ امتیاز و نظر ═══════════
    rating = models.IntegerField(
        'امتیاز',
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField('متن نظر', blank=True, max_length=300, default='')
    tags = models.JSONField('تگ‌ها', default=list)  # ['clean', 'punctual', ...]

    # ═══════════ پاسخ سالن ═══════════
    reply = models.TextField('پاسخ سالن', blank=True, default='')
    replied_at = models.DateTimeField('زمان پاسخ', null=True, blank=True)

    class Meta:
        db_table = 'reviews'
        verbose_name = '⭐ نظر'
        verbose_name_plural = '⭐ نظرات'
        ordering = ['-created_at']
        unique_together = ['appointment', 'customer']

    def __str__(self):
        return f'{self.customer.phone} - {self.business.name} ({self.rating}★)'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from django.db.models import Avg
        stats = self.business.reviews.aggregate(
            avg=models.Avg('rating'),
            count=models.Count('id'),
        )
        self.business.reviews_count = stats['count'] or 0
        self.business.rating = stats['avg'] or 0
        self.business.save(update_fields=['reviews_count', 'rating'])


class ReviewTagVote(BaseModel):
    """رای لایک/دیسلایک برای تگ‌های نظر"""
    
    class VoteType(models.TextChoices):
        LIKE = 'like', 'لایک'
        DISLIKE = 'dislike', 'دیسلایک'
    
    review = models.ForeignKey(
        'Review',
        on_delete=models.CASCADE,
        related_name='tag_votes',
        verbose_name='نظر',
    )
    tag_id = models.CharField(
        'شناسه تگ',
        max_length=50,
    )
    vote_type = models.CharField(
        'نوع رای',
        max_length=10,
        choices=VoteType.choices,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_tag_votes',
        verbose_name='کاربر',
    )
    
    class Meta:
        db_table = 'review_tag_votes'
        verbose_name = '👍 رای تگ نظر'
        verbose_name_plural = '👍 رای‌های تگ نظرات'
        unique_together = ['review', 'tag_id', 'user']
    
    def __str__(self):
        return f'{self.user.phone} - {self.tag_id} ({self.vote_type})'