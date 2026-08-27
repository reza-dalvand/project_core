from django.contrib import admin
from .models import Portfolio, PortfolioImage


class PortfolioImageInline(admin.TabularInline):
    model = PortfolioImage
    extra = 3
    max_num = 3


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['title', 'business', 'category', 'sub_service', 'created_at']
    list_filter = ['category', 'business']
    search_fields = ['title', 'business__name']
    inlines = [PortfolioImageInline]


@admin.register(PortfolioImage)
class PortfolioImageAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'sort_order']
    list_filter = ['portfolio']