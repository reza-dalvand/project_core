# apps/portfolios/migrations/0002_migrate_cover_and_remove_field.py
from django.db import migrations, connection

def migrate_cover_to_gallery(apps, schema_editor):
    """
    انتقال دیتای cover_image به گالری.
    ✅ ایمن: ابتدا چک می‌کند ستون در دیتابیس وجود دارد یا خیر.
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name='portfolios' AND column_name='cover_image'
            )
        """)
        column_exists = cursor.fetchone()[0]

    if not column_exists:
        # ستون قبلاً حذف شده، نیازی به انتقال دیتا نیست
        return

    Portfolio = apps.get_model('portfolios', 'Portfolio')
    PortfolioImage = apps.get_model('portfolios', 'PortfolioImage')

    for portfolio in Portfolio.objects.filter(cover_image__isnull=False).exclude(cover_image=''):
        if not portfolio.images.exists():
            PortfolioImage.objects.create(
                portfolio=portfolio,
                image=portfolio.cover_image,
                sort_order=0,
            )

def reverse_migration(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('portfolios', '0001_initial'),
    ]

    operations = [
        # 1️⃣ انتقال دیتا (با بررسی امن)
        migrations.RunPython(
            migrate_cover_to_gallery,
            reverse_migration,
        ),
        # 2️⃣ حذف ستون با SQL ایمن (IF EXISTS) + آپدیت State جنگو
        migrations.RunSQL(
            sql="ALTER TABLE portfolios DROP COLUMN IF EXISTS cover_image;",
            reverse_sql="ALTER TABLE portfolios ADD COLUMN cover_image VARCHAR(100) NULL;",
            state_operations=[
                migrations.RemoveField(
                    model_name='portfolio',
                    name='cover_image',
                ),
            ],
        ),
    ]