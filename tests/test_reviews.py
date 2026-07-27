"""
تست‌های سیستم نظرات و امتیازات
"""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.reviews.models import Review, ReviewTag, ReviewResponse
from apps.bookings.models import Appointment
from apps.businesses.models import Business
from apps.reviews.services.review_service import ReviewService


@pytest.fixture
def review_tags(db):
    """ایجاد تگ‌های تست"""
    tags = []
    for i in range(3):
        tag = ReviewTag.objects.create(
            label=f'تگ تست {i + 1}',
            icon='check_circle',
            order=i + 1,
            is_active=True,
        )
        tags.append(tag)
    return tags


@pytest.fixture
def completed_appointment(business_owner_user, customer_user):
    """ایجاد نوبت انجام‌شده"""
    from apps.businesses.models import Category, Province, City, Service

    province = Province.objects.create(name='تهران', slug='tehran')
    city = City.objects.create(name='تهران', slug='tehran-city', province=province)
    category = Category.objects.create(name='سالن زیبایی', slug='salon')

    business = Business.objects.create(
        owner=business_owner_user,
        name='سالن تست',
        category=category,
        province=province,
        city=city,
        address='آدرس تست',
        status='approved',
    )

    service = Service.objects.create(
        business=business,
        name='خدمت تست',
        original_price=500000,
        duration_minutes=60,
    )

    appointment = Appointment.objects.create(
        customer=customer_user,
        business=business,
        service=service,
        date='2026-08-01',
        time='10:00:00',
        status=Appointment.Status.DONE,
        original_price=500000,
        final_price=500000,
    )

    return appointment


@pytest.mark.django_db
class TestReviewService:
    """تست‌های ReviewService"""

    def test_can_review_success(self, customer_user, completed_appointment):
        """تست بررسی امکان ثبت نظر - موفق"""
        can_review = ReviewService.can_review(
            customer_user,
            completed_appointment,
        )
        assert can_review is True

    def test_can_review_not_done(self, customer_user, business_owner_user):
        """تست بررسی امکان ثبت نظر - نوبت انجام نشده"""
        from apps.bookings.models import Appointment
        from apps.businesses.models import Business, Service, Category, Province, City

        province = Province.objects.create(name='تهران', slug='tehran')
        city = City.objects.create(name='تهران', slug='tehran-city', province=province)
        category = Category.objects.create(name='سالن', slug='salon')

        business = Business.objects.create(
            owner=business_owner_user,
            name='سالن تست',
            category=category,
            province=province,
            city=city,
            address='آدرس',
            status='approved',
        )

        service = Service.objects.create(
            business=business,
            name='خدمت',
            original_price=500000,
            duration_minutes=60,
        )

        appointment = Appointment.objects.create(
            customer=customer_user,
            business=business,
            service=service,
            date='2026-08-01',
            time='10:00:00',
            status=Appointment.Status.CONFIRMED,  # نه done
            original_price=500000,
            final_price=500000,
        )

        can_review = ReviewService.can_review(customer_user, appointment)
        assert can_review is False

    def test_create_review_success(self, customer_user, completed_appointment, review_tags):
        """تست ایجاد نظر - موفق"""
        review = ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            rating=5,
            comment='خدمت عالی بود',
            tag_ids=[review_tags[0].id, review_tags[1].id],
        )

        assert review is not None
        assert review.customer == customer_user
        assert review.business == completed_appointment.business
        assert review.rating == 5
        assert review.comment == 'خدمت عالی بود'
        assert review.tags.count() == 2

        # بررسی بروزرسانی آمار کسب‌وکار
        completed_appointment.business.refresh_from_db()
        assert completed_appointment.business.rating_avg == 5.0
        assert completed_appointment.business.rating_count == 1

    def test_create_review_duplicate(self, customer_user, completed_appointment):
        """تست ایجاد نظر تکراری"""
        # ایجاد اولین نظر
        ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            rating=5,
            comment='عالی',
        )

        # تلاش برای ایجاد نظر دوم
        from apps.reviews.services.review_service import ReviewAlreadyExistsException

        with pytest.raises(ReviewAlreadyExistsException):
            ReviewService.create_review(
                customer=customer_user,
                appointment_id=completed_appointment.id,
                rating=4,
                comment='خوب',
            )

    def test_create_business_response_success(
            self,
            business_owner_user,
            completed_appointment,
            customer_user,
    ):
        """تست ایجاد پاسخ کسب‌وکار - موفق"""
        # ایجاد نظر
        review = ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            rating=4,
            comment='خوب بود',
        )

        # ایجاد پاسخ
        response = ReviewService.create_business_response(
            business=business_owner_user.business,
            review_id=review.id,
            text='ممنون از نظر شما. خوشحالیم که راضی بودید.',
        )

        assert response is not None
        assert response.review == review
        assert response.business == business_owner_user.business
        assert 'ممنون' in response.text


@pytest.mark.django_db
class TestReviewAPI:
    """تست‌های API نظرات"""

    def test_list_review_tags(self, authenticated_customer_client, review_tags):
        """تست لیست تگ‌ها"""
        url = reverse('api:reviews:review-tags')
        response = authenticated_customer_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True
        assert len(response.json()['data']) == 3

    def test_create_review_api(
            self,
            authenticated_customer_client,
            completed_appointment,
            review_tags,
    ):
        """تست ایجاد نظر از طریق API"""
        url = reverse('api:reviews:create-review')
        data = {
            'appointment_id': completed_appointment.id,
            'rating': 5,
            'comment': 'خدمت فوق‌العاده بود',
            'tag_ids': [review_tags[0].id, review_tags[1].id],
        }

        response = authenticated_customer_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['success'] is True
        assert response.json()['data']['rating'] == 5

        # بررسی ایجاد در دیتابیس
        assert Review.objects.count() == 1

    def test_business_reviews_api(
            self,
            authenticated_customer_client,
            completed_appointment,
            customer_user,
    ):
        """تست لیست نظرات کسب‌وکار"""
        # ایجاد چند نظر
        for i in range(3):
            ReviewService.create_review(
                customer=customer_user,
                appointment_id=completed_appointment.id,
                rating=5 - i,
                comment=f'نظر {i + 1}',
            )
            # برای تست‌های بعدی، نوبت‌های جدید ایجاد کنیم
            if i < 2:
                from apps.bookings.models import Appointment
                new_appointment = Appointment.objects.create(
                    customer=customer_user,
                    business=completed_appointment.business,
                    service=completed_appointment.service,
                    date='2026-08-02',
                    time='10:00:00',
                    status=Appointment.Status.DONE,
                    original_price=500000,
                    final_price=500000,
                )
                completed_appointment = new_appointment

        url = reverse(
            'api:reviews:business-reviews',
            kwargs={'business_id': completed_appointment.business.id}
        )
        response = authenticated_customer_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True
        assert len(response.json()['data']) == 3

    def test_can_review_check_api(
            self,
            authenticated_customer_client,
            completed_appointment,
    ):
        """تست بررسی امکان ثبت نظر"""
        url = reverse(
            'api:reviews:can-review',
            kwargs={'appointment_id': completed_appointment.id}
        )
        response = authenticated_customer_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True
        assert response.json()['data']['can_review'] is True

    def test_create_response_api(
            self,
            authenticated_business_client,
            business_owner_user,
            completed_appointment,
            customer_user,
    ):
        """تست ایجاد پاسخ کسب‌وکار"""
        # ایجاد نظر
        review = ReviewService.create_review(
            customer=customer_user,
            appointment_id=completed_appointment.id,
            rating=4,
            comment='خوب بود',
        )

        url = reverse('api:reviews:create-response')
        data = {
            'review_id': review.id,
            'text': 'ممنون از نظر شما. خوشحالیم که راضی بودید و امیدواریم دوباره شما را ببینیم.',
        }

        response = authenticated_business_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['success'] is True

        # بررسی ایجاد پاسخ
        assert ReviewResponse.objects.count() == 1