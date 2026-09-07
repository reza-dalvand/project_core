from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewTagVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('tag_id', models.CharField(max_length=50, verbose_name='شناسه تگ')),
                ('vote_type', models.CharField(choices=[('like', 'لایک'), ('dislike', 'دیسلایک')], max_length=10, verbose_name='نوع رای')),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tag_votes', to='reviews.review', verbose_name='نظر')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_tag_votes', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
            options={
                'verbose_name': '👍 رای تگ نظر',
                'verbose_name_plural': '👍 رای‌های تگ نظرات',
                'db_table': 'review_tag_votes',
                'unique_together': {('review', 'tag_id', 'user')},
            },
        ),
    ]