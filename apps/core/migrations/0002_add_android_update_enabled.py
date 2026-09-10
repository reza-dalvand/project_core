from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_appconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='appconfig',
            name='android_force_update_enabled',
            field=models.BooleanField(
                default=True,
                help_text='اگر غیرفعال باشد، مدال آپدیت اجباری در اندروید نمایش داده نمی‌شود',
                verbose_name='نمایش مدال آپدیت اجباری در اندروید',
            ),
        ),
        migrations.AddField(
            model_name='appconfig',
            name='android_optional_update_enabled',
            field=models.BooleanField(
                default=True,
                help_text='اگر غیرفعال باشد، مدال آپدیت اختیاری در اندروید نمایش داده نمی‌شود',
                verbose_name='نمایش مدال آپدیت اختیاری در اندروید',
            ),
        ),
    ]