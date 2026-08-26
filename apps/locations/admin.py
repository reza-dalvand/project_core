from django.contrib import admin
from .models import Province, City


class CityInline(admin.TabularInline):
    model = City
    extra = 3


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    inlines = [CityInline]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'province', 'is_active']
    list_filter = ['province', 'is_active']
    search_fields = ['name']