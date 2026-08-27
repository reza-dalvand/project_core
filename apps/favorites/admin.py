from django.contrib import admin
from .models import FavoriteBusiness, FavoritePost


@admin.register(FavoriteBusiness)
class FavoriteBusinessAdmin(admin.ModelAdmin):
    list_display = ['user', 'business', 'created_at']
    list_filter = ['business']
    search_fields = ['user__phone', 'business__name']


@admin.register(FavoritePost)
class FavoritePostAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    search_fields = ['user__phone']