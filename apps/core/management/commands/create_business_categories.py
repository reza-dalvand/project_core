# apps/core/management/commands/create_business_categories.py
"""
ایجاد انواع کسب‌وکارها
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'ایجاد انواع کسب‌وکارها'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('🚀 شروع ایجاد انواع کسب‌وکارها...'))

        from apps.categories.models import BusinessCategory

        business_types = [
            'خدمات چند منظوره',
            'خدمات ناخن',
            'خدمات مو',
            'خدمات پوست و صورت',
            'خدمات ابرو و مژه',
        ]

        for name in business_types:
            obj, created = BusinessCategory.objects.get_or_create(
                name=name,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ کسب‌وکار {obj.name} ایجاد شد'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ کسب‌وکار {obj.name} از قبل وجود دارد'))

        self.stdout.write(self.style.SUCCESS('\n✅ ایجاد انواع کسب‌وکارها با موفقیت انجام شد!'))