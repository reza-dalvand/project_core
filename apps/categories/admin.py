from django.contrib import admin
from .models import ServiceCategory, SubService, BusinessCategory


class SubServiceInline(admin.TabularInline):
    model = SubService
    extra = 3


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon_name', 'color', 'sort_order', 'is_active']
    list_editable = ['sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    inlines = [SubServiceInline]


@admin.register(SubService)
class SubServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'type_id', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name']


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']