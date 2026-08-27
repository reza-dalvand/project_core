from django.db import migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='linerental',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True,
                geography=True,
                null=True,
                srid=4326,
                verbose_name='موقعیت جغرافیایی'
            ),
        ),
        migrations.AddField(
            model_name='modelrequest',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True,
                geography=True,
                null=True,
                srid=4326,
                verbose_name='موقعیت جغرافیایی'
            ),
        ),
    ]