from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AppConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latest_version', models.CharField(default='1.0.0', max_length=20, verbose_name='آخرین نسخه')),
                ('min_required_version', models.CharField(default='1.0.0', max_length=20, verbose_name='حداقل نسخه مورد نیاز')),
                ('is_force_update', models.BooleanField(default=False, verbose_name='آپدیت اجباری')),
                ('update_title', models.CharField(default='نسخه جدید بیو کلاب منتشر شد!', max_length=200, verbose_name='عنوان آپدیت')),
                ('update_message', models.TextField(default='برای تجربه بهتر، لطفاً به آخرین نسخه به‌روزرسانی کنید.', verbose_name='پیام آپدیت')),
                ('changelog', models.JSONField(blank=True, default=list, help_text='لیست تغییرات: [{"icon": "✨", "text": "بهبود عملکرد"}]', verbose_name='تغییرات نسخه')),
                ('store_url', models.URLField(blank=True, default='https://beauclub.ir', verbose_name='لینک آپدیت')),
                ('store_name', models.CharField(blank=True, default='بیو کلاب وب', max_length=100, verbose_name='نام فروشگاه')),
                ('is_maintenance', models.BooleanField(default=False, verbose_name='حالت تعمیرات فعال')),
                ('maintenance_title', models.CharField(default='در حال بروزرسانی هستیم 🔧', max_length=200, verbose_name='عنوان تعمیرات')),
                ('maintenance_message', models.TextField(default='تیم فنی بیو کلاب در حال انجام بهبودهای لازم است. لطفاً دقایقی دیگر مراجعه فرمایید.', verbose_name='پیام تعمیرات')),
                ('maintenance_estimated_end', models.CharField(blank=True, default='', max_length=100, verbose_name='زمان تقریبی پایان')),
                ('maintenance_reason', models.TextField(blank=True, default='', verbose_name='دلیل تعمیرات')),
                ('support_phone', models.CharField(blank=True, default='', max_length=20, verbose_name='شماره پشتیبانی')),
            ],
            options={
                'db_table': 'app_config',
                'verbose_name': '⚙️ تنظیمات اپلیکیشن',
                'verbose_name_plural': '⚙️ تنظیمات اپلیکیشن',
            },
        ),
    ]