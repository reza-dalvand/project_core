"""
Management Command: ایجاد تگ‌های پیش‌فرض برای نظرات
"""
from django.core.management.base import BaseCommand
from apps.reviews.models import ReviewTag


class Command(BaseCommand):
    help = 'ایجاد تگ‌های پیش‌فرض برای نظرات'

    DEFAULT_TAGS = [
        {
            'label': 'مکان تمیز بود',
            'icon': 'cleaning_services',
            'order': 1,
        },
        {
            'label': 'سر وقت انجام شد',
            'icon': 'schedule',
            'order': 2,
        },
        {
            'label': 'کیفیت عالی بود',
            'icon': 'star',
            'order': 3,
        },
        {
            'label': 'رفتار محترمانه',
            'icon': 'favorite',
            'order': 4,
        },
        {
            'label': 'قیمت مناسب بود',
            'icon': 'attach_money',
            'order': 5,
        },
        {
            'label': 'پیشنهاد می‌کنم',
            'icon': 'thumb_up',
            'order': 6,
        },
        {
            'label': 'تجهیزات حرفه‌ای',
            'icon': 'build',
            'order': 7,
        },
        {
            'label': 'محیط آرامش‌بخش',
            'icon': 'self_improvement',
            'order': 8,
        },
    ]

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('🏷️  شروع ایجاد تگ‌های پیش‌فرض...'))

        created_count = 0
        existing_count = 0

        for tag_data in self.DEFAULT_TAGS:
            tag, created = ReviewTag.objects.get_or_create(
                label=tag_data['label'],
                defaults={
                    'icon': tag_data['icon'],
                    'order': tag_data['order'],
                    'is_active': True,
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ تگ "{tag_data["label"]}" ایجاد شد'))
                created_count += 1
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ تگ "{tag_data["label"]}" از قبل وجود دارد'))
                existing_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ ایجاد تگ‌ها با موفقیت انجام شد!'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  • {created_count} تگ جدید ایجاد شد'
        ))
        self.stdout.write(self.style.WARNING(
            f'  • {existing_count} تگ از قبل وجود داشت'
        ))