"""
تست‌های پنل مدیریت داشبورد — فاز ۶
پوشش: احراز هویت، دکوراتورها، میدلور، ویوها، محدودیت نقش‌ها، Rate Limiting
"""
import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone


# ═══════════════════════════════════════════════
#   احراز هویت داشبورد
# ═══════════════════════════════════════════════
@pytest.mark.django_db
class TestDashboardLogin:
    """تست‌های صفحه ورود داشبورد"""

    def test_login_page_loads(self, client):
        """صفحه ورود باید با کد ۲۰۰ لود شود"""
        url = reverse('dashboard:login')
        response = client.get(url)
        assert response.status_code == 200

    def test_login_page_contains_form(self, client):
        """صفحه ورود باید فرم شماره تلفن داشته باشد"""
        url = reverse('dashboard:login')
        response = client.get(url)
        content = response.content.decode()
        assert 'name="phone"' in content
        assert 'csrfmiddlewaretoken' in content

    def test_login_with_invalid_phone_format(self, client):
        """شماره تلفن نامعتبر باید خطا بدهد"""
        url = reverse('dashboard:login')
        response = client.post(url, {'phone': '12345'})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'معتبر' in content

    def test_login_with_non_admin_phone(self, client, customer_user):
        """کاربر عادی نباید بتواند وارد داشبورد شود"""
        url = reverse('dashboard:login')
        response = client.post(url, {'phone': customer_user.phone})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'دسترسی به پنل مدیریت ندارد' in content

    def test_login_with_admin_phone_sends_otp(
        self, client, mock_otp,
        dashboard_admin_user, dashboard_admin_profile,
    ):
        """ورود با شماره ادمین باید کد تایید بفرستد"""
        url = reverse('dashboard:login')
        response = client.post(url, {'phone': dashboard_admin_user.phone})
        # باید به صفحه تایید کد هدایت شود
        assert response.status_code == 302
        assert response.url == reverse('dashboard:verify_otp')

    def test_login_redirect_if_already_logged_in(self, dashboard_client):
        """اگر قبلاً لاگین شده، باید به خانه هدایت شود"""
        url = reverse('dashboard:login')
        response = dashboard_client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('dashboard:home')


@pytest.mark.django_db
class TestDashboardOTPVerification:
    """تست‌های تایید کد داشبورد"""

    def test_verify_otp_redirect_without_session(self, client):
        """بدون سشن باید به ورود هدایت شود"""
        url = reverse('dashboard:verify_otp')
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('dashboard:login')

    def test_verify_otp_redirect_without_phone(self, client):
        """سشن بدون شماره تلفن باید به ورود هدایت شود"""
        session = client.session
        session['dashboard_otp_role'] = 'super_admin'
        session.save()
        url = reverse('dashboard:verify_otp')
        response = client.get(url)
        assert response.status_code == 302

    def test_verify_otp_invalid_code_length(self, client, dashboard_admin_user):
        """کد با طول نامعتبر باید خطا بدهد"""
        session = client.session
        session['dashboard_otp_phone'] = dashboard_admin_user.phone
        session['dashboard_otp_role'] = 'super_admin'
        session['dashboard_otp_attempts'] = 0
        session.save()

        url = reverse('dashboard:verify_otp')
        response = client.post(url, {'code': '123'})
        assert response.status_code == 200
        content = response.content.decode()
        assert '۵ رقم' in content

    def test_verify_otp_max_attempts(self, client, dashboard_admin_user):
        """بعد از ۵ تلاش ناموفق باید به ورود هدایت شود"""
        session = client.session
        session['dashboard_otp_phone'] = dashboard_admin_user.phone
        session['dashboard_otp_role'] = 'super_admin'
        session['dashboard_otp_attempts'] = 5
        session.save()

        url = reverse('dashboard:verify_otp')
        response = client.post(url, {'code': '12345'})
        assert response.status_code == 302
        assert response.url == reverse('dashboard:login')

    def test_verify_otp_missing_role_redirects_to_login(
        self, client, mock_otp,
        dashboard_admin_user, dashboard_admin_profile,
    ):
        """
        فاز ۲: اگر نقش در سشن نباشد، باید به ورود هدایت شود
        (نه اینکه با نقش پیش‌فرض وارد شود)
        """
        session = client.session
        session['dashboard_otp_phone'] = dashboard_admin_user.phone
        # نقش عمداً تنظیم نشده
        session['dashboard_otp_attempts'] = 0
        session.save()

        url = reverse('dashboard:verify_otp')
        response = client.post(url, {'code': '12345'})
        # باید به لاگین هدایت شود
        assert response.status_code == 302
        assert response.url == reverse('dashboard:login')


@pytest.mark.django_db
class TestDashboardLogout:
    """تست خروج از داشبورد"""

    def test_logout_clears_session(self, dashboard_client):
        """خروج باید سشن را پاک کند"""
        url = reverse('dashboard:logout')
        response = dashboard_client.get(url)
        assert response.status_code == 302
        # بررسی پاک شدن سشن
        assert 'dashboard_admin_logged_in' not in dashboard_client.session

    def test_logout_redirects_to_login(self, dashboard_client):
        """خروج باید به صفحه ورود هدایت شود"""
        url = reverse('dashboard:logout')
        response = dashboard_client.get(url)
        assert response.url == reverse('dashboard:login')


# ═══════════════════════════════════════════════
#   میدلور سشن داشبورد
# ═══════════════════════════════════════════════
@pytest.mark.django_db
class TestDashboardMiddleware:
    """تست‌های میدلور انقضای سشن"""

    def test_valid_session_passes(self, dashboard_client):
        """سشن معتبر باید عبور کند"""
        url = reverse('dashboard:home')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_expired_session_redirects(self, client, dashboard_admin_user):
        """سشن منقضی شده باید به ورود هدایت شود"""
        session = client.session
        session['dashboard_admin_logged_in'] = True
        session['dashboard_admin_phone'] = dashboard_admin_user.phone
        session['dashboard_role'] = 'super_admin'
        session['dashboard_login_time'] = (
            timezone.now() - timedelta(minutes=61)
        ).isoformat()
        session.save()

        url = reverse('dashboard:home')
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('dashboard:login')

    def test_session_extends_on_activity(self, dashboard_client):
        """سشن باید با هر درخواست تمدید شود"""
        url = reverse('dashboard:home')
        response = dashboard_client.get(url)
        assert response.status_code == 200
        # زمان ورود باید بروزرسانی شده باشد
        assert 'dashboard_login_time' in dashboard_client.session

    def test_inactive_user_session_invalidated(
        self, client, dashboard_admin_user, dashboard_admin_profile,
    ):
        """کاربر غیرفعال باید از داشبورد خارج شود"""
        # غیرفعال کردن کاربر
        dashboard_admin_user.is_active = False
        dashboard_admin_user.save(update_fields=['is_active'])

        session = client.session
        session['dashboard_admin_logged_in'] = True
        session['dashboard_admin_phone'] = dashboard_admin_user.phone
        session['dashboard_role'] = 'super_admin'
        session['dashboard_login_time'] = timezone.now().isoformat()
        session.save()

        url = reverse('dashboard:home')
        response = client.get(url)
        # باید به لاگین هدایت شود
        assert response.status_code == 302


# ═══════════════════════════════════════════════
#   ویوهای اصلی داشبورد
# ═══════════════════════════════════════════════
@pytest.mark.django_db
class TestDashboardHome:
    """تست صفحه اصلی داشبورد"""

    def test_home_requires_login(self, client):
        """بدون ورود باید به لاگین هدایت شود"""
        url = reverse('dashboard:home')
        response = client.get(url)
        assert response.status_code == 302

    def test_home_loads_for_admin(self, dashboard_client):
        """صفحه اصلی باید برای ادمین لود شود"""
        url = reverse('dashboard:home')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_home_contains_stats(self, dashboard_client):
        """صفحه اصلی باید آمار داشته باشد"""
        url = reverse('dashboard:home')
        response = dashboard_client.get(url)
        content = response.content.decode()
        assert 'کاربران' in content


@pytest.mark.django_db
class TestDashboardUsers:
    """تست مدیریت کاربران"""

    def test_users_list_loads(self, dashboard_client):
        url = reverse('dashboard:users_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_users_list_with_search(self, dashboard_client):
        url = reverse('dashboard:users_list')
        response = dashboard_client.get(url, {'search': '0912'})
        assert response.status_code == 200

    def test_users_list_with_filter(self, dashboard_client):
        url = reverse('dashboard:users_list')
        response = dashboard_client.get(url, {'status': 'active'})
        assert response.status_code == 200

    def test_user_detail_loads(self, dashboard_client, customer_user):
        url = reverse('dashboard:user_detail', kwargs={'user_id': customer_user.id})
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_user_toggle_active(self, dashboard_client, customer_user):
        url = reverse('dashboard:user_toggle_active', kwargs={'user_id': customer_user.id})
        response = dashboard_client.post(url)
        assert response.status_code == 302
        customer_user.refresh_from_db()
        assert customer_user.is_active is False

    def test_cannot_deactivate_self(self, dashboard_client, dashboard_admin_user):
        """ادمین نمی‌تواند خودش را غیرفعال کند"""
        url = reverse(
            'dashboard:user_toggle_active',
            kwargs={'user_id': dashboard_admin_user.id},
        )
        response = dashboard_client.post(url)
        assert response.status_code == 302
        dashboard_admin_user.refresh_from_db()
        assert dashboard_admin_user.is_active is True

    def test_cannot_deactivate_superuser(self, dashboard_client, admin_user):
        """ادمین نمی‌تواند سوپریوزر را غیرفعال کند"""
        url = reverse('dashboard:user_toggle_active', kwargs={'user_id': admin_user.id})
        response = dashboard_client.post(url)
        assert response.status_code == 302
        admin_user.refresh_from_db()
        assert admin_user.is_active is True


@pytest.mark.django_db
class TestDashboardBusinesses:
    """تست مدیریت کسب‌وکارها"""

    def test_businesses_list_loads(self, dashboard_client):
        url = reverse('dashboard:businesses_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_businesses_list_with_search(self, dashboard_client):
        url = reverse('dashboard:businesses_list')
        response = dashboard_client.get(url, {'search': 'سالن'})
        assert response.status_code == 200

    def test_business_detail_loads(self, dashboard_client, approved_business):
        url = reverse(
            'dashboard:business_detail',
            kwargs={'business_id': approved_business.id},
        )
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_business_approve(self, dashboard_client, approved_business):
        """تایید کسب‌وکار"""
        approved_business.status = 'pending'
        approved_business.save(update_fields=['status'])

        url = reverse(
            'dashboard:business_approve',
            kwargs={'business_id': approved_business.id},
        )
        response = dashboard_client.post(url)
        assert response.status_code == 302
        approved_business.refresh_from_db()
        assert approved_business.status == 'approved'

    def test_business_reject_requires_reason(self, dashboard_client, approved_business):
        """رد کسب‌وکار بدون دلیل باید خطا بدهد"""
        url = reverse(
            'dashboard:business_reject',
            kwargs={'business_id': approved_business.id},
        )
        response = dashboard_client.post(url, {'rejection_reason': ''})
        assert response.status_code == 302

    def test_business_toggle_vip(self, dashboard_client, approved_business):
        url = reverse(
            'dashboard:business_toggle_vip',
            kwargs={'business_id': approved_business.id},
        )
        response = dashboard_client.post(url)
        assert response.status_code == 302
        approved_business.refresh_from_db()
        assert approved_business.is_vip is True


@pytest.mark.django_db
class TestDashboardFinancial:
    """تست مدیریت مالی"""

    def test_financial_index_loads(self, dashboard_client):
        url = reverse('dashboard:financial')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_transactions_list_loads(self, dashboard_client):
        url = reverse('dashboard:transactions_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_settlements_list_loads(self, dashboard_client):
        url = reverse('dashboard:settlements_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestDashboardContent:
    """تست مدیریت محتوا"""

    def test_content_index_loads(self, dashboard_client):
        url = reverse('dashboard:content')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_explore_list_loads(self, dashboard_client):
        url = reverse('dashboard:explore_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_portfolios_list_loads(self, dashboard_client):
        url = reverse('dashboard:portfolios_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestDashboardSupport:
    """تست پشتیبانی"""

    def test_support_index_loads(self, dashboard_client):
        url = reverse('dashboard:support')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_tickets_list_loads(self, dashboard_client):
        url = reverse('dashboard:tickets_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_messages_list_loads(self, dashboard_client):
        url = reverse('dashboard:messages_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_sms_logs_loads(self, dashboard_client):
        url = reverse('dashboard:sms_logs')
        response = dashboard_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestDashboardSettings:
    """تست تنظیمات"""

    def test_settings_index_super_admin(self, dashboard_client):
        """سوپر ادمین باید به تنظیمات دسترسی داشته باشد"""
        url = reverse('dashboard:settings')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_settings_restricted_for_app_admin(self, dashboard_app_admin_client):
        """ادمین اپلیکیشن نباید به تنظیمات دسترسی داشته باشد"""
        url = reverse('dashboard:settings')
        response = dashboard_app_admin_client.get(url)
        # باید به خانه هدایت شود
        assert response.status_code == 302

    def test_roles_list_super_admin(self, dashboard_client):
        url = reverse('dashboard:roles_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_admins_list_super_admin(self, dashboard_client):
        url = reverse('dashboard:admins_list')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_system_settings_super_admin(self, dashboard_client):
        url = reverse('dashboard:system_settings')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_admin_cannot_deactivate_self(
        self, dashboard_client, dashboard_admin_user, dashboard_admin_profile,
    ):
        """ادمین نمی‌تواند خودش را غیرفعال کند"""
        url = reverse(
            'dashboard:admin_toggle_active',
            kwargs={'admin_id': dashboard_admin_profile.id},
        )
        response = dashboard_client.post(url)
        assert response.status_code == 302
        dashboard_admin_profile.refresh_from_db()
        assert dashboard_admin_profile.is_active is True


# ═══════════════════════════════════════════════
#   محدودیت نقش‌ها
# ═══════════════════════════════════════════════
@pytest.mark.django_db
class TestRoleRestrictions:
    """تست محدودیت دسترسی بر اساس نقش"""

    def test_app_admin_can_view_users(self, dashboard_app_admin_client):
        """ادمین اپلیکیشن می‌تواند کاربران را ببیند"""
        url = reverse('dashboard:users_list')
        response = dashboard_app_admin_client.get(url)
        assert response.status_code == 200

    def test_app_admin_can_view_businesses(self, dashboard_app_admin_client):
        """ادمین اپلیکیشن می‌تواند کسب‌وکارها را ببیند"""
        url = reverse('dashboard:businesses_list')
        response = dashboard_app_admin_client.get(url)
        assert response.status_code == 200

    def test_unauthenticated_redirect(self, client):
        """کاربر بدون ورود باید هدایت شود"""
        urls = [
            reverse('dashboard:home'),
            reverse('dashboard:users_list'),
            reverse('dashboard:businesses_list'),
            reverse('dashboard:financial'),
            reverse('dashboard:content'),
            reverse('dashboard:support'),
            reverse('dashboard:settings'),
        ]
        for url in urls:
            response = client.get(url)
            assert response.status_code == 302, f"Failed for {url}"


# ═══════════════════════════════════════════════
#   Rate Limiting
# ═══════════════════════════════════════════════
@pytest.mark.django_db
class TestDashboardRateLimiting:
    """تست محدودیت نرخ ورود"""

    def test_rate_limit_blocks_after_max_attempts(self, client):
        """بعد از ۵ تلاش ناموفق، ورود بلاک شود"""
        from django.core.cache import cache
        cache.clear()

        url = reverse('dashboard:login')
        non_admin_phone = '09129999999'

        # ۵ تلاش با شماره غیر مجاز (هر بار شمارنده افزایش می‌یابد)
        for i in range(5):
            response = client.post(url, {'phone': non_admin_phone})
            assert response.status_code == 200

        # تلاش ششم باید بلاک شود
        response = client.post(url, {'phone': non_admin_phone})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'تعداد تلاش‌های شما بیش از حد مجاز است' in content

    def test_rate_limit_resets_after_timeout(self, client):
        """بعد از انقضای تایمر، ورود دوباره مجاز شود"""
        from django.core.cache import cache
        cache.clear()

        non_admin_phone = '09128888888'

        # پر کردن کش با مقدار منقضی شده
        cache.set(f'dashboard_login_lock:{non_admin_phone}', 5, timeout=1)
        import time
        time.sleep(2)

        url = reverse('dashboard:login')
        response = client.post(url, {'phone': non_admin_phone})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'تعداد تلاش‌های شما بیش از حد مجاز است' not in content


# ═══════════════════════════════════════════════
#   دکوراتورها
# ═══════════════════════════════════════════════
@pytest.mark.django_db
class TestDashboardDecorators:
    """تست دکوراتورهای احراز هویت"""

    def test_admin_login_required_redirects_anonymous(self, client):
        """بدون سشن باید به ورود هدایت شود"""
        url = reverse('dashboard:home')
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('dashboard:login')

    def test_admin_login_required_passes_authenticated(self, dashboard_client):
        """با سشن معتبر باید عبور کند"""
        url = reverse('dashboard:home')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_role_required_super_admin_only(self, dashboard_app_admin_client):
        """نقش غیر مجاز باید هدایت شود"""
        url = reverse('dashboard:settings')
        response = dashboard_app_admin_client.get(url)
        assert response.status_code == 302

    def test_role_required_passes_super_admin(self, dashboard_client):
        """سوپر ادمین باید عبور کند"""
        url = reverse('dashboard:settings')
        response = dashboard_client.get(url)
        assert response.status_code == 200

    def test_invalidated_admin_profile_redirects(self, client, dashboard_admin_user, dashboard_admin_profile):
        """پروفایل ادمین غیرفعال باید خروج اجباری دهد"""
        dashboard_admin_profile.is_active = False
        dashboard_admin_profile.save(update_fields=['is_active'])

        session = client.session
        session['dashboard_admin_logged_in'] = True
        session['dashboard_admin_phone'] = dashboard_admin_user.phone
        session['dashboard_role'] = 'super_admin'
        session['dashboard_login_time'] = timezone.now().isoformat()
        session.save()

        url = reverse('dashboard:home')
        response = client.get(url)
        assert response.status_code == 302