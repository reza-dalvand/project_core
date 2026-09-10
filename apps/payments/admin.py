from django.contrib import admin
from .models import Transaction, Settlement


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'tracking_code', 'customer', 'business', 'type',
        'amount', 'app_fee', 'status', 'gateway', 'created_at',
    ]
    list_filter = ['type', 'status', 'gateway']
    search_fields = ['tracking_code', 'customer__phone', 'business__name']
    readonly_fields = ['tracking_code', 'ref_number']
    # ✅ FIX: raw_id_fields برای پرفورمنس بهتر
    raw_id_fields = ['business', 'customer', 'appointment']
    date_hierarchy = 'created_at'
    fieldsets = (
        ('💰 اطلاعات تراکنش', {
            'fields': (
                'business', 'customer', 'appointment',
                'type', 'amount', 'app_fee', 'status',
            ),
        }),
        ('🏦 درگاه پرداخت', {
            'fields': (
                'gateway', 'gateway_transaction_id',
                'tracking_code', 'ref_number',
                'card_number', 'card_bank',
            ),
        }),
        ('📅 تسویه', {
            'fields': ('settled_at', 'estimated_settlement'),
            'classes': ('collapse',),
        }),
        ('❌ استرداد', {
            'fields': ('refund_reason',),
            'classes': ('collapse',),
        }),
    )


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ['business', 'amount', 'status', 'bank_name', 'settled_at']
    list_filter = ['status']
    search_fields = ['business__name', 'bank_sheba']
    raw_id_fields = ['business']
    readonly_fields = ['settled_at']