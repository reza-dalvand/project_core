"""
ایجاد کسب‌وکارهای فیک برای توسعه و تست

نمونه اجرا:
    python manage.py create_fake_businesses
    python manage.py create_fake_businesses --count 20
    python manage.py create_fake_businesses --count 5 --no-schedules
"""
import random
from datetime import time as dtime

import jdatetime
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()

# ───────────────────────────────────────────────
#   کد ملی معتبر فیک
# ───────────────────────────────────────────────
def generate_valid_national_id():
    digits = [random.randint(0, 9) for _ in range(9)]
    total = sum(d * (10 - i) for i, d in enumerate(digits))
    remainder = total % 11
    check = remainder if remainder < 2 else 11 - remainder
    digits.append(check)
    return ''.join(map(str, digits))


# ───────────────────────────────────────────────
#   انواع کسب‌وکار (باید با BusinessCategory همخوانی داشته باشد)
# ───────────────────────────────────────────────
BUSINESS_CATEGORIES = [
    'خدمات چند منظوره',
    'خدمات ناخن',
    'خدمات مو',
    'خدمات پوست و صورت',
    'خدمات ابرو و مژه',
]

# ───────────────────────────────────────────────
#   دسته‌بندی خدمات + زیرخدمات (برای ساخت سرویس)
#   اگر اینها در دیتابیس نبودند، خود کامند می‌سازد
# ───────────────────────────────────────────────
SERVICE_CATEGORIES = {
    'ناخن': {
        'icon_name': 'nail',
        'color': '#FF6B8A',
        'gradient_start': '#FF8FA3',
        'gradient_end': '#FF6B8A',
        'sub_services': {
            'کاشت ناخن ژله‌ای': 'nail_gel',
            'کاشت ناخن پودر': 'nail_powder',
            'مانیکور': 'manicure',
            'پدیکور': 'pedicure',
            'ژلیش ناخن': 'gel_polish',
            'طراحی ناخن': 'nail_art',
            'ترمیم ناخن': 'nail_repair',
        },
    },
    'پوست و صورت': {
        'icon_name': 'spa',
        'color': '#4ECDC4',
        'gradient_start': '#7EDDD6',
        'gradient_end': '#4ECDC4',
        'sub_services': {
            'فیشیال کلاسیک': 'facial_classic',
            'فیشیال تخصصی': 'facial_special',
            'پاکسازی پوست': 'skin_cleanse',
            'آبرسانی پوست': 'skin_hydration',
            'درمان آکنه': 'acne_treatment',
            'میکرودرم ابریژن': 'microdermabrasion',
        },
    },
    'مو': {
        'icon_name': 'content_cut',
        'color': '#9B5DE5',
        'gradient_start': '#BB86FC',
        'gradient_end': '#9B5DE5',
        'sub_services': {
            'کراتینه مو': 'hair_keratin',
            'پروتئین تراپی': 'protein_therapy',
            'رنگ مو': 'hair_color',
            'دکلره مو': 'hair_bleach',
            'کوتاهی مو': 'haircut',
            'براشینگ مو': 'hair_brushing',
        },
    },
    'ابرو و مژه': {
        'icon_name': 'visibility',
        'color': '#F15BB5',
        'gradient_start': '#FF7BCD',
        'gradient_end': '#F15BB5',
        'sub_services': {
            'فیبروز ابرو': 'fibroze_brow',
            'میکروبلیدینگ': 'microblading',
            'لیفت ابرو': 'eyebrow_lift',
            'کاشت مژه': 'lash_extension',
            'لیفت مژه': 'lash_lift',
            'لامینت مژه': 'lash_laminate',
        },
    },
}

# ───────────────────────────────────────────────
#   شهرها + مختصات
# ───────────────────────────────────────────────
CITIES = {
    'تهران': {'province': 'تهران', 'lat': 35.7898, 'lng': 51.3768},
    'اصفهان': {'province': 'اصفهان', 'lat': 32.6546, 'lng': 51.6680},
    'شیراز': {'province': 'فارس', 'lat': 29.5918, 'lng': 52.5837},
    'مشهد': {'province': 'خراسان رضوی', 'lat': 36.2605, 'lng': 59.6168},
    'تبریز': {'province': 'آذربایجان شرقی', 'lat': 38.0800, 'lng': 46.2919},
}

# ───────────────────────────────────────────────
#   نام‌های فیک برای کسب‌وکارها
# ───────────────────────────────────────────────
BUSINESS_NAMES = [
    'سالن زیبایی رز', 'سالن آریانا', 'کلینیک پوست و مو نیلوفر',
    'سالن ستاره', 'سالن مروارید',
    'سالن ونوس', 'کلینیک زیبایی پریسا', 'سالن یاس',
    'مرکز ابرو و مژه سایه', 'سالن ارکیده', 'سالن شبنم',
    'کلینیک پوست آبنوس', 'سالن طلایی',
    'سالن گلستان', 'سالن صدف', 'مرکز ناخن پونه',
    'سالن خورشید', 'سالن بهار',
]

WORKING_HOURS = [
    'شنبه تا پنجشنبه ۹ تا ۱۸',
    'شنبه تا چهارشنبه ۱۰ تا ۲۰',
    'شنبه تا پنجشنبه ۸ تا ۲۱',
    'همه روزه ۱۰ تا ۲۲',
    'شنبه تا جمعه ۹ تا ۲۰',
]

ABOUT_TEXTS = [
    'با بیش از ۱۰ سال سابقه در زمینه خدمات زیبایی، مفتخریم که بهترین خدمات را به مشتریان عزیز ارائه دهیم.',
    'سالن ما با کادری مجرب و مواد درجه یک، آماده خدمت‌رسانی به شما عزیزان است.',
    'ما با استفاده از جدیدترین متدهای روز دنیا، خدمات زیبایی را با کیفیت بالا ارائه می‌دهیم.',
    'هدف ما جلب رضایت مشتریان عزیز با ارائه خدمات با کیفیت و قیمتی مناسب است.',
    'با کادری حرفه‌ای و محیطی آرام و دلنشین، میزبان شما عزیزان هستیم.',
]


class Command(BaseCommand):
    help = 'ایجاد کسب‌وکارهای فیک با سرویس‌ها و زمان‌بندی برای توسعه و تست'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=10,
            help='تعداد کسب‌وکارها (پیش‌فرض: ۱۰)',
        )
        parser.add_argument(
            '--no-schedules', action='store_true',
            help='زمان‌بندی (ServiceSchedule) ایجاد نشود',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = min(options['count'], len(BUSINESS_NAMES))
        create_schedules = not options['no_schedules']

        self.stdout.write(self.style.WARNING(
            f'🚀 شروع ایجاد {count} کسب‌وکار فیک...'
        ))

        # ─── ۱. ساخت/دریافت دسته‌بندی‌ها ───
        self.stdout.write('📦 در حال ساخت دسته‌بندی‌ها...')
        self._ensure_business_categories()
        cat_map = self._ensure_service_categories()

        # ─── ۲. ساخت/دریافت مکان‌ها ───
        self.stdout.write('📍 در حال ساخت مکان‌ها...')
        city_map = self._ensure_cities()

        # ─── ۳. ساخت کسب‌وکارها ───
        created_biz = 0
        for i in range(count):
            biz = self._create_business(i, city_map)
            if biz is None:
                continue
            created_biz += 1

            # سرویس‌ها
            services = self._create_services(biz, cat_map)

            # زمان‌بندی
            if create_schedules and services:
                sched_count = self._create_schedules(biz, services)
                self.stdout.write(
                    f'   🕐 {sched_count} زمان‌بندی برای «{biz.name}»'
                )

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {created_biz} کسب‌وکار فیک ایجاد شد.'
        ))

    # ───────────────────────────────────────────
    #   دسته‌بندی‌ها
    # ───────────────────────────────────────────
    def _ensure_business_categories(self):
        from apps.categories.models import BusinessCategory
        for name in BUSINESS_CATEGORIES:
            BusinessCategory.objects.get_or_create(name=name)

    def _ensure_service_categories(self):
        from apps.categories.models import ServiceCategory, SubService
        cat_map = {}
        for cat_name, cat_info in SERVICE_CATEGORIES.items():
            category, _ = ServiceCategory.objects.get_or_create(
                name=cat_name,
                defaults={
                    'icon_name': cat_info['icon_name'],
                    'color': cat_info['color'],
                    'gradient_start': cat_info['gradient_start'],
                    'gradient_end': cat_info['gradient_end'],
                    'sort_order': len(cat_map) + 1,
                },
            )
            sub_map = {}
            for sub_name, type_id in cat_info['sub_services'].items():
                from django.utils.text import slugify
                slug = slugify(sub_name, allow_unicode=True)
                sub, _ = SubService.objects.get_or_create(
                    category=category,
                    slug=slug,
                    defaults={'name': sub_name, 'type_id': type_id},
                )
                sub_map[sub_name] = sub
            cat_map[cat_name] = {'category': category, 'subs': sub_map}
        return cat_map

    # ───────────────────────────────────────────
    #   مکان‌ها
    # ───────────────────────────────────────────
    def _ensure_cities(self):
        from apps.locations.models import Province, City
        city_map = {}
        for city_name, info in CITIES.items():
            province, _ = Province.objects.get_or_create(name=info['province'])
            city, _ = City.objects.get_or_create(
                province=province,
                name=city_name,
                defaults={'slug': city_name},
            )
            city_map[city_name] = {'city': city, **info}
        return city_map

    # ───────────────────────────────────────────
    #   ساخت کسب‌وکار
    # ───────────────────────────────────────────
    def _create_business(self, index, city_map):
        from apps.businesses.models import Business
        from apps.categories.models import BusinessCategory

        name = BUSINESS_NAMES[index]
        if Business.objects.filter(name=name).exists():
            self.stdout.write(f'   ⚠ «{name}» از قبل وجود دارد، رد شد.')
            return None

        # ─── کاربر مالک فیک ───
        phone = f'0919900{str(index + 1).zfill(4)}'
        owner, _ = User.objects.get_or_create(
            phone=phone,
            defaults={
                'first_name': random.choice(
                    ['مریم', 'زهرا', 'فاطمه', 'سارا', 'نرگس', 'مهسا', 'پریسا', 'الهام']
                ),
                'last_name': random.choice(
                    ['محمدی', 'احمدی', 'حسینی', 'کریمی', 'رضایی', 'جعفری', 'موسوی']
                ),
                'is_verified': True,
                'is_active': True,
                'is_national_id_verified': True,
                'verified_name': '',
                'national_id': generate_valid_national_id(),
            },
        )

        city_name = random.choice(list(city_map.keys()))
        city_info = city_map[city_name]
        category = BusinessCategory.objects.filter(
            name__in=BUSINESS_CATEGORIES
        ).order_by('?').first()

        national_id = generate_valid_national_id()
        verified_name = f'{owner.first_name} {owner.last_name}'

        biz = Business.objects.create(
            owner=owner,
            name=name,
            category=category,
            province=city_info['city'].province,
            city=city_info['city'],
            address=f'{city_name}، خیابان ولیعصر، کوچه بهار، پلاک {random.randint(1, 200)}',
            phone=phone,
            working_hours=random.choice(WORKING_HOURS),
            about=random.choice(ABOUT_TEXTS),
            latitude=city_info['lat'] + random.uniform(-0.05, 0.05),
            longitude=city_info['lng'] + random.uniform(-0.05, 0.05),
            status=Business.Status.APPROVED,
            national_id=national_id,
            verified_name=verified_name,
            is_national_id_verified=True,
            bank_owner_name=verified_name,
            bank_national_id=national_id,
            bank_name=random.choice(['ملی', 'ملت', 'صادرات', 'پاسارگاد', 'سامان']),
            bank_sheba='IR' + ''.join(
                str(random.randint(0, 9)) for _ in range(24)
            ),
            bank_card_number=''.join(
                str(random.randint(0, 9)) for _ in range(16)
            ),
            bank_info_registered=True,
            bank_info_verified=True,
            is_vip=random.choice([True, False, False]),
            rating=round(random.uniform(3.5, 5.0), 1),
            reviews_count=random.randint(5, 120),
        )

        self.stdout.write(self.style.SUCCESS(
            f'   ✓ کسب‌وکار «{biz.name}» ({category.name}) در {city_name} ایجاد شد'
        ))
        return biz

    # ───────────────────────────────────────────
    #   ساخت سرویس‌ها
    # ───────────────────────────────────────────
    def _create_services(self, biz, cat_map):
        from apps.services.models import Service

        # انتخاب ۳ دسته تصادفی برای تنوع
        cat_names = random.sample(list(cat_map.keys()), k=min(3, len(cat_map)))
        services = []

        for cat_name in cat_names:
            cat_info = cat_map[cat_name]
            sub_names = random.sample(
                list(cat_info['subs'].keys()),
                k=min(1, len(cat_info['subs'])),
            )
            for sub_name in sub_names:
                sub = cat_info['subs'][sub_name]
                price = random.randint(15, 80) * 10000
                deposit = random.choice([0, 0, 50000, 100000, 150000])
                if deposit > price:
                    deposit = price // 4

                service = Service.objects.create(
                    business=biz,
                    name=f'{sub_name} - {biz.name}',
                    category=cat_info['category'],
                    sub_service=sub,
                    description='ارائه خدمت با کیفیت بالا توسط کادر مجرب و با استفاده از مواد درجه یک.',
                    original_price=price,
                    discount_percent=random.choice([0, 0, 10, 15, 20]),
                    has_deposit=deposit > 0,
                    deposit_amount=deposit,
                    duration=random.choice([30, 45, 60, 90, 120]),
                    renewal_days=random.choice([0, 30, 60, 90]),
                    is_active=True,
                )
                services.append(service)

        return services

    # ───────────────────────────────────────────
    #   ساخت زمان‌بندی (۷ روز آینده)
    # ───────────────────────────────────────────
    def _create_schedules(self, biz, services):
        from apps.schedules.models import ServiceSchedule

        today = jdatetime.date.today()
        count = 0

        for service in services:
            for day_offset in range(7):
                target = today + jdatetime.timedelta(days=day_offset)
                date_key = f'{target.year}/{target.month:02d}/{target.day:02d}'

                # جلوگیری از تکرار
                if ServiceSchedule.objects.filter(
                    service=service, date_key=date_key
                ).exists():
                    continue

                ServiceSchedule.objects.create(
                    business=biz,
                    service=service,
                    jy=target.year,
                    jm=target.month,
                    jd=target.day,
                    date_key=date_key,
                    work_start=dtime(random.choice([8, 9, 10]), 0),
                    work_end=dtime(random.choice([18, 19, 20, 21]), 0),
                    slot_duration=service.duration or 30,
                    breaks=[{'start': '13:00', 'end': '14:00'}],
                )
                count += 1

        return count