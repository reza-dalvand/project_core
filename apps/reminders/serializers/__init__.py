from rest_framework import serializers

import jdatetime

from apps.reminders.models import RenewalReminder
from apps.reminders.services import get_today_jalali


class RenewalReminderSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    # ✅ اضافه شدن فیلدهای مشتری
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    customer_name = serializers.SerializerMethodField()

    # ✅ days_remaining به‌صورت dynamic محاسبه می‌شود
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = RenewalReminder
        fields = [
            "id",
            "business",
            "business_name",
            "customer",
            "customer_name",
            "customer_phone",
            "service",
            "service_name",
            "last_service_date",
            "due_date",
            "days_remaining",
            "reminder_sent",
            "sent_date",
            "has_new_booking_after_send",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "business",
            "customer",
            "service",
            "last_service_date",
            "due_date",
            "reminder_sent",
            "sent_date",
            "has_new_booking_after_send",
            "created_at",
        ]

    def get_customer_name(self, obj):
        # استخراج نام مشتری (بسته به مدل User شما)
        if hasattr(obj.customer, "full_name") and obj.customer.full_name:
            return obj.customer.full_name

        name = f"{obj.customer.first_name} {obj.customer.last_name}".strip()
        return name or "مشتری"

    def get_days_remaining(self, obj):
        """
        محاسبه لحظه‌ای روزهای باقی‌مانده بر اساس due_date.

        این کار باعث می‌شود حتی اگر مقدار ذخیره‌شده در دیتابیس یک روز stale شود،
        API مقدار درست به فرانت‌اند بدهد.
        """
        try:
            parts = str(obj.due_date).split("/")
            if len(parts) != 3:
                raise ValueError

            due_date = jdatetime.date(
                int(parts[0]),
                int(parts[1]),
                int(parts[2]),
            )

            today = get_today_jalali()
            return (due_date - today).days

        except Exception:
            # fallback به مقدار ذخیره‌شده
            return obj.days_remaining