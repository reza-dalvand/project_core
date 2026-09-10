from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_android_update_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='appconfig',
            name='is_maintenance_modal_enabled',
            field=models.BooleanField(
                default=True,
                help_text='اگر غیرفعال باشد، حتی در حالت تعمیرات مدال نمایش داده نمی‌شود (هم وب و هم اندروید)',
                verbose_name='نمایش مدال تعمیرات',
            ),
        ),
    ]