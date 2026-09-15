"""
Views برای اپ landing (سایت معرفی) — نسخه جدید مینیمال
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import (
    SiteSettings, HeroSection, FeaturesSection, Feature,
    HowToSection, HowToStep, ServicesSection, ServiceCategory,
    AboutSection, AboutPoint, TeamSection, TeamMember,
    StatsSection, StatItem, FAQSection, FAQItem,
    ContactSection, ContactMessage, DownloadSection,
    TrustBadge, NavItem, FooterLinkGroup, FooterLink
)
from .forms import ContactForm


def index(request):
    """صفحه اصلی سایت معرفی — نسخه مینیمال جدید"""
    
    # ─── تنظیمات کلی سایت ───
    site_settings = SiteSettings.objects.filter(is_active=True).first()
    
    # ─── بخش هیرو ───
    hero = HeroSection.objects.filter(is_active=True).first()
    
    # ─── بخش امکانات ───
    features_section = FeaturesSection.objects.filter(is_active=True).first()
    features = Feature.objects.filter(is_active=True).order_by('order') if features_section else []
    
    # ─── بخش نحوه کار (مراحل رزرو) ───
    howto_section = HowToSection.objects.filter(is_active=True).first()
    howto_steps = HowToStep.objects.filter(is_active=True).order_by('order', 'step_number') if howto_section else []
    
    # ─── بخش خدمات ───
    services_section = ServicesSection.objects.filter(is_active=True).first()
    service_categories = ServiceCategory.objects.filter(is_active=True).order_by('order') if services_section else []
    
    # ─── بخش درباره ما ───
    about_section = AboutSection.objects.filter(is_active=True).first()
    about_points = AboutPoint.objects.filter(is_active=True).order_by('order') if about_section else []
    
    # ─── بخش تیم ───
    team_section = TeamSection.objects.filter(is_active=True).first()
    team_members = TeamMember.objects.filter(is_active=True).order_by('order') if team_section else []
    
    # ─── بخش آمار ───
    stats_section = StatsSection.objects.filter(is_active=True).first()
    stats = StatItem.objects.filter(is_active=True).order_by('order') if stats_section else []
    
    # ─── بخش سوالات متداول ───
    faq_section = FAQSection.objects.filter(is_active=True).first()
    faqs = FAQItem.objects.filter(is_active=True).order_by('order') if faq_section else []
    
    # ─── بخش تماس ───
    contact_section = ContactSection.objects.filter(is_active=True).first()
    
    # ─── بخش دانلود ───
    download_section = DownloadSection.objects.filter(is_active=True).first()
    
    # ─── آیتم‌های ناوبری (Navbar) ───
    nav_items = NavItem.objects.filter(is_active=True).order_by('order')
    
    # ─── لینک‌های فوتر ───
    footer_groups = FooterLinkGroup.objects.prefetch_related('links').filter(is_active=True).order_by('order')
    
    # ─── نمادهای اعتماد ───
    trust_badges = TrustBadge.objects.filter(is_active=True).order_by('order')
    
    context = {
        'page_title': site_settings.site_name if site_settings else 'بیو کلاب',
        'site_settings': site_settings,
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
        'stats': stats,
        'faq_section': faq_section,
        'faqs': faqs,
        'contact_section': contact_section,
        'download_section': download_section,
        'nav_items': nav_items,
        'footer_groups': footer_groups,
        'trust_badges': trust_badges,
    }
    return render(request, 'landing/index.html', context)


@require_POST
def submit_contact(request):
    """پردازش فرم تماس - به صورت AJAX"""
    form = ContactForm(request.POST)
    if form.is_valid():
        ContactMessage.objects.create(
            full_name=form.cleaned_data['full_name'],
            phone=form.cleaned_data['phone'],
            email=form.cleaned_data.get('email', ''),
            subject=form.cleaned_data['subject'],
            message=form.cleaned_data['message'],
        )
        contact_settings = ContactSection.objects.first()
        success_msg = 'پیام شما با موفقیت ارسال شد.'
        if contact_settings:
            success_msg = contact_settings.form_success_message

        return JsonResponse({
            'success': True,
            'message': success_msg,
        })

    return JsonResponse({
        'success': False,
        'message': 'لطفاً تمام فیلدهای الزامی را پر کنید.',
        'errors': form.errors,
    }, status=400)