# Generated for ZarinPal migration
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='gateway',
            field=models.CharField(
                default='zarinpal',
                max_length=50,
                verbose_name='درگاه پرداخت',
            ),
        ),
    ]