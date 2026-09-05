from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('action', models.CharField(
                    db_index=True,
                    help_text='مثلاً: business.approved',
                    max_length=100,
                    verbose_name='عملیات',
                )),
                ('admin_phone', models.CharField(
                    max_length=20,
                    verbose_name='شماره ادمین',
                )),
                ('admin_role', models.CharField(
                    max_length=50,
                    verbose_name='نقش ادمین',
                )),
                ('client_ip', models.CharField(
                    blank=True,
                    default='',
                    max_length=45,
                    verbose_name='آدرس IP',
                )),
                ('target_type', models.CharField(
                    blank=True,
                    default='',
                    max_length=50,
                    verbose_name='نوع هدف',
                )),
                ('target_id', models.CharField(
                    blank=True,
                    max_length=50,
                    null=True,
                    verbose_name='شناسه هدف',
                )),
                ('target_name', models.CharField(
                    blank=True,
                    default='',
                    max_length=200,
                    verbose_name='نام هدف',
                )),
                ('details', models.JSONField(
                    blank=True,
                    default=dict,
                    verbose_name='جزئیات',
                )),
                ('severity', models.CharField(
                    choices=[
                        ('info', 'اطلاعاتی'),
                        ('warning', 'هشدار'),
                        ('critical', 'بحرانی'),
                    ],
                    default='info',
                    max_length=20,
                    verbose_name='شدت',
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                    db_index=True,
                    verbose_name='زمان ثبت',
                )),
            ],
            options={
                'verbose_name': '📋 لاگ حسابرسی',
                'verbose_name_plural': '📋 لاگ‌های حسابرسی',
                'db_table': 'dashboard_audit_logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['action', '-created_at'],
                name='dash_audit_action_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['admin_phone', '-created_at'],
                name='dash_audit_admin_idx',
            ),
        ),
    ]