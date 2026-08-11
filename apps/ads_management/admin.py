from django.contrib import admin
from .models import AdCampaign


@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'status', 'budget', 'spent',
        'impressions', 'clicks', 'created_at',
    ]
    list_filter = ['status']
    search_fields = ['name']