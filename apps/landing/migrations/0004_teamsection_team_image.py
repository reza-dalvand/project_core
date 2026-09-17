# Generated manually for team_image field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0003_footerlinkgroup_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamsection',
            name='team_image',
            field=models.ImageField(
                blank=True,
                help_text='اگر خالی باشد، تصویر پیش‌فرض آدمک‌ها نمایش داده می‌شود',
                null=True,
                upload_to='team/group/',
                verbose_name='عکس گروهی تیم',
            ),
        ),
    ]