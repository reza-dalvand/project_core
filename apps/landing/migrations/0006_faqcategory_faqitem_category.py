# apps/landing/migrations/0006_faqcategory_faqitem_category.py
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0005_alter_teamsection_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='FAQCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='عنوان تب')),
                ('icon', models.CharField(blank=True, default='', max_length=50, verbose_name='آیکون (Material Icon)')),
                ('order', models.IntegerField(default=0, verbose_name='ترتیب')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('section', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='categories', to='landing.faqsection', verbose_name='بخش سوالات')),
            ],
            options={
                'verbose_name': '📂 تب سوالات',
                'verbose_name_plural': '📂 تب‌های سوالات',
                'ordering': ['order'],
            },
        ),
        migrations.AddField(
            model_name='faqitem',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='items', to='landing.faqcategory', verbose_name='دسته‌بندی (تب)'),
        ),
    ]