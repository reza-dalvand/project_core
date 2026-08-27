from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='smstemplate',
            name='send_method',
            field=models.CharField(
                choices=[
                    ('otp', 'پترن احراز هویت (verify_lookup)'),
                    ('simple', 'پیام ساده (sms_send)'),
                    ('bulk', 'ارسال گروهی (sms_sendarray)'),
                ],
                default='simple',
                max_length=20,
                verbose_name='روش ارسال',
            ),
        ),
    ]