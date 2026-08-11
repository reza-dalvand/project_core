from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'business', 'category', 'sub_service',
        'original_price', 'discount_percent', 'final_price',
        'has_deposit', 'deposit_amount', 'duration',
        'renewal_days', 'is_active',
    ]
    list_filter = ['is_active', 'has_deposit', 'category']
    search_fields = ['name', 'business__name']
    readonly_fields = ['final_price', 'app_fee']

    fieldsets = (
        ('💆 اطلاعات خدمت', {
            'fields': ('business', 'name', 'category', 'sub_service', 'description'),
        }),
        ('💰 قیمت‌گذاری', {
            'fields': ('original_price', 'discount_percent', 'final_price'),
        }),
        ('🏦 بیعانه', {
            'fields': ('has_deposit', 'deposit_amount'),
        }),
        ('⏱️ زمان', {
            'fields': ('duration', 'renewal_days'),
        }),
        ('⚡ وضعیت', {
            'fields': ('is_active',),
        }),
        ('📊 کمیسیون', {
            'fields': ('app_fee',),
            'classes': ('collapse',),
        }),
    )