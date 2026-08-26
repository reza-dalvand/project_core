from django.contrib import admin
from .models import ModelRequest, LineRental


@admin.register(ModelRequest)
class ModelRequestAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'business', 'service',
        'cost_type', 'discount', 'is_urgent', 'created_at',
    ]
    list_filter = ['cost_type', 'is_urgent']
    search_fields = ['title', 'business__name']


@admin.register(LineRental)
class LineRentalAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'business', 'collab_type',
        'service_category', 'contact_phone', 'created_at',
    ]
    list_filter = ['collab_type', 'service_category']
    search_fields = ['title', 'business__name']