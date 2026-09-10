"""
کامند برای ایجاد دسته‌بندی‌های اصلی و زیرخدمات زیبایی

دسته‌بندی‌های اصلی:
- ناخن
- پوست و صورت
- مو
- ابرو و مژه

زیرخدمات بر اساس خدمات رایج سالن‌های زیبایی ایران
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.categories.models import ServiceCategory, SubService


class Command(BaseCommand):
    help = 'ایجاد دسته‌بندی‌های اصلی و زیرخدمات زیبایی'

    # داده‌های دسته‌بندی‌ها و زیرخدمات
    categories_data = [
        {
            'name': 'ناخن',
            'icon_name': 'nail',
            'color': '#FF6B8A',
            'gradient_start': '#FF8FA3',
            'gradient_end': '#FF6B8A',
            'sort_order': 1,
            'sub_services': [
                {'name': 'کاشت ناخن ژله‌ای', 'type_id': 'nail_gel'},
                {'name': 'کاشت ناخن پودر', 'type_id': 'nail_powder'},
                {'name': 'کاشت ناخن دیپ', 'type_id': 'nail_dip'},
                {'name': 'مانیکور', 'type_id': 'manicure'},
                {'name': 'پدیکور', 'type_id': 'pedicure'},
                {'name': 'ژلیش ناخن', 'type_id': 'gel_polish'},
                {'name': 'طراحی ناخن', 'type_id': 'nail_art'},
                {'name': 'ترمیم ناخن', 'type_id': 'nail_repair'},
                {'name': 'استون کاری', 'type_id': 'nail_removal'},
                {'name': 'لمینت ناخن', 'type_id': 'nail_laminate'},
                {'name': 'فیشیال ناخن', 'type_id': 'nail_facial'},
                {'name': 'کاشت ناخن شیشه‌ای', 'type_id': 'nail_glass'},
                {'name': 'کاشت ناخن فیبری', 'type_id': 'nail_fiber'},
            ],
        },
        {
            'name': 'پوست و صورت',
            'icon_name': 'skin_face',
            'color': '#4ECDC4',
            'gradient_start': '#7EDDD6',
            'gradient_end': '#4ECDC4',
            'sort_order': 2,
            'sub_services': [
                {'name': 'فیشیال کلاسیک', 'type_id': 'facial_classic'},
                {'name': 'فیشیال تخصصی', 'type_id': 'facial_special'},
                {'name': 'فیشیال هیدرودرمی', 'type_id': 'facial_hydroderm'},
                {'name': 'پاکسازی پوست', 'type_id': 'skin_cleanse'},
                {'name': 'آبرسانی پوست', 'type_id': 'skin_hydration'},
                {'name': 'جوانسازی پوست', 'type_id': 'skin_rejuvenation'},
                {'name': 'درمان آکنه', 'type_id': 'acne_treatment'},
                {'name': 'درمان لک پوستی', 'type_id': 'spot_treatment'},
                {'name': 'میکرودرم ابریژن', 'type_id': 'microdermabrasion'},
                {'name': 'مزوتراپی صورت', 'type_id': 'mesotherapy_face'},
                {'name': 'PRP صورت', 'type_id': 'prp_face'},
                {'name': 'لیفت صورت', 'type_id': 'face_lift'},
                {'name': 'ماسک صورت', 'type_id': 'face_mask'},
                {'name': 'لایه برداری پوست', 'type_id': 'skin_peeling'},
                {'name': 'درمان چروک', 'type_id': 'wrinkle_treatment'},
            ],
        },
        {
            'name': 'مو',
            'icon_name': 'hair',
            'color': '#9B5DE5',
            'gradient_start': '#BB86FC',
            'gradient_end': '#9B5DE5',
            'sort_order': 3,
            'sub_services': [
                {'name': 'کراتینه مو', 'type_id': 'hair_keratin'},
                {'name': 'پروتئین تراپی', 'type_id': 'protein_therapy'},
                {'name': 'باتوکس مو', 'type_id': 'hair_botox'},
                {'name': 'آمپول مو', 'type_id': 'hair_injection'},
                {'name': 'رنگ مو', 'type_id': 'hair_color'},
                {'name': 'دکلره مو', 'type_id': 'hair_bleach'},
                {'name': 'مش و هایلایت', 'type_id': 'highlights'},
                {'name': 'بالیاژ', 'type_id': 'balayage'},
                {'name': 'آمبره', 'type_id': 'ombre'},
                {'name': 'صاف کردن مو', 'type_id': 'hair_straightening'},
                {'name': 'فر مو', 'type_id': 'hair_curl'},
                {'name': 'کوتاهی مو', 'type_id': 'haircut'},
                {'name': 'اصلاح مو', 'type_id': 'hair_trim'},
                {'name': 'براشینگ مو', 'type_id': 'hair_brushing'},
                {'name': 'شینیون مو', 'type_id': 'hair_updo'},
                {'name': 'بافت مو', 'type_id': 'hair_braid'},
                {'name': 'اکستنشن مو', 'type_id': 'hair_extension'},
                {'name': 'حنا گذاری', 'type_id': 'henna'},
            ],
        },
        {
            'name': 'ابرو و مژه',
            'icon_name': 'brow_lash',
            'color': '#F15BB5',
            'gradient_start': '#FF7BCD',
            'gradient_end': '#F15BB5',
            'sort_order': 4,
            'sub_services': [
                {'name': 'فیبروز ابرو', 'type_id': 'fibroze_brow'},
                {'name': 'میکروبلیدینگ', 'type_id': 'microblading'},
                {'name': 'تاتو ابرو', 'type_id': 'eyebrow_tattoo'},
                {'name': 'رژ لب دائم', 'type_id': 'lip_blush'},
                {'name': 'خط چشم دائم', 'type_id': 'eyeliner_tattoo'},
                {'name': 'شیدینگ ابرو', 'type_id': 'eyebrow_shading'},
                {'name': 'قرینه سازی ابرو', 'type_id': 'eyebrow_symmetry'},
                {'name': 'لیفت ابرو', 'type_id': 'eyebrow_lift'},
                {'name': 'لامینیت ابرو', 'type_id': 'eyebrow_laminate'},
                {'name': 'کاشت مژه', 'type_id': 'lash_extension'},
                {'name': 'لیفت مژه', 'type_id': 'lash_lift'},
                {'name': 'لمینت مژه', 'type_id': 'lash_laminate'},
                {'name': 'حجم دهی مژه', 'type_id': 'lash_volume'},
                {'name': 'ریموو تاتو', 'type_id': 'tattoo_removal'},
                {'name': 'اصلاح ابرو', 'type_id': 'eyebrow_trim'},
            ],
        },
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('🔄 شروع ایجاد دسته‌بندی‌ها و زیرخدمات...')

        created_categories = 0
        updated_categories = 0
        created_sub_services = 0

        for cat_data in self.categories_data:
            category, created = ServiceCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'icon_name': cat_data['icon_name'],
                    'color': cat_data['color'],
                    'gradient_start': cat_data['gradient_start'],
                    'gradient_end': cat_data['gradient_end'],
                    'sort_order': cat_data['sort_order'],
                }
            )

            if created:
                created_categories += 1
                self.stdout.write(f'✅ دسته‌بندی ایجاد شد: {category.name}')
            else:
                updated_categories += 1
                # بروزرسانی اطلاعات در صورت نیاز
                category.icon_name = cat_data['icon_name']
                category.color = cat_data['color']
                category.gradient_start = cat_data['gradient_start']
                category.gradient_end = cat_data['gradient_end']
                category.sort_order = cat_data['sort_order']
                category.save()
                self.stdout.write(f'🔃 دسته‌بندی بروزرسانی شد: {category.name}')

            # ایجاد زیرخدمات
            for sub_data in cat_data['sub_services']:
                sub_service, created = SubService.objects.get_or_create(
                    category=category,
                    type_id=sub_data['type_id'],
                    defaults={'name': sub_data['name']}
                )
                if created:
                    created_sub_services += 1
                    self.stdout.write(f'   └─ ✅ زیرخدمت ایجاد شد: {sub_service.name}')

        # جمع‌بندی
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('📊 گزارش نهایی:'))
        self.stdout.write(self.style.SUCCESS(f'   • دسته‌بندی‌های جدید: {created_categories}'))
        self.stdout.write(self.style.SUCCESS(f'   • دسته‌بندی‌های بروزرسانی شده: {updated_categories}'))
        self.stdout.write(self.style.SUCCESS(f'   • زیرخدمات جدید: {created_sub_services}'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
