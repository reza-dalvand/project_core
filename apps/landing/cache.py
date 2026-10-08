"""
کش لندینگ — جلوگیری از کوئری‌های تکراری
✅ باگ‌های ۱۹ و ۲۰: کش‌سازی داده‌های لندینگ

استراتژی:
- تمام داده‌های لندینگ یک‌جا خوانده شده و در کش ذخیره می‌شوند
- هر ریکوئست فقط از کش می‌خواند (نه از دیتابیس)
- هنگام تغییر داده‌ها در داشبورد، کش اینویدیت می‌شود
"""
import logging

from django.core.cache import cache
from django.db.models import Exists, OuterRef, Prefetch

logger = logging.getLogger(__name__)

LANDING_CACHE_KEY = 'landing:all_data:v2'
LANDING_CACHE_TTL = 300  # ۵ دقیقه


def get_landing_data() -> dict:
    """
    دریافت تمام داده‌های لندینگ از کش یا دیتابیس.
    فقط یک‌بار از دیتابیس می‌خواند و کش می‌کند.
    """
    data = cache.get(LANDING_CACHE_KEY)
    if data is not None:
        return data

    # ─── خواندن از دیتابیس (فقط بار اول) ───
    from .models import (
        AboutPoint,
        AboutSection,
        ContactSection,
        DownloadSection,
        FAQCategory,
        FAQItem,
        FAQSection,
        Feature,
        FeaturesSection,
        FooterLink,
        FooterLinkGroup,
        HeroSection,
        HowToSection,
        HowToStep,
        NavItem,
        ServiceCategory,
        ServicesSection,
        SiteSettings,
        StatItem,
        StatsSection,
        TeamMember,
        TeamSection,
        TrustBadge,
    )

    data = {}

    # ─── تنظیمات سایت ───
    data['site_settings'] = (
        SiteSettings.objects.filter(is_active=True).first()
    )

    # ─── آیتم‌های ناوبری ───
    data['nav_items'] = list(
        NavItem.objects.filter(is_active=True).order_by('order')
    )

    # ─── هیرو ───
    data['hero'] = (
        HeroSection.objects.filter(is_active=True).first()
    )

    # ─── ویژگی‌ها ───
    data['features_section'] = (
        FeaturesSection.objects.filter(is_active=True).first()
    )
    data['features'] = list(
        Feature.objects.filter(is_active=True).order_by('order')
    )

    # ─── نحوه کار ───
    data['howto_section'] = (
        HowToSection.objects.filter(is_active=True).first()
    )
    data['howto_steps'] = list(
        HowToStep.objects.filter(is_active=True).order_by(
            'order', 'step_number'
        )
    )

    # ─── خدمات ───
    data['services_section'] = (
        ServicesSection.objects.filter(is_active=True).first()
    )
    data['service_categories'] = list(
        ServiceCategory.objects.filter(is_active=True).order_by('order')
    )

    # ─── درباره ما ───
    data['about_section'] = (
        AboutSection.objects.filter(is_active=True).first()
    )
    data['about_points'] = list(
        AboutPoint.objects.filter(is_active=True).order_by('order')
    )

    # ─── تیم ───
    data['team_section'] = (
        TeamSection.objects.filter(is_active=True).first()
    )
    data['team_members'] = list(
        TeamMember.objects.filter(is_active=True).order_by('order')
    )

    # ─── آمار ───
    data['stats_section'] = (
        StatsSection.objects.filter(is_active=True).first()
    )
    data['stats'] = list(
        StatItem.objects.filter(is_active=True).order_by('order')
    )

    # ─── سوالات متداول ───
    faq_section = FAQSection.objects.filter(is_active=True).first()
    data['faq_section'] = faq_section

    if faq_section:
        # ✅ فقط دسته‌هایی که حداقل یک سوال فعال دارند
        data['faq_categories'] = list(
            FAQCategory.objects.filter(
                section=faq_section,
                is_active=True,
            )
            .filter(
                Exists(
                    FAQItem.objects.filter(
                        category=OuterRef('pk'),
                        is_active=True,
                    )
                )
            )
            .prefetch_related(
                Prefetch(
                    'items',
                    queryset=FAQItem.objects.filter(
                        is_active=True
                    ).order_by('order'),
                )
            )
            .order_by('order')
        )
        data['faqs'] = list(
            FAQItem.objects.filter(
                section=faq_section,
                is_active=True,
            ).order_by('order')
        )
    else:
        data['faq_categories'] = []
        data['faqs'] = []

    # ─── دانلود ───
    data['download_section'] = (
        DownloadSection.objects.filter(is_active=True).first()
    )

    # ─── تماس با ما ───
    data['contact_section'] = (
        ContactSection.objects.filter(is_active=True).first()
    )

    # ─── نمادهای اعتماد ───
    data['trust_badges'] = list(
        TrustBadge.objects.filter(is_active=True).order_by('order')
    )

    # ─── لینک‌های فوتر (فقط لینک‌های فعال) ───
    data['footer_groups'] = list(
        FooterLinkGroup.objects.filter(is_active=True)
        .prefetch_related(
            Prefetch(
                'links',
                queryset=FooterLink.objects.filter(
                    is_active=True
                ).order_by('order'),
            )
        )
        .order_by('order')
    )

    # ─── ذخیره در کش ───
    cache.set(LANDING_CACHE_KEY, data, LANDING_CACHE_TTL)

    return data


def invalidate_landing_cache():
    """
    اینویدیت کش لندینگ.
    باید هنگام تغییر داده‌های لندینگ صدا زده شود.
    """
    cache.delete(LANDING_CACHE_KEY)
    logger.info('Landing cache invalidated')