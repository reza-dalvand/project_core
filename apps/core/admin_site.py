"""
AdminSite سفارشی برای ورود به پنل ادمین با پیامک
بدون فرم نام کاربری / رمز عبور
"""
import logging

from django.contrib import admin
from django.contrib.auth import get_user_model, login as auth_login, logout
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models import OtpCode
from apps.accounts.services.otp_service import OTPService
from apps.core.exceptions import OTPException
from apps.core.utils import mask_phone, to_english_digits
from apps.core.validators import validate_iranian_phone

logger = logging.getLogger(__name__)


class OTPAdminSite(admin.AdminSite):
    """
    پنل ادمین با ورود پیامکی

    جریان:
    1. کاربر شماره موبایل را وارد می‌کند
    2. کد ۵ رقمی برای شماره ارسال می‌شود
    3. کد وارد می‌شود
    4. اگر کاربر is_staff و is_active بود، لاگین می‌شود
    """

    login_template = 'admin/login.html'
    otp_purpose = OtpCode.Purpose.ADMIN_LOGIN
    max_otp_attempts = 5

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def login(self, request, extra_context=None):
        # اگر قبلاً لاگین شده باشد
        if request.user.is_authenticated:
            if request.user.is_staff:
                return HttpResponseRedirect(self._safe_redirect(request))
            # اگر کاربر عادی است، از جلسه خارج شود
            logout(request)

        context = {
            'site_header': self.site_header,
            'site_title': self.site_title,
            'index_title': self.index_title,
            'step': 'phone',
            'phone': '',
            'masked_phone': '',
            'error': '',
            'message': '',
            'next': request.POST.get('next') or request.GET.get('next', ''),
        }

        if extra_context:
            context.update(extra_context)

        if request.method == 'POST':
            action = request.POST.get('action')

            if action == 'send':
                return self._send_otp(request, context)

            if action == 'verify':
                return self._verify_otp(request, context)

        return render(request, self.login_template, context)

    def _send_otp(self, request, context):
        """
        مرحله اول: دریافت شماره موبایل و ارسال کد
        """
        raw_phone = (
            request.POST.get('phone')
            or request.session.get('admin_otp_phone', '')
        ).strip()

        try:
            phone = validate_iranian_phone(raw_phone)
        except ValidationError as e:
            message = e.messages[0] if hasattr(e, 'messages') and e.messages else 'شماره موبایل معتبر نیست'
            context['error'] = message
            return render(request, self.login_template, context)

        UserModel = get_user_model()

        # فقط کاربری که staff و فعال باشد می‌تواند وارد پنل ادمین شود
        user = UserModel.objects.filter(
            phone=phone,
            is_active=True,
            is_staff=True,
        ).first()

        # برای جلوگیری از شمارش شماره‌های مجاز،
        # فقط در صورت وجود کاربر staff پیامک را واقعاً ارسال می‌کنیم.
        # ولی پیام نمایشی کلی است.
        if user:
            try:
                OTPService.send_otp(
                    phone=phone,
                    purpose=self.otp_purpose,
                    user=user,
                )
            except OTPException as e:
                context['error'] = e.message
                return render(request, self.login_template, context)

        request.session['admin_otp_phone'] = phone
        request.session['admin_otp_attempts'] = 0

        context.update({
            'step': 'otp',
            'phone': phone,
            'masked_phone': mask_phone(phone),
            'message': 'در صورتی که این شماره مجاز باشد، کد ورود ارسال شد.',
        })

        return render(request, self.login_template, context)

    def _verify_otp(self, request, context):
        """
        مرحله دوم: بررسی کد پیامکی و ورود کاربر
        """
        phone = request.session.get('admin_otp_phone')

        if not phone:
            return HttpResponseRedirect(reverse('admin:login'))

        attempts = request.session.get('admin_otp_attempts', 0)

        # محدودیت تعداد تلاش
        if attempts >= self.max_otp_attempts:
            request.session.pop('admin_otp_phone', None)
            request.session.pop('admin_otp_attempts', None)
            context['error'] = 'تعداد تلاش‌ها بیش از حد مجاز است. دوباره درخواست کد دهید.'
            return render(request, self.login_template, context)

        code = to_english_digits(request.POST.get('code', '')).strip()

        if not code.isdigit() or len(code) != 5:
            request.session['admin_otp_attempts'] = attempts + 1
            context.update({
                'step': 'otp',
                'masked_phone': mask_phone(phone),
                'error': 'کد تایید باید ۵ رقم باشد.',
            })
            return render(request, self.login_template, context)

        try:
            OTPService.verify_otp(
                phone=phone,
                code=code,
                purpose=self.otp_purpose,
            )
        except OTPException as e:
            request.session['admin_otp_attempts'] = attempts + 1
            logger.warning(
                'Admin OTP login failed for %s',
                mask_phone(phone),
            )
            context.update({
                'step': 'otp',
                'masked_phone': mask_phone(phone),
                'error': e.message,
            })
            return render(request, self.login_template, context)

        UserModel = get_user_model()

        user = UserModel.objects.filter(
            phone=phone,
            is_active=True,
            is_staff=True,
        ).first()

        if not user:
            request.session.pop('admin_otp_phone', None)
            request.session.pop('admin_otp_attempts', None)
            context['error'] = 'این شماره دسترسی به پنل مدیریت ندارد.'
            return render(request, self.login_template, context)

        # ورود بدون رمز عبور
        auth_login(
            request,
            user,
            backend='django.contrib.auth.backends.ModelBackend',
        )

        request.session.pop('admin_otp_phone', None)
        request.session.pop('admin_otp_attempts', None)

        logger.info('Admin OTP login success for user_id=%s', user.id)

        return HttpResponseRedirect(self._safe_redirect(request))

    def _safe_redirect(self, request):
        next_url = request.POST.get('next') or request.GET.get('next') or ''

        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
        ):
            return next_url

        return reverse('admin:index')