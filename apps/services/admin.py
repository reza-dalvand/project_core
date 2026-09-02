from django.contrib import admin
from .models import Service, PriceList, PriceListNote


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
    raw_id_fields = ['business', 'category', 'sub_service']
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


# ✅ NEW: ثبت مدل PriceList
class PriceListNoteInline(admin.TabularInline):
    model = PriceListNote
    extra = 1
    max_num = 10


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['business', 'theme', 'is_published', 'notes_count', 'created_at']
    list_filter = ['theme', 'is_published']
    search_fields = ['business__name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['business']
    inlines = [PriceListNoteInline]
    fieldsets = (
        ('📋 اطلاعات لیست قیمت', {
            'fields': ('business', 'theme', 'is_published'),
        }),
        ('📅 تاریخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def notes_count(self, obj):
        return obj.notes.count()
    notes_count.short_description = 'تعداد یادداشت‌ها'


# ✅ NEW: ثبت مدل PriceListNote
@admin.register(PriceListNote)
class PriceListNoteAdmin(admin.ModelAdmin):
    list_display = ['label', 'price_list', 'min_value', 'max_value', 'created_at']
    list_filter = ['price_list__business']
    search_fields = ['label', 'price_list__business__name']
    raw_id_fields = ['price_list']