from django.contrib import admin
from .models import ExplorePost, PostImage


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 3


@admin.register(ExplorePost)
class ExplorePostAdmin(admin.ModelAdmin):
    list_display = ['business', 'source', 'caption_preview', 'is_pinned', 'created_at']
    list_filter = ['source', 'is_pinned']
    search_fields = ['caption', 'business__name']
    inlines = [PostImageInline]

    def caption_preview(self, obj):
        return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption
    caption_preview.short_description = 'کپشن'


@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ['post', 'sort_order']
    list_filter = ['post']