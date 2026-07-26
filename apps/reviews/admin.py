from django.contrib import admin
from apps.core.admin_mixins import AppStaffMixin
from .models import ReviewTag, Review, ReviewResponse


@admin.register(ReviewTag)
class ReviewTagAdmin(admin.ModelAdmin):
    list_display = ['label', 'icon', 'is_active', 'order']
    list_editable = ['order', 'is_active']


class ReviewResponseInline(admin.StackedInline):
    model = ReviewResponse
    extra = 0
    max_num = 1


@admin.register(Review)
class ReviewAdmin(AppStaffMixin, admin.ModelAdmin):
    list_display = [
        'customer', 'business', 'service',
        'rating', 'is_approved', 'is_hidden', 'created_at'
    ]
    list_filter = ['rating', 'is_approved', 'is_hidden', 'created_at']
    search_fields = ['customer__phone', 'business__name', 'comment']
    readonly_fields = ['created_at']
    inlines = [ReviewResponseInline]
    actions = ['approve_reviews', 'hide_reviews', 'unhide_reviews']

    @admin.action(description='✅ تایید نظرات انتخاب شده')
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description='🙈 مخفی کردن نظرات')
    def hide_reviews(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description='👁️ نمایش نظرات مخفی')
    def unhide_reviews(self, request, queryset):
        queryset.update(is_hidden=False)