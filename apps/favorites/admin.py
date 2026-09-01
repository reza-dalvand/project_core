from django.contrib import admin
from .models import FavoriteBusiness


@admin.register(FavoriteBusiness)
class FavoriteBusinessAdmin(admin.ModelAdmin):
    list_display = ['user', 'business', 'created_at']
    list_filter = ['business']
    search_fields = ['user__phone', 'business__name']


