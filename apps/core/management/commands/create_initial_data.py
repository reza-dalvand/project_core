# apps/core/management/commands/create_initial_data.py

"""
ایجاد کاربر ادمین اولیه برای توسعه
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "ایجاد کاربر Superuser اولیه برای توسعه"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.WARNING("🚀 شروع ایجاد کاربر اولیه...")
        )

        phone = "09909412001"
        password = "Reza2009!2009"

        if User.objects.filter(phone=phone).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️ کاربری با شماره {phone} از قبل وجود دارد."
                )
            )
        else:
            User.objects.create_superuser(
                phone=phone,
                password=password,
                first_name="مدیر",
                last_name="ارشد",
            )

            self.stdout.write(
                self.style.SUCCESS("✓ Superuser با موفقیت ایجاد شد")
            )

        self.stdout.write(
            self.style.SUCCESS("\n✅ عملیات با موفقیت انجام شد!")
        )

        self.stdout.write(
            self.style.WARNING("\n💡 اطلاعات ورود:")
        )
        self.stdout.write(
            self.style.WARNING(f"  Phone: {phone}")
        )
        self.stdout.write(
            self.style.WARNING(f"  Password: {password}")
        )