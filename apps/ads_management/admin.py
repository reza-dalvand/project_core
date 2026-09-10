from django.contrib import admin
from .models import AdCampaign, AdBanner

@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'budget', 'spent', 'impressions', 'clicks', 'created_at']
    list_filter = ['status']
    search_fields = ['name']

@admin.register(AdBanner)
class AdBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'business', 'badge', 'order', 'is_active', 'starts_at', 'expires_at']
    list_filter = ['is_active', 'business']
    search_fields = ['title', 'description', 'business__name']
    list_editable = ['order', 'is_active']
    raw_id_fields = ['business']
    fieldsets = (
        ('محتوای بنر', {
            'fields': ('title', 'description', 'image', 'badge')
        }),
        ('لینک و مقصد', {
            'fields': ('business', 'custom_url')
        }),
        ('تنظیمات نمایش', {
            'fields': ('order', 'is_active', 'starts_at', 'expires_at')
        }),
    )