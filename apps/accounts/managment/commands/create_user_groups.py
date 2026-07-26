"""
Management Command: ایجاد گروه‌های استاندارد کاربران
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import CustomUser


class Command(BaseCommand):
    help = 'ایجاد گروه‌های استاندارد کاربران با دسترسی‌های مشخص'

    # تعریف گروه‌ها و دسترسی‌هایشان
    GROUPS_PERMISSIONS = {
        'landing_admin': {
            'description': 'ادمین سایت معرفی',
            'apps': ['landing'],
            'permissions': ['view', 'add', 'change', 'delete'],
        },
        'app_admin': {
            'description': 'ادمین بک‌اند اپلیکیشن (دسترسی کامل)',
            'apps': ['accounts', 'businesses', 'bookings', 'payments', 'reviews', 'notifications'],
            'permissions': ['view', 'add', 'change', 'delete'],
        },
        'app_staff': {
            'description': 'کارمند اپ (پشتیبان)',
            'apps': ['accounts', 'businesses', 'bookings', 'payments', 'reviews', 'notifications'],
            'permissions': ['view'],  # فقط مشاهده
            'extra_permissions': {
                # این‌ها را می‌تواند تغییر دهد
                'reviews.review': ['change'],  # تایید نظرات
                'bookings.cancellationrequest': ['change'],  # تایید لغو
                'payments.refundrequest': ['change'],  # تایید استرداد
                'notifications.notification': ['add', 'change'],  # ارسال اعلان
            },
        },
        'business_owner': {
            'description': 'صاحب کسب‌وکار (دسترسی به داده‌های خود)',
            'apps': [],
            'permissions': [],
            'extra_permissions': {
                'businesses.business': ['view', 'change'],
                'businesses.service': ['view', 'add', 'change', 'delete'],
                'businesses.portfolio': ['view', 'add', 'change', 'delete'],
                'businesses.portfolioimage': ['view', 'add', 'change', 'delete'],
                'businesses.workinghours': ['view', 'add', 'change', 'delete'],
                'businesses.workinghoursbreak': ['view', 'add', 'change', 'delete'],
                'businesses.linerentalad': ['view', 'add', 'change', 'delete'],
                'businesses.modelrequest': ['view', 'add', 'change', 'delete'],
                'businesses.socialmedia': ['view', 'add', 'change', 'delete'],
                'bookings.appointment': ['view'],
                'bookings.timeslot': ['view'],
                'payments.transaction': ['view'],
                'payments.bankaccount': ['view', 'add', 'change'],
                'reviews.review': ['view'],
                'reviews.reviewresponse': ['add', 'change'],
            },
        },
    }

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('🚀 شروع ایجاد گروه‌های کاربری...'))

        for group_name, config in self.GROUPS_PERMISSIONS.items():
            # ایجاد یا دریافت گروه
            group, created = Group.objects.get_or_create(name=group_name)

            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ گروه "{group_name}" ایجاد شد'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ گروه "{group_name}" از قبل وجود دارد'))
                # پاک کردن permission های قبلی
                group.permissions.clear()

            permissions_to_add = []

            # افزودن permission های پایه بر اساس اپ‌ها
            for app_label in config['apps']:
                content_types = ContentType.objects.filter(app_label=app_label)
                for content_type in content_types:
                    for perm_type in config['permissions']:
                        codename = f'{perm_type}_{content_type.model}'
                        try:
                            perm = Permission.objects.get(
                                content_type=content_type,
                                codename=codename
                            )
                            permissions_to_add.append(perm)
                        except Permission.DoesNotExist:
                            pass

            # افزودن permission های اضافی
            for model_path, perm_types in config.get('extra_permissions', {}).items():
                app_label, model_name = model_path.split('.')
                try:
                    content_type = ContentType.objects.get(
                        app_label=app_label,
                        model=model_name
                    )
                    for perm_type in perm_types:
                        codename = f'{perm_type}_{model_name}'
                        try:
                            perm = Permission.objects.get(
                                content_type=content_type,
                                codename=codename
                            )
                            permissions_to_add.append(perm)
                        except Permission.DoesNotExist:
                            self.stdout.write(self.style.WARNING(
                                f'  ⚠ Permission یافت نشد: {codename}'
                            ))
                except ContentType.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ ContentType یافت نشد: {model_path}'
                    ))

            # افزودن همه permission ها به گروه
            if permissions_to_add:
                group.permissions.add(*permissions_to_add)
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ {len(permissions_to_add)} permission به گروه "{group_name}" اضافه شد'
                ))

        # ═══════ ایجاد Superuser نمونه (اختیاری) ═══════
        self.stdout.write(self.style.WARNING('\n📊 خلاصه گروه‌ها:'))
        for group in Group.objects.all():
            perm_count = group.permissions.count()
            self.stdout.write(self.style.SUCCESS(
                f'  • {group.name}: {perm_count} permission'
            ))

        self.stdout.write(self.style.SUCCESS('\n✅ ایجاد گروه‌ها با موفقیت انجام شد!'))
        self.stdout.write(self.style.WARNING('\n💡 برای استفاده:'))
        self.stdout.write(self.style.WARNING('  1. یک کاربر با role دلخواه بسازید'))
        self.stdout.write(self.style.WARNING('  2. کاربر را Staff کنید (is_staff=True)'))
        self.stdout.write(self.style.WARNING('  3. کاربر را به گروه مربوطه اضافه کنید'))
        self.stdout.write(self.style.WARNING('  4. وارد پنل admin شوید'))