
from django.contrib import admin
from apps.core.admin_mixins import AppAdminMixin, AppStaffMixin
from .models import (
    Wallet, WalletTransaction,
    BankAccount, Transaction,
    Settlement, RefundRequest,
)


# ═══════════════════════════════════════════════════════════════
#                    Wallet
# ═══════════════════════════════════════════════════════════════
class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ['created_at', 'amount', 'type', 'balance_after']


@admin.register(Wallet)
class WalletAdmin(AppAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'balance', 'is_frozen', 'updated_at']
    list_filter = ['is_frozen', 'updated_at']
    search_fields = ['user__phone', 'user__full_name']
    readonly_fields = ['total_credit', 'total_debit', 'updated_at']
    inlines = [WalletTransactionInline]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['wallet', 'amount', 'type', 'balance_after', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['wallet__user__phone']
    readonly_fields = ['created_at']


# ═══════════════════════════════════════════════════════════════
#                    Bank Account
# ═══════════════════════════════════════════════════════════════
@admin.register(BankAccount)
class BankAccountAdmin(AppAdminMixin, admin.ModelAdmin):
    list_display = [
        'owner_name', 'bank_name', 'user', 'business',
        'status', 'is_active', 'created_at',
    ]
    list_filter = ['status', 'is_active', 'bank_name', 'created_at']
    search_fields = ['owner_name', 'national_id', 'sheba', 'card_number']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['verify_accounts', 'reject_accounts']

    @admin.action(description='✅ تایید حساب‌های انتخاب شده')
    def verify_accounts(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='verified', verified_at=timezone.now())

    @admin.action(description='❌ رد حساب‌های انتخاب شده')
    def reject_accounts(self, request, queryset):
        queryset.update(status='rejected')


# ═══════════════════════════════════════════════════════════════
#                    Transaction
# ═══════════════════════════════════════════════════════════════
@admin.register(Transaction)
class TransactionAdmin(AppAdminMixin, admin.ModelAdmin):
    list_display = [
        'tracking_code', 'user', 'type', 'amount',
        'status', 'gateway', 'created_at',
    ]
    list_filter = ['type', 'status', 'gateway', 'created_at']
    search_fields = [
        'tracking_code', 'ref_number', 'user__phone',
        'user__full_name', 'gateway_ref_id',
    ]
    readonly_fields = [
        'tracking_code', 'ref_number', 'commission_amount',
        'net_amount', 'created_at', 'paid_at', 'settled_at', 'refunded_at',
    ]
    date_hierarchy = 'created_at'
    raw_id_fields = ['user', 'appointment', 'business']


# ═══════════════════════════════════════════════════════════════
#                    Settlement
# ═══════════════════════════════════════════════════════════════
@admin.register(Settlement)
class SettlementAdmin(AppAdminMixin, admin.ModelAdmin):
    list_display = [
        'business', 'amount', 'status',
        'frequency', 'requested_at', 'completed_at',
    ]
    list_filter = ['status', 'frequency', 'requested_at', 'completed_at']
    search_fields = ['business__name', 'bank_ref_code']
    readonly_fields = ['requested_at', 'processed_at', 'completed_at']
    raw_id_fields = ['business', 'bank_account']
    actions = ['approve_settlements', 'reject_settlements']

    @admin.action(description='✅ تایید و پردازش تسویه‌ها')
    def approve_settlements(self, request, queryset):
        from django.utils import timezone
        queryset.filter(status='pending').update(
            status='processing',
            processed_at=timezone.now(),
        )

    @admin.action(description='❌ رد تسویه‌ها')
    def reject_settlements(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')


# ═══════════════════════════════════════════════════════════════
#                    Refund Request
# ═══════════════════════════════════════════════════════════════
@admin.register(RefundRequest)
class RefundRequestAdmin(AppAdminMixin, admin.ModelAdmin):
    list_display = [
        'transaction', 'requested_by', 'amount',
        'reason', 'status', 'requested_at',
    ]
    list_filter = ['status', 'reason', 'requested_at', 'refunded_at']
    search_fields = [
        'transaction__tracking_code',
        'requested_by__phone',
    ]
    readonly_fields = ['requested_at', 'reviewed_at', 'refunded_at']
    raw_id_fields = ['transaction', 'appointment', 'requested_by', 'reviewed_by', 'refund_transaction']
    actions = ['approve_refunds', 'reject_refunds']

    @admin.action(description='✅ تایید درخواست‌های استرداد')
    def approve_refunds(self, request, queryset):
        from django.utils import timezone
        queryset.filter(status='pending').update(
            status='approved',
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )

    @admin.action(description='❌ رد درخواست‌های استرداد')
    def reject_refunds(self, request, queryset):
        from django.utils import timezone
        queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )