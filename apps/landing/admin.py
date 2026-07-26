"""
Admin configuration for landing app (سایت معرفی زیبانو)
پنل مدیریت کامل سایت معرفی زیبانو
"""
from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from apps.core.admin_mixins import LandingAdminMixin
from .models import (
    SiteSettings,
    HeroSection,
    FeaturesSection, Feature,
    HowToSection, HowToStep,
    ServicesSection, ServiceCategory,
    AboutSection, AboutPoint,
    TeamSection, TeamMember,
    StatsSection, StatItem,
    FAQSection, FAQItem,
    ContactSection, ContactMessage,
    DownloadSection,
    TrustBadge,
    NavItem,
    FooterLinkGroup, FooterLink,
)


# ═══════════════════════════════════════════════════════════════
#                    Inline Admin Classes
# ═══════════════════════════════════════════════════════════════
class FeatureInline(admin.TabularInline):
    model = Feature
    extra = 3
    fields = ['icon', 'title', 'description', 'color', 'order', 'is_active']


class HowToStepInline(admin.TabularInline):
    model = HowToStep
    extra = 4
    fields = ['step_number', 'icon', 'title', 'description', 'order', 'is_active']


class ServiceCategoryInline(admin.TabularInline):
    model = ServiceCategory
    extra = 4
    fields = ['icon', 'name', 'count', 'order', 'is_active']


class AboutPointInline(admin.TabularInline):
    model = AboutPoint
    extra = 3
    fields = ['icon', 'title', 'description', 'order', 'is_active']


class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 2
    fields = ['avatar', 'full_name', 'role', 'description', 'initials', 'order', 'is_active']


class StatItemInline(admin.TabularInline):
    model = StatItem
    extra = 4
    fields = ['icon', 'value', 'display_text', 'label', 'order', 'is_active']


class FAQItemInline(admin.TabularInline):
    model = FAQItem
    extra = 3
    fields = ['question', 'answer', 'order', 'is_active']


class FooterLinkInline(admin.TabularInline):
    model = FooterLink
    extra = 3
    fields = ['label', 'url', 'order', 'is_active']


# ═══════════════════════════════════════════════════════════════
#                    Model Admin Classes
# ═══════════════════════════════════════════════════════════════
@admin.register(SiteSettings)
class SiteSettingsAdmin(LandingAdminMixin, admin.ModelAdmin):
    """مدیریت تنظیمات سایت"""

    list_display = ['site_name', 'site_slogan', 'phone', 'email', 'is_active']

    fieldsets = (
        ('🏷️ برندینگ', {
            'fields': ('site_name', 'site_slogan', 'logo', 'logo_icon', 'favicon'),
        }),
        ('🎨 رنگ‌بندی', {
            'fields': ('primary_color', 'primary_dark_color', 'primary_light_color', 'background_color'),
            'classes': ('collapse',),
        }),
        ('🔍 سئو', {
            'fields': ('meta_description', 'meta_keywords'),
        }),
        ('📞 اطلاعات تماس', {
            'fields': ('phone', 'email', 'address', 'working_hours'),
        }),
        ('📱 لینک‌های دانلود', {
            'fields': ('cafebazaar_url', 'myket_url', 'google_play_url', 'app_store_url'),
        }),
        ('🌐 شبکه‌های اجتماعی', {
            'fields': ('instagram_url', 'telegram_url', 'whatsapp_url', 'twitter_url'),
            'classes': ('collapse',),
        }),
        ('🛡️ ای‌نماد', {
            'fields': ('enamad_image', 'enamad_code'),
            'classes': ('collapse',),
        }),
        ('📝 فوتر', {
            'fields': ('footer_text', 'copyright_year'),
        }),
        ('⚡ وضعیت', {
            'fields': ('is_active',),
        }),
    )

    def has_add_permission(self, request):
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HeroSection)
class HeroSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    """مدیریت بخش هیرو"""

    list_display = ['title', 'badge_text', 'stat1_value', 'stat2_value', 'stat3_value', 'is_active']

    fieldsets = (
        ('📝 محتوا', {
            'fields': ('badge_text', 'title', 'title_highlight', 'description'),
        }),
        ('🔘 دکمه‌ها', {
            'fields': (
                ('primary_btn_text', 'primary_btn_icon'),
                ('secondary_btn_text', 'secondary_btn_icon'),
            ),
        }),
        ('📊 آمار هیرو', {
            'fields': (
                ('stat1_icon', 'stat1_value', 'stat1_label'),
                ('stat2_icon', 'stat2_value', 'stat2_label'),
                ('stat3_icon', 'stat3_value', 'stat3_label'),
            ),
        }),
        ('🖼️ تصویر', {
            'fields': ('hero_image',),
            'classes': ('collapse',),
        }),
        ('⚡ وضعیت', {
            'fields': ('is_active',),
        }),
    )

    def has_add_permission(self, request):
        if HeroSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(FeaturesSection)
class FeaturesSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    """مدیریت بخش ویژگی‌ها"""

    list_display = ['title', 'badge_text', 'is_active', 'order']
    inlines = [FeatureInline]

    def has_add_permission(self, request):
        if FeaturesSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(Feature)
class FeatureAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'icon', 'color_colored', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']

    def color_colored(self, obj):
        return format_html(
            '<span style="display:inline-block;width:20px;height:20px;'
            'border-radius:4px;background:{};margin-left:8px;"></span>{}',
            obj.color, obj.color
        )
    color_colored.short_description = 'رنگ'


@admin.register(HowToSection)
class HowToSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'is_active', 'order']
    inlines = [HowToStepInline]

    def has_add_permission(self, request):
        if HowToSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(ServicesSection)
class ServicesSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'is_active', 'order']
    inlines = [ServiceCategoryInline]

    def has_add_permission(self, request):
        if ServicesSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(AboutSection)
class AboutSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'card_title', 'is_active', 'order']
    inlines = [AboutPointInline]

    fieldsets = (
        ('📝 محتوای اصلی', {
            'fields': ('badge_text', 'title', 'description'),
        }),
        ('🎴 کارت بصری', {
            'fields': ('card_title', 'card_description'),
        }),
        ('📊 آمار کارت', {
            'fields': (
                ('card_stat1_value', 'card_stat1_label'),
                ('card_stat2_value', 'card_stat2_label'),
                ('card_stat3_value', 'card_stat3_label'),
            ),
        }),
        ('⚡ وضعیت', {
            'fields': ('is_active', 'order'),
        }),
    )

    def has_add_permission(self, request):
        if AboutSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(TeamSection)
class TeamSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'is_active', 'order']
    inlines = [TeamMemberInline]

    def has_add_permission(self, request):
        if TeamSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(TeamMember)
class TeamMemberAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['full_name', 'role', 'avatar_preview', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;">',
                obj.avatar.url
            )
        return format_html(
            '<span style="display:inline-block;width:40px;height:40px;border-radius:50%;'
            'background:#A88B7D;color:#fff;text-align:center;line-height:40px;font-weight:bold;">{}</span>',
            obj.get_initials()
        )
    avatar_preview.short_description = 'عکس'


@admin.register(StatsSection)
class StatsSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['__str__', 'is_active', 'order']
    inlines = [StatItemInline]

    def has_add_permission(self, request):
        if StatsSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(FAQSection)
class FAQSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'is_active', 'order']
    inlines = [FAQItemInline]

    def has_add_permission(self, request):
        if FAQSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(FAQItem)
class FAQItemAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['question_short', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']

    def question_short(self, obj):
        return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
    question_short.short_description = 'سوال'


@admin.register(ContactSection)
class ContactSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'is_active', 'order']

    fieldsets = (
        ('📝 محتوای اصلی', {
            'fields': ('badge_text', 'badge_icon', 'title', 'subtitle'),
        }),
        ('📇 کارت اطلاعات', {
            'fields': ('card_title', 'card_description'),
        }),
        ('📬 فرم تماس', {
            'fields': ('form_title', 'form_description', 'form_success_message'),
        }),
        ('⚡ وضعیت', {
            'fields': ('is_active', 'order'),
        }),
    )

    def has_add_permission(self, request):
        if ContactSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(ContactMessage)
class ContactMessageAdmin(LandingAdminMixin, admin.ModelAdmin):
    """مدیریت پیام‌های تماس"""

    list_display = [
        'full_name', 'subject', 'phone', 'email',
        'message_preview', 'is_read', 'is_replied', 'created_at'
    ]
    list_filter = ['is_read', 'is_replied', 'created_at']
    list_editable = ['is_read', 'is_replied']
    search_fields = ['full_name', 'phone', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('📨 اطلاعات ارسال‌کننده', {
            'fields': ('full_name', 'phone', 'email'),
        }),
        ('📝 پیام', {
            'fields': ('subject', 'message'),
        }),
        ('🔧 مدیریت', {
            'fields': ('is_read', 'is_replied', 'admin_note'),
        }),
        ('📅 تاریخ', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    actions = ['mark_as_read', 'mark_as_unread', 'mark_as_replied']

    def message_preview(self, obj):
        return obj.message[:60] + '...' if len(obj.message) > 60 else obj.message
    message_preview.short_description = 'پیام'

    @admin.action(description='علامت‌گذاری به عنوان خوانده شده')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description='علامت‌گذاری به عنوان خوانده نشده')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)

    @admin.action(description='علامت‌گذاری به عنوان پاسخ داده شده')
    def mark_as_replied(self, request, queryset):
        queryset.update(is_replied=True)


@admin.register(DownloadSection)
class DownloadSectionAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'show_cafebazaar', 'show_myket', 'show_google_play', 'show_app_store', 'is_active']

    fieldsets = (
        ('📝 محتوا', {
            'fields': ('title', 'description', 'hint_text'),
        }),
        ('📱 کنترل نمایش استورها', {
            'fields': ('show_cafebazaar', 'show_myket', 'show_google_play', 'show_app_store'),
            'description': 'تیک بزنید تا هر استور نمایش داده شود',
        }),
        ('⚡ وضعیت', {
            'fields': ('is_active', 'order'),
        }),
    )

    def has_add_permission(self, request):
        if DownloadSection.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(TrustBadge)
class TrustBadgeAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'icon', 'badge_preview', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']

    def badge_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:6px;">',
                obj.image.url
            )
        return format_html(
            '<span style="font-size:24px;color:#A88B7D;">{}</span>',
            obj.icon
        )
    badge_preview.short_description = 'پیش‌نمایش'


@admin.register(NavItem)
class NavItemAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['label', 'anchor', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']


@admin.register(FooterLinkGroup)
class FooterLinkGroupAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'order', 'links_count']
    inlines = [FooterLinkInline]

    def links_count(self, obj):
        return obj.links.count()
    links_count.short_description = 'تعداد لینک‌ها'


@admin.register(FooterLink)
class FooterLinkAdmin(LandingAdminMixin, admin.ModelAdmin):
    list_display = ['label', 'group', 'url', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['group', 'is_active']