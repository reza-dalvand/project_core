from django.contrib import admin
from .models import Business, BusinessGallery, BusinessTeamMember


class BusinessGalleryInline(admin.TabularInline):
    model = BusinessGallery
    extra = 3
    max_num = 3


class BusinessTeamMemberInline(admin.TabularInline):
    model = BusinessTeamMember
    extra = 2


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'owner', 'category', 'city',
        'status', 'rating', 'reviews_count', 'is_vip',
    ]
    list_filter = ['status', 'is_vip', 'category', 'province']
    search_fields = ['name', 'owner__phone', 'owner__first_name', 'owner__last_name']
    readonly_fields = ['booking_slug', 'rating', 'reviews_count', 'booking_link_clicks', 'booking_link_bookings']
    inlines = [BusinessGalleryInline, BusinessTeamMemberInline]

    fieldsets = (
        ('🏪 اطلاعات پایه', {
            'fields': ('owner', 'name', 'category', 'province', 'city', 'address', 'phone', 'working_hours', 'about'),
        }),
        ('🖼️ تصاویر', {
            'fields': ('cover_image', 'owner_photo', 'logo'),
        }),
        ('📍 موقعیت جغرافیایی', {
            'fields': ('latitude', 'longitude'),
        }),
        ('✅ وضعیت تایید', {
            'fields': ('status', 'rejection_reason'),
        }),
        ('🆔 احراز هویت', {
            'fields': ('national_id', 'verified_name', 'is_national_id_verified'),
        }),
        ('🏦 حساب بانکی', {
            'fields': (
                'bank_owner_name', 'bank_national_id', 'bank_name', 'bank_id',
                'bank_sheba', 'bank_card_number', 'bank_account_number',
                'bank_info_registered', 'bank_info_verified',
            ),
            'classes': ('collapse',),
        }),
        ('🔗 لینک رزرو', {
            'fields': ('booking_slug', 'booking_link_clicks', 'booking_link_bookings'),
        }),
        ('⭐ آمار', {
            'fields': ('rating', 'reviews_count'),
        }),
        ('👑 VIP', {
            'fields': ('is_vip', 'vip_expires_at'),
        }),
    )


@admin.register(BusinessGallery)
class BusinessGalleryAdmin(admin.ModelAdmin):
    list_display = ['business', 'sort_order']
    list_filter = ['business']


@admin.register(BusinessTeamMember)
class BusinessTeamMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'phone']
    list_filter = ['business']
    search_fields = ['name', 'phone']