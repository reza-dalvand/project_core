"""
Review Service — مدیریت نظرات و امتیازات
ساده‌سازی شده با reply در خود Review
"""
import logging
from django.db import transaction
from django.db.models import Avg, Count, Case, When, Value, IntegerField
from django.utils import timezone

from apps.reviews.models import Review
from apps.appointments.models import Appointment

from apps.core.exceptions import (
    ReviewException,
    ReviewAlreadyExistsException,
    AppointmentNotCompletedException,
)

logger = logging.getLogger(__name__)


class ReviewService:
    """سرویس مدیریت نظرات"""

    @classmethod
    def can_review(cls, user, appointment) -> bool:
        """بررسی امکان ثبت نظر"""
        if appointment.customer != user:
            return False
        if appointment.status != Appointment.Status.DONE:
            return False
        if Review.objects.filter(appointment=appointment).exists():
            return False
        return True

    @classmethod
    @transaction.atomic
    def create_review(
        cls,
        customer,
        appointment_id: int,
        rating: int,
        comment: str = '',
        tags: list = None,
    ) -> Review:
        """ایجاد نظر جدید"""
        if not (1 <= rating <= 5):
            raise ReviewException(
                message='امتیاز باید بین ۱ تا ۵ باشد',
                code='INVALID_RATING',
            )

        try:
            appointment = Appointment.objects.select_related(
                'customer', 'business', 'service',
            ).get(id=appointment_id)
        except Appointment.DoesNotExist:
            raise ReviewException(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
            )

        if not cls.can_review(customer, appointment):
            if appointment.customer != customer:
                raise ReviewException(
                    message='شما مجاز به ثبت نظر برای این نوبت نیستید',
                    code='REVIEW_NOT_ALLOWED',
                )
            elif appointment.status != Appointment.Status.DONE:
                raise AppointmentNotCompletedException()
            else:
                raise ReviewAlreadyExistsException()

        if comment and len(comment) > 300:
            raise ReviewException(
                message='متن نظر نمی‌تواند بیشتر از ۳۰۰ کاراکتر باشد',
                code='COMMENT_TOO_LONG',
            )

        review = Review.objects.create(
            business=appointment.business,
            service=appointment.service,
            appointment=appointment,
            customer=customer,
            rating=rating,
            comment=comment.strip() if comment else '',
            tags=tags or [],
        )

        # بروزرسانی آمار کسب‌وکار
        cls._update_business_stats(appointment.business)

        # ارسال نوتیفیکیشن
        cls._notify_business(review)

        logger.info(
            f"Review created: customer={customer.phone}, "
            f"business={appointment.business.name}, rating={rating}"
        )

        return review

    @classmethod
    @transaction.atomic
    def create_business_reply(
        cls,
        business,
        review_id: int,
        reply_text: str,
    ) -> Review:
        """ثبت پاسخ کسب‌وکار به نظر"""
        try:
            review = Review.objects.select_related('business').get(id=review_id)
        except Review.DoesNotExist:
            raise ReviewException(
                message='نظر مورد نظر یافت نشد',
                code='REVIEW_NOT_FOUND',
            )

        if review.business != business:
            raise ReviewException(
                message='این نظر متعلق به کسب‌وکار شما نیست',
                code='REVIEW_NOT_YOURS',
            )

        if review.reply:
            raise ReviewException(
                message='شما قبلاً به این نظر پاسخ داده‌اید',
                code='REPLY_ALREADY_EXISTS',
            )

        if not reply_text or len(reply_text.strip()) < 10:
            raise ReviewException(
                message='متن پاسخ باید حداقل ۱۰ کاراکتر باشد',
                code='REPLY_TOO_SHORT',
            )

        if len(reply_text) > 300:
            raise ReviewException(
                message='متن پاسخ نمی‌تواند بیشتر از ۳۰۰ کاراکتر باشد',
                code='REPLY_TOO_LONG',
            )

        review.reply = reply_text.strip()
        review.replied_at = timezone.now()
        review.save(update_fields=['reply', 'replied_at'])

        logger.info(
            f"Business reply created: business={business.name}, review={review.id}"
        )

        return review

    @classmethod
    def get_business_reviews(
        cls,
        business,
        page: int = 1,
        page_size: int = 10,
        rating_filter: int = None,
    ) -> dict:
        """
        دریافت نظرات کسب‌وکار
        با Conditional Aggregation برای توزیع امتیازات
        """
        queryset = Review.objects.filter(
            business=business,
        ).select_related(
            'customer', 'service',
        ).order_by('-created_at')

        if rating_filter and 1 <= rating_filter <= 5:
            queryset = queryset.filter(rating=rating_filter)

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        reviews = queryset[start:end]

        # محاسبه توزیع امتیازات + میانگین در یک کوئری
        stats = Review.objects.filter(
            business=business,
        ).aggregate(
            avg_rating=Avg('rating'),
            **{
                f'rating_{i}': Count(
                    Case(When(rating=i, then=1), output_field=IntegerField())
                )
                for i in range(1, 6)
            }
        )

        rating_distribution = {
            i: stats[f'rating_{i}'] or 0
            for i in range(1, 6)
        }

        return {
            'reviews': list(reviews),
            'total': total,
            'page': page,
            'page_size': page_size,
            'avg_rating': float(stats['avg_rating'] or 0),
            'rating_distribution': rating_distribution,
        }

    @classmethod
    def _update_business_stats(cls, business) -> None:
        """بروزرسانی آمار کسب‌وکار"""
        stats = Review.objects.filter(
            business=business,
        ).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id'),
        )

        business.rating = stats['avg_rating'] or 0
        business.reviews_count = stats['count'] or 0
        business.save(update_fields=['rating', 'reviews_count'])

    @classmethod
    def _notify_business(cls, review: Review) -> None:
        """ارسال نوتیفیکیشن به کسب‌وکار"""
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                user=review.business.owner,
                type='new_review',
                title='نظر جدید دریافت شد ⭐',
                body=(
                    f'{review.customer.full_name} '
                    f'به کسب‌وکار شما {review.rating} ستاره داد.'
                ),
                data={'review_id': review.id, 'rating': review.rating},
            )
        except Exception as e:
            logger.error(f"Failed to send review notification: {e}")