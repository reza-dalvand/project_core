"""
Management Command: ایجاد قالب‌های پیش‌فرض پیامک
"""
from django.core.management.base import BaseCommand
from apps.notifications.models import SMSTemplate


class Command(BaseCommand):
    help = 'ایجاد قالب‌های پیش‌فرض پیامک برای کاوه‌نگار'

    TEMPLATES = [
        {
            'type': SMSTemplate.Type.OTP_LOGIN,
            'name': 'کد تایید ورود',
            'provider_template_id': 'zibano-otp',
            'pattern': 'کد تایید ورود شما به زیبانو: {{ code }}\nاین کد را با کسی به اشتراک نگذارید.',
            'variables': ['code'],
        },
        {
            'type': SMSTemplate.Type.OTP_CHANGE_PHONE,
            'name': 'کد تایید تغییر شماره',
            'provider_template_id': 'zibano-change-phone',
            'pattern': 'کد تایید تغییر شماره موبایل: {{ code }}\nاگر شما این درخواست را نداده‌اید، لطفاً با پشتیبانی تماس بگیرید.',
            'variables': ['code'],
        },
        {
            'type': SMSTemplate.Type.BOOKING_CONFIRMED,
            'name': 'تایید رزرو نوبت',
            'provider_template_id': 'zibano-booking-confirmed',
            'pattern': 'رزرو شما در {{ business_name }} تایید شد.\nخدمت: {{ service_name }}\nتاریخ: {{ date }} ساعت {{ time }}\nکد تایید: {{ code }}',
            'variables': ['business_name', 'service_name', 'date', 'time', 'code'],
        },
        {
            'type': SMSTemplate.Type.BOOKING_REMINDER,
            'name': 'یادآوری نوبت',
            'provider_template_id': 'zibano-booking-reminder',
            'pattern': 'یادآوری: فردا ساعت {{ time }} نوبت {{ service_name }} در {{ business_name }} دارید.\nلطفاً به موقع مراجعه کنید.',
            'variables': ['business_name', 'service_name', 'date', 'time'],
        },
        {
            'type': SMSTemplate.Type.BOOKING_CANCELLED,
            'name': 'لغو نوبت',
            'provider_template_id': 'zibano-booking-cancelled',
            'pattern': 'نوبت {{ service_name }} در {{ business_name }} برای تاریخ {{ date }} لغو شد.\nمبلغ بیعانه ظرف ۲۴ ساعت به حساب شما واریز می‌شود.',
            'variables': ['business_name', 'service_name', 'date'],
        },
        {
            'type': SMSTemplate.Type.PAYMENT_SUCCESS,
            'name': 'پرداخت موفق',
            'provider_template_id': 'zibano-payment-success',
            'pattern': 'پرداخت {{ amount }} تومان با موفقیت انجام شد.\nکد پیگیری: {{ tracking_code }}',
            'variables': ['amount', 'tracking_code'],
        },
        {
            'type': SMSTemplate.Type.REFUND_COMPLETED,
            'name': 'استرداد وجه',
            'provider_template_id': 'zibano-refund',
            'pattern': 'مبلغ {{ amount }} تومان به حساب شما واریز شد.\nزیبانو - رزرو آنلاین خدمات زیبایی',
            'variables': ['amount'],
        },
        {
            'type': SMSTemplate.Type.BUSINESS_APPROVED,
            'name': 'تایید کسب‌وکار',
            'provider_template_id': 'zibano-business-approved',
            'pattern': 'تبریک! کسب‌وکار "{{ business_name }}" در زیبانو تایید شد.\nاکنون می‌توانید خدمات خود را ثبت و نوبت‌دهی را شروع کنید.',
            'variables': ['business_name'],
        },
        {
            'type': SMSTemplate.Type.BUSINESS_REJECTED,
            'name': 'رد کسب‌وکار',
            'provider_template_id': 'zibano-business-rejected',
            'pattern': 'کسب‌وکار "{{ business_name }}" تایید نشد.\nدلیل: {{ reason }}\nلطفاً اطلاعات را اصلاح و مجدداً ارسال کنید.',
            'variables': ['business_name', 'reason'],
        },
        {
            'type': SMSTemplate.Type.VERIFICATION_CODE,
            'name': 'کد تایید نوبت',
            'provider_template_id': 'zibano-verify-code',
            'pattern': 'کد تایید نوبت شما: {{ code }}\nاین کد را پس از انجام خدمت به سالن‌دار ارائه دهید.',
            'variables': ['code'],
        },
    ]

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.WARNING('📱 شروع ایجاد قالب‌های پیامک...')
        )

        created_count = 0
        existing_count = 0

        for template_data in self.TEMPLATES:
            template, created = SMSTemplate.objects.get_or_create(
                type=template_data['type'],
                defaults={
                    'name': template_data['name'],
                    'provider_template_id': template_data['provider_template_id'],
                    'pattern': template_data['pattern'],
                    'variables': template_data['variables'],
                    'is_active': True,
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ قالب "{template_data["name"]}" ایجاد شد'
                    )
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ قالب "{template_data["name"]}" از قبل وجود دارد'
                    )
                )
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ ایجاد قالب‌ها: {created_count} جدید، '
                f'{existing_count} موجود'
            )
        )