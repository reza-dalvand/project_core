from django.contrib import admin
from .models import SearchHistory


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'query', 'result_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__phone', 'query']
    readonly_fields = ['created_at']