"""
Review Service — مدیریت نظرات و امتیازات
منطق جدید: هر مشتری فقط یکبار برای هر کسب‌وکار نظر می‌دهد (اختیاری)
"""
import logging
from django.db import transaction
from django.db.models import Avg, Count, Case, When, IntegerField
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
    def has_reviewed_business(cls, user, business) -> bool:
        """آیا کاربر قبلاً برای این کسب‌وکار نظر ثبت کرده است؟"""
        return Review.objects.filter(
            customer=user,
            business=business,
        ).exists()

    @classmethod
    def can_review(cls, user, appointment) -> bool:
        """
        بررسی امکان ثبت نظر
        قوانین:
        - نوبت باید DONE باشد
        - حداقل ۱ دقیقه از done_at گذشته باشد (برای تست)
        - کاربر قبلاً برای این کسب‌وکار نظر نداده باشد
        """
        if appointment.customer != user:
            return False
        if appointment.status != Appointment.Status.DONE:
            return False
        if not appointment.done_at:
            return False

        # بررسی ۱ دقیقه بعد از انجام خدمت (done_at)
        from datetime import timedelta
        from django.utils import timezone as django_timezone
        now = django_timezone.now()
        if now < appointment.done_at + timedelta(minutes=1):
            return False

        # ✅ قانون جدید: اگر قبلاً برای این کسب‌وکار نظر داده، مجاز نیست
        if cls.has_reviewed_business(user, appointment.business):
            return False

        return True

    @classmethod
    @transaction.atomic
    def create_review(
        cls,
        customer,
        appointment_id: int,
        comment: str = '',
        tag_votes: list = None,
    ) -> Review:
        """ایجاد نظر جدید — فقط یکبار برای هر کسب‌وکار"""
        from apps.reviews.models import ReviewTagVote

        try:
            appointment = Appointment.objects.select_related(
                'customer', 'business', 'service',
            ).get(id=appointment_id)
        except Appointment.DoesNotExist:
            raise ReviewException(message='نوبت مورد نظر یافت نشد', code='APPOINTMENT_NOT_FOUND')

        if not cls.can_review(customer, appointment):
            if appointment.customer != customer:
                raise ReviewException(message='شما مجاز به ثبت نظر برای این نوبت نیستید', code='REVIEW_NOT_ALLOWED')
            elif appointment.status != Appointment.Status.DONE:
                raise AppointmentNotCompletedException()
            elif cls.has_reviewed_business(customer, appointment.business):
                raise ReviewException(
                    message='شما قبلاً برای این کسب‌وکار نظر ثبت کرده‌اید',
                    code='REVIEW_ALREADY_EXISTS_FOR_BUSINESS',
                )
            else:
                raise ReviewAlreadyExistsException()

        if comment and len(comment) > 300:
            raise ReviewException(message='متن نظر نمی‌تواند بیشتر از ۳۰۰ کاراکتر باشد', code='COMMENT_TOO_LONG')

        # محاسبه خودکار ستاره (Rating) بر اساس لایک/دیسلایک‌ها
        tag_votes = tag_votes or []
        likes = sum(1 for v in tag_votes if v.get('vote_type') == 'like')
        dislikes = sum(1 for v in tag_votes if v.get('vote_type') == 'dislike')
        total_votes = likes + dislikes

        if total_votes > 0:
            ratio = likes / total_votes
            rating = round(1 + (ratio * 4))
        else:
            rating = 3

        # ✅ ایجاد نظر جدید (بدون آپدیت قبلی)
        review = Review.objects.create(
            business=appointment.business,
            service=appointment.service,
            appointment=appointment,
            customer=customer,
            rating=rating,
            comment=comment.strip() if comment else '',
            tags=[],
        )

        # ثبت رای‌های تگ
        for vote in tag_votes:
            ReviewTagVote.objects.create(
                review=review,
                tag_id=vote['tag_id'],
                vote_type=vote['vote_type'],
                user=customer,
            )

        # بروزرسانی وضعیت نوبت
        appointment.has_review = True
        appointment.save(update_fields=['has_review'])

        cls._update_business_stats(appointment.business)
        cls._notify_business(review)

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
        """دریافت نظرات کسب‌وکار"""
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
        """
        بروزرسانی آمار کسب‌وکار
        
        ✅ قانون جدید:
        - قبل از ۳ رای: امتیاز پیش‌فرض ۵.۰ نمایش داده می‌شود
        - بعد از ۳ رای: میانگین واقعی نظرات محاسبه می‌شود
        """
        MIN_REVIEWS_THRESHOLD = 3
        DEFAULT_RATING = 5.0

        stats = Review.objects.filter(
            business=business,
        ).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id'),
        )

        count = stats['count'] or 0
        avg = stats['avg_rating'] or 0

        business.reviews_count = count
        
        # ✅ اگر کمتر از ۳ رای باشد، امتیاز پیش‌فرض ۵.۰
        if count < MIN_REVIEWS_THRESHOLD:
            business.rating = DEFAULT_RATING
        else:
            business.rating = avg
        
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