# apps/core/management/commands/create_initial_data.py
"""
ایجاد داده‌های اولیه برای توسعه
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'ایجاد داده‌های اولیه برای توسعه'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('🚀 شروع ایجاد داده‌های اولیه...'))

        # ═══════════ ۱. Superuser ═══════════
        if not User.objects.filter(phone='09120000000').exists():
            User.objects.create_superuser(
                phone='09120000000',
                password='admin123456',
                first_name='مدیر',
                last_name='ارشد',
            )
            self.stdout.write(self.style.SUCCESS('✓ Superuser ایجاد شد'))

        # ═══════════ ۲. دسته‌بندی‌های خدمات ═══════════
        from apps.categories.models import ServiceCategory, SubService, BusinessCategory

        categories_data = [
            {
                'name': 'میکاپ',
                'icon_name': 'face',
                'color': '#E91E63',
                'gradient_start': '#E91E63',
                'gradient_end': '#C2185B',
                'sort_order': 1,
                'sub_services': ['میکاپ عروس', 'میکاپ ملایم', 'میکاپ شب'],
            },
            {
                'name': 'ناخن',
                'icon_name': 'brush',
                'color': '#9C27B0',
                'gradient_start': '#9C27B0',
                'gradient_end': '#7B1FA2',
                'sort_order': 2,
                'sub_services': ['کاشت ژله‌ای', 'کاشت پودری', 'مانیکور'],
            },
            {
                'name': 'لیزر',
                'icon_name': 'flash_on',
                'color': '#2196F3',
                'gradient_start': '#2196F3',
                'gradient_end': '#1976D2',
                'sort_order': 3,
                'sub_services': ['لیزر فول بادی', 'لیزر صورت', 'لیزر بیکینی'],
            },
            {
                'name': 'پوست و فیشیال',
                'icon_name': 'spa',
                'color': '#4CAF50',
                'gradient_start': '#4CAF50',
                'gradient_end': '#388E3C',
                'sort_order': 4,
                'sub_services': ['فیشیال VIP', 'فیشیال ساده', 'هیدرودرمی'],
            },
        ]

        for cat_data in categories_data:
            sub_services = cat_data.pop('sub_services')
            category, created = ServiceCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ دسته‌بندی {category.name} ایجاد شد'))

            for i, sub_name in enumerate(sub_services):
                SubService.objects.get_or_create(
                    category=category,
                    name=sub_name,
                    defaults={
                        'slug': f'{category.slug}-{i}',
                        'type_id': f'{category.slug}_{i}',
                    },
                )

        # ═══════════ ۳. انواع کسب‌وکار ═══════════
        business_types = ['سالن زیبایی', 'کلینیک پوست', 'مرکز لیزر', 'آرایشگاه مردانه']
        for name in business_types:
            BusinessCategory.objects.get_or_create(name=name)

        self.stdout.write(self.style.SUCCESS('✓ انواع کسب‌وکار ایجاد شد'))

        # ═══════════ ۴. استان‌ها و شهرها ═══════════
        from apps.locations.models import Province, City

        provinces_data = [
            {'name': 'تهران', 'cities': ['تهران', 'کرج', 'شهریار', 'اسلامشهر']},
            {'name': 'اصفهان', 'cities': ['اصفهان', 'کاشان', 'نجف‌آباد']},
            {'name': 'فارس', 'cities': ['شیراز', 'مرودشت', 'جهرم']},
            {'name': 'خراسان رضوی', 'cities': ['مشهد', 'نیشابور', 'سبزوار']},
            {'name': 'آذربایجان شرقی', 'cities': ['تبریز', 'مراغه', 'اهر']},
        ]

        for prov_data in provinces_data:
            province, created = Province.objects.get_or_create(
                name=prov_data['name'],
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ استان {province.name} ایجاد شد'))

            for city_name in prov_data['cities']:
                City.objects.get_or_create(
                    province=province,
                    name=city_name,
                )

        # ═══════════ ۵. قالب‌های پیامک ═══════════
        from apps.notifications.models import SMSTemplate

        templates_data = [
            ('login', 'کد تایید ورود', 'zibano-otp', 'کد تایید: {code}', ['code']),
            ('change_phone', 'تغییر شماره', 'zibano-change-phone', 'کد تایید: {code}', ['code']),
            ('booking_verify', 'تایید رزرو', 'zibano-booking-verify', 'کد تایید نوبت: {code}', ['code']),
        ]

        for t_type, name, provider_id, pattern, variables in templates_data:
            SMSTemplate.objects.get_or_create(
                type=t_type,
                defaults={
                    'name': name,
                    'provider_template_id': provider_id,
                    'pattern': pattern,
                    'variables': variables,
                },
            )

        self.stdout.write(self.style.SUCCESS('✓ قالب‌های پیامک ایجاد شد'))

        self.stdout.write(self.style.SUCCESS('\n✅ ایجاد داده‌های اولیه با موفقیت انجام شد!'))
        self.stdout.write(self.style.WARNING('\n💡 اطلاعات ورود:'))
        self.stdout.write(self.style.WARNING('  Phone: 09120000000'))
        self.stdout.write(self.style.WARNING('  Password: admin123456'))