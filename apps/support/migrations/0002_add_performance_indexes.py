# apps/support/migrations/0002_add_performance_indexes.py

"""
فاز ۵: افزودن ایندکس‌های عملکردی
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("support", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="supportticket",
            index=models.Index(
                fields=["user", "created_at"],
                name="ticket_user_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="supportticket",
            index=models.Index(
                fields=["status", "priority"],
                name="ticket_status_priority_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="supportticket",
            index=models.Index(
                fields=["status", "created_at"],
                name="ticket_status_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="supportticket",
            index=models.Index(
                fields=["user", "status"],
                name="ticket_user_status_idx",
            ),
        ),
    ]