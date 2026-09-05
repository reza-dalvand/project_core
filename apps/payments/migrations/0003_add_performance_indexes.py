# apps/payments/migrations/0003_add_performance_indexes.py
"""
فاز ۵: افزودن ایندکس‌های عملکردی
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_alter_transaction_gateway'),
    ]

    operations = [
        # Transaction indexes
        migrations.AddIndex(
        model_name='transaction',
        index=models.Index(
        fields=['status', 'created_at'],
        name='tx_status_created_idx',
        ),
        ),
        migrations.AddIndex(
        model_name='transaction',
        index=models.Index(
        fields=['business', 'type', 'status'],
        name='tx_biz_type_status_idx',
        ),
        ),
        migrations.AddIndex(
        model_name='transaction',
        index=models.Index(
        fields=['customer', 'created_at'],
        name='tx_customer_created_idx',
        ),
        ),
        migrations.AddIndex(
        model_name='transaction',
        index=models.Index(
        fields=['gateway', 'status'],
        name='tx_gateway_status_idx',
        ),
        ),
        migrations.AddIndex(
        model_name='transaction',
        index=models.Index(
        fields=['settled_at'],
        name='tx_settled_at_idx',
        ),
        ),
        migrations.AddIndex(
        model_name='transaction',
        index=models.Index(
        fields=['tracking_code'],
        name='tx_tracking_code_idx',
        ),
        ),
        # Settlement indexes
        migrations.AddIndex(
        model_name='settlement',
        index=models.Index(
        fields=['status', 'created_at'],
        name='settle_status_created_idx',
        ),
        ),
        migrations.AddIndex(
        model_name='settlement',
        index=models.Index(
        fields=['business', 'status'],
        name='settle_biz_status_idx',
        ),
        ),
        migrations.AddIndex(
        model_name='settlement',
        index=models.Index(
        fields=['settled_at'],
        name='settle_settled_at_idx',
        ),
        ),
    ]