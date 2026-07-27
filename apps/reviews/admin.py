"""
Admin configuration for reviews app
"""
from django.contrib import admin
from apps.core.admin_mixins import AppStaffMixin
from .models import ReviewTag, Review, ReviewResponse


@admin.register(ReviewTag)
class ReviewTagAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['label', 'icon', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['label']


class ReviewResponseInline(admin.StackedInline):
    model = ReviewResponse
    extra = 0
    max_num = 1
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Review)
class ReviewAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = [
        'customer', 'business', 'service',
        'rating', 'is_approved', 'is_hidden', 'created_at'
    ]
    list_filter = ['rating', 'is_approved', 'is_hidden', 'created_at']
    search_fields = ['customer__phone', 'business__name', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['customer', 'appointment', 'business', 'service']
    inlines = [ReviewResponseInline]
    date_hierarchy = 'created_at'

    actions = ['approve_reviews', 'hide_reviews', 'unhide_reviews']

    @admin.action(description='✅ تایید نظرات انتخاب‌شده')
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description='🙈 مخفی کردن نظرات')
    def hide_reviews(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description='👁️ نمایش نظرات مخفی')
    def unhide_reviews(self, request, queryset):
        queryset.update(is_hidden=False)


@admin.register(ReviewResponse)
class ReviewResponseAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = ['review', 'business', 'created_at']
    list_filter = ['created_at']
    search_fields = ['review__customer__phone', 'business__name', 'text']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['review', 'business']