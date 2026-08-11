"""
سرویس مدیریت نظرات و امتیازات
✅ بهینه‌شده: Conditional Aggregation و update() به جای save()
"""
import logging
from django.db import transaction
from django.db.models import Avg, Count, Case, When, Value, IntegerField
from django.utils import timezone
from apps.reviews.models import Review, ReviewResponse, ReviewTag
from apps.bookings.models import Appointment
from apps.businesses.models import Business
from apps.core.exceptions import ZibanoBaseException

logger = logging.getLogger(__name__)


class ReviewException(ZibanoBaseException):
    default_message = 'خطا در ثبت نظر'
    default_code = 'REVIEW_ERROR'


class ReviewNotAllowedException(ReviewException):
    default_message = 'شما مجاز به ثبت نظر برای این نوبت نیستید'
    default_code = 'REVIEW_NOT_ALLOWED'


class ReviewAlreadyExistsException(ReviewException):
    default_message = 'شما قبلاً برای این نوبت نظر ثبت کرده‌اید'
    default_code = 'REVIEW_ALREADY_EXISTS'


class AppointmentNotCompletedException(ReviewException):
    default_message = 'فقط برای نوبت‌های انجام‌شده می‌توانید نظر ثبت کنید'
    default_code = 'APPOINTMENT_NOT_COMPLETED'


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
        tag_ids: list = None,
    ) -> Review:
        """ایجاد نظر جدید"""
        if not (1 <= rating <= 5):
            raise ReviewException(
                message='امتیاز باید بین ۱ تا ۵ باشد',
                code='INVALID_RATING',
            )

        try:
            appointment = Appointment.objects.select_related(
                'customer', 'business', 'service'
            ).get(id=appointment_id)
        except Appointment.DoesNotExist:
            raise ReviewException(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
            )

        if not cls.can_review(customer, appointment):
            if appointment.customer != customer:
                raise ReviewNotAllowedException()
            elif appointment.status != Appointment.Status.DONE:
                raise AppointmentNotCompletedException()
            else:
                raise ReviewAlreadyExistsException()

        if comment and len(comment) > 500:
            raise ReviewException(
                message='متن نظر نمی‌تواند بیشتر از ۵۰۰ کاراکتر باشد',
                code='COMMENT_TOO_LONG',
            )

        review = Review.objects.create(
            customer=customer,
            appointment=appointment,
            business=appointment.business,
            service=appointment.service,
            rating=rating,
            comment=comment.strip() if comment else '',
            is_approved=True,
        )

        if tag_ids:
            tags = ReviewTag.objects.filter(id__in=tag_ids, is_active=True)
            review.tags.set(tags)

        cls._update_business_stats(appointment.business)
        cls._notify_business(review)

        logger.info(
            f"Review created: customer={customer.phone}, "
            f"business={appointment.business.name}, rating={rating}"
        )
        return review

    @classmethod
    @transaction.atomic
    def create_business_response(
        cls,
        business: Business,
        review_id: int,
        text: str,
    ) -> ReviewResponse:
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

        if ReviewResponse.objects.filter(review=review).exists():
            raise ReviewException(
                message='شما قبلاً به این نظر پاسخ داده‌اید',
                code='RESPONSE_ALREADY_EXISTS',
            )

        if not text or len(text.strip()) < 10:
            raise ReviewException(
                message='متن پاسخ باید حداقل ۱۰ کاراکتر باشد',
                code='RESPONSE_TOO_SHORT',
            )

        if len(text) > 500:
            raise ReviewException(
                message='متن پاسخ نمی‌تواند بیشتر از ۵۰۰ کاراکتر باشد',
                code='RESPONSE_TOO_LONG',
            )

        response = ReviewResponse.objects.create(
            review=review,
            business=business,
            text=text.strip(),
        )

        cls._notify_customer_response(review, response)

        logger.info(
            f"Business response created: business={business.name}, review={review.id}"
        )
        return response

    @classmethod
    @transaction.atomic
    def update_business_response(
        cls,
        business: Business,
        review_id: int,
        text: str,
    ) -> ReviewResponse:
        """ویرایش پاسخ کسب‌وکار"""
        try:
            response = ReviewResponse.objects.select_related(
                'review', 'review__business'
            ).get(review_id=review_id)
        except ReviewResponse.DoesNotExist:
            raise ReviewException(
                message='پاسخ مورد نظر یافت نشد',
                code='RESPONSE_NOT_FOUND',
            )

        if response.review.business != business:
            raise ReviewException(
                message='این پاسخ متعلق به کسب‌وکار شما نیست',
                code='RESPONSE_NOT_YOURS',
            )

        if not text or len(text.strip()) < 10:
            raise ReviewException(
                message='متن پاسخ باید حداقل ۱۰ کاراکتر باشد',
                code='RESPONSE_TOO_SHORT',
            )

        if len(text) > 500:
            raise ReviewException(
                message='متن پاسخ نمی‌تواند بیشتر از ۵۰۰ کاراکتر باشد',
                code='RESPONSE_TOO_LONG',
            )

        response.text = text.strip()
        response.save(update_fields=['text', 'updated_at'])
        return response

    @classmethod
    @transaction.atomic
    def delete_business_response(
        cls,
        business: Business,
        review_id: int,
    ) -> None:
        """حذف پاسخ کسب‌وکار"""
        try:
            response = ReviewResponse.objects.select_related(
                'review', 'review__business'
            ).get(review_id=review_id)
        except ReviewResponse.DoesNotExist:
            raise ReviewException(
                message='پاسخ مورد نظر یافت نشد',
                code='RESPONSE_NOT_FOUND',
            )

        if response.review.business != business:
            raise ReviewException(
                message='این پاسخ متعلق به کسب‌وکار شما نیست',
                code='RESPONSE_NOT_YOURS',
            )

        response.delete()

    @classmethod
    def _update_business_stats(cls, business: Business) -> None:
        """
        ✅ بهینه: استفاده از update() به جای save()
        یک کوئری به جای دو کوئری
        """
        stats = Review.objects.filter(
            business=business,
            is_approved=True,
            is_hidden=False,
        ).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id'),
        )

        # ✅ update() یک کوئری است، save() دو کوئری
        Business.objects.filter(id=business.id).update(
            rating_avg=stats['avg_rating'] or 0,
            rating_count=stats['count'] or 0,
        )

        # بروزرسانی instance cache
        business.rating_avg = stats['avg_rating'] or 0
        business.rating_count = stats['count'] or 0

    @classmethod
    def _notify_business(cls, review: Review) -> None:
        """ارسال نوتیفیکیشن به کسب‌وکار"""
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                user=review.business.owner,
                type='new_review',
                title='نظر جدید دریافت شد',
                body=f'{review.customer.full_name or review.customer.phone} '
                     f'به کسب‌وکار شما {review.rating} ستاره داد',
                data={'review_id': review.id, 'rating': review.rating},
            )
        except Exception as e:
            logger.error(f"Failed to send review notification: {e}")

    @classmethod
    def _notify_customer_response(
        cls,
        review: Review,
        response: ReviewResponse,
    ) -> None:
        """ارسال نوتیفیکیشن به مشتری"""
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                user=review.customer,
                type='business_response',
                title=f'پاسخ {review.business.name} به نظر شما',
                body=response.text[:100] + '...' if len(response.text) > 100 else response.text,
                data={'review_id': review.id, 'business_id': review.business.id},
            )
        except Exception as e:
            logger.error(f"Failed to send response notification: {e}")

    @classmethod
    def get_business_reviews(
        cls,
        business: Business,
        page: int = 1,
        page_size: int = 10,
        rating_filter: int = None,
    ) -> dict:
        """
        ✅ بهینه: Conditional Aggregation برای توزیع امتیازات
        ۳ کوئری به جای ۸ کوئری
        """
        queryset = Review.objects.filter(
            business=business,
            is_approved=True,
            is_hidden=False,
        ).select_related(
            'customer', 'service', 'response'
        ).prefetch_related('tags').order_by('-created_at')

        if rating_filter and 1 <= rating_filter <= 5:
            queryset = queryset.filter(rating=rating_filter)

        # Pagination
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        reviews = queryset[start:end]

        # ✅ محاسبه توزیع امتیازات + میانگین در یک کوئری
        stats = Review.objects.filter(
            business=business,
            is_approved=True,
            is_hidden=False,
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
    def get_user_reviews(
        cls,
        user,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """دریافت نظرات ثبت‌شده توسط کاربر"""
        queryset = Review.objects.filter(
            customer=user,
        ).select_related(
            'business', 'service', 'response'
        ).prefetch_related('tags').order_by('-created_at')

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        reviews = queryset[start:end]

        return {
            'reviews': list(reviews),
            'total': total,
            'page': page,
            'page_size': page_size,
        }