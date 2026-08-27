"""
Manager سفارشی برای مدل کاربر
"""
from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    """
    Manager سفارشی برای User
    کاربر با شماره موبایل احراز هویت می‌شود (نه ایمیل)
    """

    def _create_user(self, phone, password=None, **extra_fields):
        """ساخت کاربر پایه"""
        if not phone:
            raise ValueError('شماره موبایل الزامی است')

        from apps.core.utils import to_english_digits
        phone = to_english_digits(phone).strip()

        if phone.startswith('+98'):
            phone = '0' + phone[3:]
        elif phone.startswith('0098'):
            phone = '0' + phone[4:]

        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        """ساخت کاربر عادی"""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        """ساخت مدیر ارشد"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(phone, password, **extra_fields)