from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('businesses', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='business',
            name='booking_slug',
            field=models.SlugField(
                allow_unicode=True,
                unique=True,
                verbose_name='اسلاگ رزرو',
            ),
        ),
    ]