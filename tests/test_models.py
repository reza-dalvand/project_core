"""
تست‌های مدل‌ها — ساختار جدید بدون role
"""
import pytest
from django.db import IntegrityError
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """تست مدل User جدید"""

    def test_create_user(self, customer_user):
        assert customer_user.phone == '09123456789'
        assert customer_user.first_name == 'کاربر'
        assert customer_user.last_name == 'تست'
        assert customer_user.is_verified is True
        assert customer_user.is_staff is False

    def test_full_name_property(self, customer_user):
        assert customer_user.full_name == 'کاربر تست'

    def test_create_superuser(self, admin_user):
        assert admin_user.is_staff is True
        assert admin_user.is_superuser is True

    def test_user_no_role(self, customer_user):
        """کاربر نباید role داشته باشد"""
        assert not hasattr(customer_user, 'role')

    def test_user_display_name(self, customer_user):
        assert customer_user.display_name == 'کاربر تست'


@pytest.mark.django_db
class TestOtpCode:
    """تست OtpCode"""

    def test_create_otp(self, db):
        from django.utils import timezone
        from datetime import timedelta
        from apps.accounts.models import OtpCode
        otp = OtpCode.objects.create(
            phone='09123456789',
            code='12345',
            purpose=OtpCode.Purpose.LOGIN,
            expires_at=timezone.now() + timedelta(minutes=5) # ✅ اضافه شد
        )
        assert otp.is_valid is True
        assert otp.is_expired is False

    def test_generate_code(self):
        from apps.accounts.models import OtpCode
        code = OtpCode.generate_code()
        assert len(code) == 5
        assert code.isdigit()

    def test_otp_purposes(self):
        from apps.accounts.models import OtpCode
        purposes = [c[0] for c in OtpCode.Purpose.choices]
        assert 'login' in purposes
        assert 'change_phone' in purposes
        assert 'booking_verify' in purposes


@pytest.mark.django_db
class TestCategories:
    """تست مدل‌های دسته‌بندی"""

    def test_service_category(self, service_category):
        assert service_category.name == 'پوست و فیشیال'
        assert service_category.slug is not None

    def test_sub_service(self, sub_service):
        assert sub_service.name == 'فیشیال VIP'
        assert sub_service.category.name == 'پوست و فیشیال'

    def test_business_category(self, business_category):
        assert business_category.name == 'سالن زیبایی'
        assert business_category.slug is not None


@pytest.mark.django_db
class TestLocations:
    """تست مدل‌های مکان"""

    def test_province(self, province):
        assert province.name == 'تهران'
        assert province.slug is not None

    def test_city(self, city):
        assert city.name == 'تهران'
        assert city.province.name == 'تهران'

    def test_city_unique_together(self, province):
        from apps.locations.models import City
        City.objects.create(name='تهران', province=province)
        with pytest.raises(IntegrityError):
            City.objects.create(name='تهران', province=province)


@pytest.mark.django_db
class TestBusiness:
    """تست مدل Business جدید"""

    def test_create_business(self, approved_business):
        assert approved_business.name == 'سالن تست'
        assert approved_business.status == 'approved'
        assert approved_business.booking_slug is not None

    def test_booking_slug_unique(self, approved_business, business_owner_user, business_category, province, city):
        from apps.businesses.models import Business
        b2 = Business.objects.create(
            owner=business_owner_user,
            name='سالن تست',
            category=business_category,
            province=province,
            city=city,
            address='آدرس ۲',
            status='approved',
        )
        assert b2.booking_slug != approved_business.booking_slug

    def test_bank_fields_in_business(self, approved_business):
        """فیلدهای بانکی مستقیم در Business"""
        approved_business.bank_sheba = 'IR123456789012345678901234'
        approved_business.bank_info_registered = True
        approved_business.save()
        assert approved_business.bank_info_registered is True

    def test_vip_fields(self, approved_business):
        assert approved_business.is_vip is False
        assert approved_business.vip_expires_at is None

    def test_rating_fields(self, approved_business):
        assert approved_business.rating == 0
        assert approved_business.reviews_count == 0


@pytest.mark.django_db
class TestService:
    """تست مدل Service جدید"""

    def test_service_properties(self, test_service):
        assert test_service.discount_amount == 50000
        assert test_service.final_price == 450000
        assert test_service.app_fee >= 10000

    def test_service_renewal_days(self, test_service):
        assert test_service.renewal_days == 30

    def test_service_category_fk(self, test_service):
        assert test_service.category.name == 'پوست و فیشیال'
        assert test_service.sub_service.name == 'فیشیال VIP'


@pytest.mark.django_db
class TestSchedule:
    """تست مدل ServiceSchedule جدید"""

    def test_create_schedule(self, test_schedule):
        # ✅ به جای مقدار ثابت، از fixture استفاده کن
        assert test_schedule.date_key is not None
        assert test_schedule.slot_count > 0
        # اگه میخوای تاریخ دقیق رو چک کنی:
        import jdatetime
        future = jdatetime.date.today() + jdatetime.timedelta(days=30)
        expected_key = f'{future.year}/{future.month:02d}/{future.day:02d}'
        assert test_schedule.date_key == expected_key

    def test_schedule_with_breaks(self, test_schedule):
        assert len(test_schedule.breaks) == 1
        assert test_schedule.breaks[0]['start'] == '13:00'

    def test_schedule_unique(self, approved_business, test_service, test_schedule):
        """تست unique_together روی service + date_key"""
        from apps.schedules.models import ServiceSchedule
        from datetime import time
        from django.db import IntegrityError
        import pytest
        
        # ✅ از همون تاریخ fixture استفاده کن
        with pytest.raises(IntegrityError):
            ServiceSchedule.objects.create(
                business=approved_business,
                service=test_service,
                jy=test_schedule.jy,
                jm=test_schedule.jm,
                jd=test_schedule.jd,
                work_start=time(9, 0),
                work_end=time(18, 0),
                slot_duration=30,
            )

@pytest.mark.django_db
class TestAppointment:
    """تست مدل Appointment جدید"""

    def test_create_appointment(self, test_appointment):
        # ✅ از fixture استفاده کن
        assert test_appointment.date_key is not None
        assert test_appointment.status == 'reserved'
        assert test_appointment.verification_code is not None
        assert len(test_appointment.verification_code) == 4
        assert test_appointment.remaining_amount == 350000

    def test_jalali_date_fields(self, test_appointment):
        # ✅ چک کن فیلدها پر شدن
        assert test_appointment.jy > 1400
        assert 1 <= test_appointment.jm <= 12
        assert 1 <= test_appointment.jd <= 31

    def test_cancel_by_customer(self, test_appointment):
        test_appointment.cancel_by_customer('تغییر برنامه')
        assert test_appointment.status == 'cancelled_by_customer'
        assert test_appointment.cancellation_reason == 'تغییر برنامه'
        assert test_appointment.cancelled_at is not None


@pytest.mark.django_db
class TestTransaction:
    """تست مدل Transaction جدید"""

    def test_create_transaction(self, customer_user, approved_business):
        from apps.payments.models import Transaction
        tx = Transaction.objects.create(
            business=approved_business,
            customer=customer_user,
            type='deposit',
            amount=100000,
            app_fee=10000,
        )
        assert tx.tracking_code is not None
        assert tx.ref_number is not None
        assert tx.status == 'blocked'

    def test_transaction_statuses(self):
        from apps.payments.models import Transaction
        statuses = [c[0] for c in Transaction.Status.choices]
        assert 'blocked' in statuses
        assert 'settling' in statuses
        assert 'settled' in statuses
        assert 'refunded' in statuses
        assert 'failed' in statuses


@pytest.mark.django_db
class TestReview:
    """تست مدل Review جدید"""

    def test_create_review(self, customer_user, approved_business, test_service):
        from apps.appointments.models import Appointment
        from apps.reviews.models import Review
        from datetime import time

        appointment = Appointment.objects.create(
            business=approved_business,
            service=test_service,
            customer=customer_user,
            jy=1405,
            jm=4,
            jd=22,
            time_slot=time(10, 0),
            total_price=450000,
        )

        review = Review.objects.create(
            business=approved_business,
            service=test_service,
            appointment=appointment,
            customer=customer_user,
            rating=5,
            comment='عالی بود',
            tags=['clean', 'punctual'],
        )

        assert review.rating == 5
        assert review.tags == ['clean', 'punctual']

        approved_business.refresh_from_db()
        assert approved_business.rating == 5.0
        assert approved_business.reviews_count == 1

    def test_review_reply(self, customer_user, approved_business, test_service):
        from apps.appointments.models import Appointment
        from apps.reviews.models import Review
        from datetime import time

        appointment = Appointment.objects.create(
            business=approved_business,
            service=test_service,
            customer=customer_user,
            jy=1405,
            jm=4,
            jd=22,
            time_slot=time(10, 0),
            total_price=450000,
        )

        review = Review.objects.create(
            business=approved_business,
            appointment=appointment,
            customer=customer_user,
            rating=4,
        )

        review.reply = 'ممنون از نظر شما'
        review.save()
        assert review.reply == 'ممنون از نظر شما'


@pytest.mark.django_db
class TestExplore:
    """تست مدل‌های ویترین"""

    def test_create_explore_post(self, approved_business):
        from apps.explore.models import ExplorePost
        post = ExplorePost.objects.create(
            business=approved_business,
            source='business',
            caption='نمونه کار جدید',
        )
        assert post.is_pinned is False


@pytest.mark.django_db
class TestReminder:
    """تست مدل یادآوری"""

    def test_create_reminder(self, customer_user, approved_business, test_service):
        from apps.appointments.models import Appointment
        from apps.reminders.models import RenewalReminder
        from datetime import time

        appointment = Appointment.objects.create(
            business=approved_business,
            service=test_service,
            customer=customer_user,
            jy=1405,
            jm=4,
            jd=22,
            time_slot=time(10, 0),
            total_price=450000,
        )

        reminder = RenewalReminder.objects.create(
            business=approved_business,
            customer=customer_user,
            appointment=appointment,
            service=test_service,
            last_service_date='1405/04/22',
            due_date='1405/05/22',
            days_remaining=30,
        )
        assert reminder.days_remaining == 30
        assert reminder.reminder_sent is False


@pytest.mark.django_db
class TestFavorites:
    """تست مدل‌های علاقه‌مندی"""

    def test_favorite_business(self, customer_user, approved_business):
        from apps.favorites.models import FavoriteBusiness
        fav = FavoriteBusiness.objects.create(
            user=customer_user,
            business=approved_business,
        )
        assert fav.user == customer_user

    def test_favorite_unique(self, customer_user, approved_business):
        from apps.favorites.models import FavoriteBusiness
        FavoriteBusiness.objects.create(
            user=customer_user,
            business=approved_business,
        )
        with pytest.raises(IntegrityError):
            FavoriteBusiness.objects.create(
                user=customer_user,
                business=approved_business,
            )