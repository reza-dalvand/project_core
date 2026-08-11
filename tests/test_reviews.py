"""
تست‌های نظرات — ساده‌سازی شده
"""
import pytest
from django.urls import reverse

from apps.reviews.models import Review


@pytest.fixture
def completed_appointment(customer_user, approved_business, test_service):
    from apps.appointments.models import Appointment
    from datetime import time
    return Appointment.objects.create(
        business=approved_business,
        service=test_service,
        customer=customer_user,
        jy=1405, jm=4, jd=22,
        time_slot=time(10, 0),
        status=Appointment.Status.DONE,
        total_price=450000,
    )


@pytest.mark.django_db
class TestReviewService:
    def test_can_review(self, customer_user, completed_appointment):
        from apps.reviews.services.review_service import ReviewService
        assert ReviewService.can_review(customer_user, completed_appointment) is True

    def test_can_review_not_done(self, customer_user, test_appointment):
        from apps.reviews.services.review_service import ReviewService
        assert ReviewService.can_review(customer_user, test_appointment) is False

    def test_create_review(self, customer_user, completed_appointment):
        from apps.reviews.services.review_service import ReviewService
        review = ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            rating=5,
            comment='عالی بود',
            tags=['clean', 'punctual'],
        )
        assert review is not None
        assert review.rating == 5
        assert review.tags == ['clean', 'punctual']

    def test_create_reply(self, business_owner_user, approved_business, customer_user, completed_appointment):
        from apps.reviews.services.review_service import ReviewService
        review = ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            rating=4,
        )
        reply = ReviewService.create_business_reply(
            business=approved_business,
            review_id=review.id,
            reply_text='ممنون از نظر شما. خوشحالیم که راضی بودید.',
        )
        assert reply is not None


@pytest.mark.django_db
class TestReviewAPI:
    def test_create_review_api(
        self, authenticated_customer_client, completed_appointment
    ):
        url = reverse('reviews:create-review')
        response = authenticated_customer_client.post(url, {
            'appointment_id': completed_appointment.id,
            'rating': 5,
            'comment': 'فوق‌العاده بود',
            'tags': ['clean'],
        }, format='json')
        assert response.status_code == 201

    def test_business_reviews_api(
        self, authenticated_customer_client, completed_appointment, approved_business
    ):
        url = reverse('reviews:business-reviews', kwargs={'business_id': approved_business.id})
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200