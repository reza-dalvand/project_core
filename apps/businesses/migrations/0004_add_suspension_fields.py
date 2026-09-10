"""
افزودن فیلدهای تعلیق به Business + مدل BusinessViolation
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('businesses', '0003_alter_business_latitude_alter_business_longitude'),
    ]

    operations = [
        migrations.AddField(
            model_name='business',
            name='is_suspended',
            field=models.BooleanField(
                default=False,
                db_index=True,
                verbose_name='تعلیق شده (تخلف)',
                help_text='در صورت فعال بودن، کسب‌وکار از جستجو حذف شده و رزرو جدید ممنوع است.',
            ),
        ),
        migrations.AddField(
            model_name='business',
            name='suspension_reason',
            field=models.TextField(
                blank=True,
                default='',
                verbose_name='دلیل تعلیق',
            ),
        ),
        migrations.AddField(
            model_name='business',
            name='suspended_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='زمان تعلیق',
            ),
        ),
        migrations.CreateModel(
            name='BusinessViolation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('cancellation_count', models.IntegerField(verbose_name='تعداد لغو توسط سالن در بازه')),
                ('period_start', models.DateTimeField(verbose_name='شروع بازه بررسی')),
                ('period_end', models.DateTimeField(verbose_name='پایان بازه بررسی')),
                ('is_resolved', models.BooleanField(
                    default=False,
                    db_index=True,
                    verbose_name='رسیدگی شده (تعلیق یا رد)',
                )),
                ('business', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='violations',
                    to='businesses.business',
                    verbose_name='کسب‌وکار',
                )),
            ],
            options={
                'verbose_name': '⚠️ تخلف کسب‌وکار',
                'verbose_name_plural': '⚠️ تخلفات کسب‌وکارها',
                'db_table': 'business_violations',
                'ordering': ['-created_at'],
            },
        ),
    ]