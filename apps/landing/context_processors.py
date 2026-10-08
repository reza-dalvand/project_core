"""
Context Processor برای اپ landing
تمام داده‌های سایت معرفی را به همه template ها پاس می‌دهد

✅ بهینه‌سازی: داده‌ها از کش خوانده می‌شوند
"""
from .cache import get_landing_data


def landing_context(request):
    """
    پاس دادن تمام داده‌های لندینگ به context.
    ✅ داده‌ها از کش خوانده می‌شوند (نه هر بار از دیتابیس).
    """
    data = get_landing_data()

    return {
        'site_settings': data.get('site_settings'),
        'nav_items': data.get('nav_items', []),
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
        'download_section': data.get('download_section'),
        'contact_section': data.get('contact_section'),
        'trust_badges': data.get('trust_badges', []),
        'footer_groups': data.get('footer_groups', []),
    }