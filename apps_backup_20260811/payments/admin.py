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
    date_hierarchy = 'created_at'


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ['business', 'amount', 'status', 'bank_name', 'settled_at']
    list_filter = ['status']
    search_fields = ['business__name', 'bank_sheba']