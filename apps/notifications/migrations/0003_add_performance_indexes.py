# apps/notifications/migrations/0003_add_performance_indexes.py
"""
فاز ۵: افزودن ایندکس‌های عملکردی
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_smstemplate_send_method"),
    ]

    operations = [
        # ─── Notification indexes (فیلد created_at وجود دارد ✅) ───
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["user", "created_at"],
                name="notif_user_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["type", "created_at"],
                name="notif_type_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["is_read", "created_at"],
                name="notif_read_created_idx",
            ),
        ),
        # ─── SMSLog indexes ───
        migrations.AddIndex(
            model_name="smslog",
            index=models.Index(
                fields=["user", "sent_at"],   
                name="smslog_user_sent_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="smslog",
            index=models.Index(
                fields=["template", "sent_at"], 
                name="smslog_template_sent_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="smslog",
            index=models.Index(
                fields=["sent_at"],             
                name="smslog_created_idx",
            ),
        ),
    ]