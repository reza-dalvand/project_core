"""
حذف ستون role از جدول users
این ستون در نسخه قبلی مدل وجود داشت ولی در ری‌فکتور حذف شده.
دیتابیس فیزیکی هنوز آن را دارد و باعث NotNullViolation می‌شود.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_otpcode_purpose'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE users DROP COLUMN IF EXISTS role;",
            reverse_sql=(
                "ALTER TABLE users ADD COLUMN role VARCHAR(50) NULL;"
            ),
        ),
    ]