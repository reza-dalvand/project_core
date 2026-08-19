"""
Context Processors برای اپ landing
این داده‌ها در تمام تمپلیت‌های landing در دسترس هستند
"""
from .models import (
    SiteSettings, HeroSection,
    FeaturesSection, Feature,
    HowToSection, HowToStep,
    ServicesSection, ServiceCategory,
    AboutSection, AboutPoint,
    TeamSection, TeamMember,
    StatsSection, StatItem,
    FAQSection, FAQItem,
    ContactSection,
    DownloadSection,
    TrustBadge,
    NavItem,
    FooterLinkGroup,
)


def site_settings(request):
    """تنظیمات عمومی سایت - در تمام صفحات در دسترس"""
    settings = SiteSettings.objects.filter(is_active=True).first()

    if not settings:
        # مقادیر پیش‌فرض در صورت نبود رکورد
        return {
            'site': {
                'name': 'بیو کلاب',
                'slogan': 'رزرو آنلاین خدمات زیبایی و سلامت',
                'primary_color': '#A88B7D',
                'primary_dark_color': '#8D7468',
                'primary_light_color': '#C5AE9F',
                'background_color': '#F5F0EC',
                'phone': '۰۲۱-۹۱۰۰۱۲۳۴',
                'email': 'support@beau.app',
                'address': 'تهران، سعادت‌آباد',
                'working_hours': 'شنبه تا پنجشنبه ۹ تا ۱۸',
                'instagram_url': '#',
                'telegram_url': '#',
                'whatsapp_url': '#',
                'twitter_url': '#',
                'cafebazaar_url': '#',
                'myket_url': '#',
                'google_play_url': '',
                'app_store_url': '',
                'footer_text': 'تمامی حقوق محفوظ است',
                'copyright_year': '۱۴۰۵',
                'logo_icon': 'spa',
                'logo': None,
                'favicon': None,
                'meta_description': 'بیو کلاب - رزرو آنلاین خدمات زیبایی و سلامت',
                'meta_keywords': '',
                'enamad_image': None,
                'enamad_code': '',
            }
        }

    return {
        'site': {
            'name': settings.site_name,
            'slogan': settings.site_slogan,
            'primary_color': settings.primary_color,
            'primary_dark_color': settings.primary_dark_color,
            'primary_light_color': settings.primary_light_color,
            'background_color': settings.background_color,
            'phone': settings.phone,
            'email': settings.email,
            'address': settings.address,
            'working_hours': settings.working_hours,
            'instagram_url': settings.instagram_url,
            'telegram_url': settings.telegram_url,
            'whatsapp_url': settings.whatsapp_url,
            'twitter_url': settings.twitter_url,
            'cafebazaar_url': settings.cafebazaar_url,
            'myket_url': settings.myket_url,
            'google_play_url': settings.google_play_url,
            'app_store_url': settings.app_store_url,
            'footer_text': settings.footer_text,
            'copyright_year': settings.copyright_year,
            'logo_icon': settings.logo_icon,
            'logo': settings.logo,
            'favicon': settings.favicon,
            'meta_description': settings.meta_description,
            'meta_keywords': settings.meta_keywords,
            'enamad_image': settings.enamad_image,
            'enamad_code': settings.enamad_code,
        }
    }


def all_sections(request):
    """تمام بخش‌های سایت - برای صفحه اصلی"""
    # ─── ناوبری ───
    nav_items = NavItem.objects.filter(is_active=True).order_by('order')

    # ─── هیرو ───
    hero = HeroSection.objects.filter(is_active=True).first()

    # ─── ویژگی‌ها ───
    features_section = FeaturesSection.objects.filter(is_active=True).first()
    features = (
        Feature.objects.filter(is_active=True).order_by('order')
        if features_section else []
    )

    # ─── نحوه کار ───
    howto_section = HowToSection.objects.filter(is_active=True).first()
    howto_steps = (
        HowToStep.objects.filter(is_active=True).order_by('order', 'step_number')
        if howto_section else []
    )

    # ─── خدمات ───
    services_section = ServicesSection.objects.filter(is_active=True).first()
    service_categories = (
        ServiceCategory.objects.filter(is_active=True).order_by('order')
        if services_section else []
    )

    # ─── درباره ما ───
    about_section = AboutSection.objects.filter(is_active=True).first()
    about_points = (
        AboutPoint.objects.filter(is_active=True).order_by('order')
        if about_section else []
    )

    # ─── تیم ───
    team_section = TeamSection.objects.filter(is_active=True).first()
    team_members = (
        TeamMember.objects.filter(is_active=True).order_by('order')
        if team_section else []
    )

    # ─── آمار ───
    stats_section = StatsSection.objects.filter(is_active=True).first()
    stat_items = (
        StatItem.objects.filter(is_active=True).order_by('order')
        if stats_section else []
    )

    # ─── سوالات متداول ───
    faq_section = FAQSection.objects.filter(is_active=True).first()
    faq_items = (
        FAQItem.objects.filter(is_active=True).order_by('order')
        if faq_section else []
    )

    # ─── تماس ───
    contact_section = ContactSection.objects.filter(is_active=True).first()

    # ─── دانلود ───
    download_section = DownloadSection.objects.filter(is_active=True).first()

    # ─── نمادهای اعتماد ───
    trust_badges = TrustBadge.objects.filter(is_active=True).order_by('order')

    # ─── لینک‌های فوتر ───
    footer_groups = FooterLinkGroup.objects.prefetch_related('links').order_by('order')

    return {
        'nav_items': nav_items,
        'hero': hero,
        'features_section': features_section,
        'features': features,
        'howto_section': howto_section,
        'howto_steps': howto_steps,
        'services_section': services_section,
        'service_categories': service_categories,
        'about_section': about_section,
        'about_points': about_points,
        'team_section': team_section,
        'team_members': team_members,
        'stats_section': stats_section,
        'stat_items': stat_items,
        'faq_section': faq_section,
        'faq_items': faq_items,
        'contact_section': contact_section,
        'download_section': download_section,
        'trust_badges': trust_badges,
        'footer_groups': footer_groups,
    }