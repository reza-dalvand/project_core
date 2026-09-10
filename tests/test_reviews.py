"""
تست‌های نظرات — ساده‌سازی شده
منطق جدید:
- هر مشتری فقط یک‌بار برای هر کسب‌وکار نظر می‌دهد
- امتیاز (rating) به‌صورت خودکار از لایک/دیسلایک تگ‌ها محاسبه می‌شود
- حداقل ۱ دقیقه پس از انجام خدمت (done_at) امکان ثبت نظر فعال می‌شود
"""
import pytest
from datetime import time, timedelta
import jdatetime
from django.urls import reverse
from django.utils import timezone
from apps.reviews.models import Review, ReviewTagVote


@pytest.fixture
def completed_appointment(customer_user, approved_business, test_service):
    """نوبت انجام‌شده با زمان انجام (بیشتر از ۱ دقیقه پیش)"""
    from apps.appointments.models import Appointment
    future_date = jdatetime.date.today() + jdatetime.timedelta(days=30)
    return Appointment.objects.create(
        business=approved_business,
        service=test_service,
        customer=customer_user,
        jy=future_date.year,
        jm=future_date.month,
        jd=future_date.day,
        time_slot=time(10, 0),
        status=Appointment.Status.DONE,
        total_price=450000,
        # ✅ FIX: done_at باید تنظیم شود و حداقل ۱ دقیقه از آن گذشته باشد
        done_at=timezone.now() - timedelta(minutes=5),
    )


@pytest.mark.django_db
class TestReviewService:
    def test_can_review(self, customer_user, completed_appointment):
        from apps.reviews.services.review_service import ReviewService
        assert ReviewService.can_review(customer_user, completed_appointment) is True

    def test_can_review_not_done(self, customer_user, test_appointment):
        """نوبت RESERVED امکان نظردهی ندارد"""
        from apps.reviews.services.review_service import ReviewService
        assert ReviewService.can_review(customer_user, test_appointment) is False

    def test_can_review_wrong_user(self, business_owner_user, completed_appointment):
        """کاربر دیگری نمی‌تواند برای نوبت این کاربر نظر بدهد"""
        from apps.reviews.services.review_service import ReviewService
        assert ReviewService.can_review(business_owner_user, completed_appointment) is False

    def test_can_review_duplicate(self, customer_user, completed_appointment):
        """نمی‌توان دو بار برای یک کسب‌وکار نظر ثبت کرد"""
        from apps.reviews.services.review_service import ReviewService
        ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            comment='عالی',
            tag_votes=[],
        )
        assert ReviewService.can_review(customer_user, completed_appointment) is False

    def test_create_review(self, customer_user, completed_appointment):
        from apps.reviews.services.review_service import ReviewService
        review = ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            comment='عالی بود',
            tag_votes=[
                {'tag_id': 'clean', 'vote_type': 'like'},
                {'tag_id': 'punctual', 'vote_type': 'like'},
            ],
        )
        assert review is not None
        # ✅ ۲ لایک، ۰ دیسلایک → ratio=1.0 → rating=round(1+4)=5
        assert review.rating == 5
        assert review.comment == 'عالی بود'
        assert review.appointment == completed_appointment
        # بررسی ایجاد رای‌های تگ
        assert ReviewTagVote.objects.filter(review=review).count() == 2

    def test_create_review_auto_rating_mixed(self, customer_user, completed_appointment):
        """امتیاز خودکار: ۱ لایک و ۱ دیسلایک → rating=3"""
        from apps.reviews.services.review_service import ReviewService
        review = ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            comment='متوسط بود',
            tag_votes=[
                {'tag_id': 'clean', 'vote_type': 'like'},
                {'tag_id': 'punctual', 'vote_type': 'dislike'},
            ],
        )
        # ratio = 1/2 = 0.5 → round(1 + 0.5*4) = round(3.0) = 3
        assert review.rating == 3

    def test_create_review_no_votes_default_rating(self, customer_user, completed_appointment):
        """بدون رای تگ، امتیاز پیش‌فرض ۳ است"""
        from apps.reviews.services.review_service import ReviewService
        review = ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            comment='بدون رای تگ',
            tag_votes=[],
        )
        assert review.rating == 3

    def test_create_review_updates_appointment_has_review(
        self, customer_user, completed_appointment
    ):
        """پس از ثبت نظر، فیلد has_review نوبت باید True شود"""
        from apps.reviews.services.review_service import ReviewService
        ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            comment='خوب بود',
        )
        completed_appointment.refresh_from_db()
        assert completed_appointment.has_review is True

    def test_create_reply(
        self, business_owner_user, approved_business,
        customer_user, completed_appointment
    ):
        from apps.reviews.services.review_service import ReviewService
        review = ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            comment='خوب بود',
        )
        reply = ReviewService.create_business_reply(
            business=approved_business,
            review_id=review.id,
            reply_text='ممنون از نظر شما. خوشحالیم که راضی بودید.',
        )
        assert reply is not None
        assert reply.reply == 'ممنون از نظر شما. خوشحالیم که راضی بودید.'
        assert reply.replied_at is not None


@pytest.mark.django_db
class TestReviewAPI:
    def test_create_review_api(
        self, authenticated_customer_client, completed_appointment
    ):
        url = reverse('reviews:create-review')
        response = authenticated_customer_client.post(url, {
            'appointment_id': completed_appointment.id,
            'comment': 'فوق‌العاده بود',
            'tag_votes': [
                {'tag_id': 'clean', 'vote_type': 'like'},
            ],
        }, format='json')
        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert data['data']['rating'] == 5
        assert data['data']['comment'] == 'فوق‌العاده بود'

    def test_create_review_api_without_tag_votes(
        self, authenticated_customer_client, completed_appointment
    ):
        """ثبت نظر بدون رای تگ — باید با امتیاز پیش‌فرض ۳ ثبت شود"""
        url = reverse('reviews:create-review')
        response = authenticated_customer_client.post(url, {
            'appointment_id': completed_appointment.id,
            'comment': 'معمولی بود',
        }, format='json')
        assert response.status_code == 201
        assert response.json()['data']['rating'] == 3

    def test_create_review_api_duplicate(
        self, authenticated_customer_client, completed_appointment
    ):
        """ثبت نظر دوم برای یک کسب‌وکار باید خطا بدهد"""
        url = reverse('reviews:create-review')
        data = {
            'appointment_id': completed_appointment.id,
            'comment': 'نظر اول',
        }
        response1 = authenticated_customer_client.post(url, data, format='json')
        assert response1.status_code == 201

        response2 = authenticated_customer_client.post(url, data, format='json')
        assert response2.status_code == 400

    def test_business_reviews_api(
        self, authenticated_customer_client, completed_appointment,
        approved_business
    ):
        url = reverse(
            'reviews:business-reviews',
            kwargs={'business_id': approved_business.id},
        )
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200

    def test_can_review_api(self, authenticated_customer_client, completed_appointment):
        """بررسی امکان نظردهی از طریق API"""
        url = reverse(
            'reviews:can-review',
            kwargs={'appointment_id': completed_appointment.id},
        )
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        assert response.json()['data']['can_review'] is True

    def test_can_review_api_not_done(self, authenticated_customer_client, test_appointment):
        """نوبت رزرو شده امکان نظردهی ندارد"""
        url = reverse(
            'reviews:can-review',
            kwargs={'appointment_id': test_appointment.id},
        )
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        assert response.json()['data']['can_review'] is False