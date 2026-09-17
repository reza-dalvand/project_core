# apps/landing/context_processors.py
"""
Context Processor برای اپ landing
تمام داده‌های سایت معرفی را به همه template ها پاس می‌دهد
"""
from .models import (
    SiteSettings, NavItem,
    HeroSection,
    FeaturesSection, Feature,
    HowToSection, HowToStep,
    ServicesSection, ServiceCategory,
    AboutSection, AboutPoint,
    TeamSection, TeamMember,
    StatsSection, StatItem,
    FAQSection, FAQItem,
    DownloadSection,
    ContactSection,
    TrustBadge,
    FooterLinkGroup,
)


def landing_context(request):
    """
    پاس دادن تمام داده‌های لندینگ به context
    """
    ctx = {}

    # ─── تنظیمات کلی سایت ───
    ctx['site_settings'] = SiteSettings.objects.filter(is_active=True).first()

    # ─── آیتم‌های ناوبری (نوبار) ───
    ctx['nav_items'] = NavItem.objects.filter(is_active=True).order_by('order')

    # ─── هیرو ───
    ctx['hero'] = HeroSection.objects.filter(is_active=True).first()

    # ─── امکانات ───
    features_section = FeaturesSection.objects.filter(is_active=True).first()
    ctx['features_section'] = features_section
    if features_section:
        ctx['features'] = features_section.features.filter(is_active=True).order_by('order')
    else:
        ctx['features'] = Feature.objects.none()

    # ─── مراحل رزرو ───
    howto_section = HowToSection.objects.filter(is_active=True).first()
    ctx['howto_section'] = howto_section
    if howto_section:
        ctx['howto_steps'] = howto_section.steps.filter(is_active=True).order_by('order', 'step_number')
    else:
        ctx['howto_steps'] = HowToStep.objects.none()

    # ─── خدمات ───
    services_section = ServicesSection.objects.filter(is_active=True).first()
    ctx['services_section'] = services_section
    if services_section:
        ctx['service_categories'] = services_section.categories.filter(is_active=True).order_by('order')
    else:
        ctx['service_categories'] = ServiceCategory.objects.none()

    # ─── درباره ما ───
    about_section = AboutSection.objects.filter(is_active=True).first()
    ctx['about_section'] = about_section
    if about_section:
        ctx['about_points'] = about_section.points.filter(is_active=True).order_by('order')
    else:
        ctx['about_points'] = AboutPoint.objects.none()

    # ─── تیم ───
    team_section = TeamSection.objects.filter(is_active=True).first()
    ctx['team_section'] = team_section
    if team_section:
        ctx['team_members'] = team_section.members.filter(is_active=True).order_by('order')
    else:
        ctx['team_members'] = TeamMember.objects.none()

    # ─── آمار ───
    stats_section = StatsSection.objects.filter(is_active=True).first()
    ctx['stats_section'] = stats_section
    if stats_section:
        ctx['stats'] = stats_section.stats.filter(is_active=True).order_by('order')
    else:
        ctx['stats'] = StatItem.objects.none()

    # ─── سؤالات متداول ───
    faq_section = FAQSection.objects.filter(is_active=True).first()
    ctx['faq_section'] = faq_section
    if faq_section:
        ctx['faqs'] = faq_section.faqs.filter(is_active=True).order_by('order')
    else:
        ctx['faqs'] = FAQItem.objects.none()

    # ─── دانلود ───
    ctx['download_section'] = DownloadSection.objects.filter(is_active=True).first()

    # ─── تماس با ما ───
    ctx['contact_section'] = ContactSection.objects.filter(is_active=True).first()

    # ─── نمادهای اعتماد ───
    ctx['trust_badges'] = TrustBadge.objects.filter(is_active=True).order_by('order')

    # ─── لینک‌های فوتر ───
    ctx['footer_groups'] = FooterLinkGroup.objects.prefetch_related(
        'links'
    ).filter(
        is_active=True
    ).order_by('order')

    return ctx