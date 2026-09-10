from django.contrib import admin
from .models import FavoriteBusiness, FavoritePost, FavoritePortfolio


@admin.register(FavoriteBusiness)
class FavoriteBusinessAdmin(admin.ModelAdmin):
    list_display = ['user', 'business', 'created_at']
    list_filter = ['business']
    search_fields = ['user__phone', 'business__name']


@admin.register(FavoritePost)
class FavoritePostAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    list_filter = ['post__business']
    search_fields = ['user__phone', 'post__caption']


@admin.register(FavoritePortfolio)
class FavoritePortfolioAdmin(admin.ModelAdmin):
    list_display = ['user', 'portfolio', 'created_at']
    list_filter = ['portfolio__business']
    search_fields = ['user__phone', 'portfolio__title']