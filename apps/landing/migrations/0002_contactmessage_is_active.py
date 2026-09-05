from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactmessage',
            name='is_active',
            field=models.BooleanField(
                default=True,
                verbose_name='فعال',
            ),
        ),
    ]