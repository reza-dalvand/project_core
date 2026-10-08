"""
Views برای اپ landing (سایت معرفی) — نسخه بهینه‌سازی شده
✅ باگ‌های ۱۹ و ۲۰: حذف کوئری‌های تکراری و استفاده از کش
"""
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .cache import get_landing_data
from .forms import ContactForm
from .models import ContactMessage, ContactSection


def index(request):
    """
    صفحه اصلی سایت معرفی — نسخه بهینه‌سازی شده

    ✅ تمام داده‌ها از کش خوانده می‌شوند (نه از دیتابیس).
    ✅ کوئری‌های تکراری با context_processor حذف شدند.
    """
    data = get_landing_data()

    site_settings = data.get('site_settings')

    context = {
        'page_title': (
            site_settings.site_name if site_settings else 'بیو کلاب'
        ),
        'site_settings': site_settings,
        'hero': data.get('hero'),
        'features_section': data.get('features_section'),
        'features': data.get('features', []),
        'howto_section': data.get('howto_section'),
        'howto_steps': data.get('howto_steps', []),
        'services_section': data.get('services_section'),
        'service_categories': data.get('service_categories', []),
        'about_section': data.get('about_section'),
        'about_points': data.get('about_points', []),
        'team_section': data.get('team_section'),
        'team_members': data.get('team_members', []),
        'stats_section': data.get('stats_section'),
        'stats': data.get('stats', []),
        'faq_section': data.get('faq_section'),
        'faq_categories': data.get('faq_categories', []),
        'faqs': data.get('faqs', []),
        'contact_section': data.get('contact_section'),
        'download_section': data.get('download_section'),
        'nav_items': data.get('nav_items', []),
        'footer_groups': data.get('footer_groups', []),
        'trust_badges': data.get('trust_badges', []),
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