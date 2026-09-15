"""
ایجاد محتوای پیش‌فرض بخش‌های لندینگ (idempotent — اجرای مجدد امن)
اجرا: python manage.py create_landing_defaults
"""
from django.core.management.base import BaseCommand

from apps.landing.models import (
    HeroSection, FeaturesSection, Feature,
    HowToSection, HowToStep,
    ServicesSection, ServiceCategory,
    AboutSection, AboutPoint,
    TeamSection, TeamMember,
    StatsSection, StatItem,
    FAQSection, FAQItem,
    ContactSection, DownloadSection,
    NavItem, FooterLinkGroup, FooterLink, TrustBadge,
)

FEATURES = [
    ('search', 'جستجوی هوشمند', 'با فیلتر شهر، دسته‌بندی و فاصله، نزدیک‌ترین کسب‌وکار معتبر را پیدا کن.', '#A88B7D'),
    ('calendar_today', 'رزرو آنی نوبت', 'بدون تماس تلفنی؛ همان لحظه ساعت دلخواهت را رزرو کن و کد تایید بگیر.', '#8D7468'),
    ('verified_user', 'کسب‌وکارهای احراز شده', 'همه سالن‌ها و کلینیک‌ها پیش از فعال‌شدن احراز هویت می‌شوند.', '#C5AE9F'),
    ('account_balance_wallet', 'پرداخت امن بیعانه', 'بیعانه تا پایان خدمت نزد بیو کلاب می‌ماند؛ در صورت لغو خودکار مسترد می‌شود.', '#A88B7D'),
    ('star', 'نظرات واقعی', 'فقط مشتریانی که خدمت را انجام داده‌اند می‌توانند نظر ثبت کنند.', '#8D7468'),
    ('support_agent', 'پشتیبانی همیشه همراه', 'تیم پشتیبانی در تمام مراحل رزرو تا انجام خدمت کنار توست.', '#C5AE9F'),
]

HOWTO = [
    (1, 'search', 'کسب‌وکار را پیدا کن', 'بر اساس شهر، دسته‌بندی و فاصله، گزینه‌های معتبر را ببین و مقایسه کن.'),
    (2, 'touch_app', 'خدمت را انتخاب کن', 'قیمت شفاف، تخفیف و مدت خدمت را ببین و بهترین را انتخاب کن.'),
    (3, 'event_available', 'نوبت را رزرو کن', 'ساعت آزاد را انتخاب کن و با پرداخت بیعانه، نوبتت را قطعی کن.'),
    (4, 'star_rate', 'دریافت خدمت و امتیاز', 'پس از انجام خدمت و تایید با کد، نظر خود را ثبت کن.'),
]

SERVICES = [
    ('میکاپ', 'face', '۱۸۰+ کسب‌وکار'),
    ('ناخن', 'brush', '۲۴۰+ کسب‌وکار'),
    ('لیزر', 'flash_on', '۱۲۰+ کسب‌وکار'),
    ('پوست و فیشیال', 'spa', '۲۰۰+ کسب‌وکار'),
    ('مو', 'content_cut', '۱۵۰+ کسب‌وکار'),
    ('ابرو و مژه', 'visibility', '۹۰+ کسب‌وکار'),
]

ABOUT_POINTS = [
    ('verified_user', 'احراز هویت کامل', 'کسب‌وکارها با کد ملی و اطلاعات بانکی احراز می‌شوند تا خیالت راحت باشد.'),
    ('lock', 'پرداخت امن', 'بیعانه تا پایان خدمت در امانت می‌ماند و در صورت لغو خودکار باز می‌گردد.'),
    ('favorite', 'تجربه شخصی‌سازی‌شده', 'علاقه‌مندی‌ها، یادآوری تمدید و پیشنهادهای نزدیک تو.'),
]

TEAM = [
    ('مریم حسینی', 'بنیان‌گذار و مدیرعامل', '۱۰ سال تجربه در صنعت زیبایی و دیجیتال.', 'م.ح'),
    ('رضا محمدی', 'مدیر فنی', 'عاشق ساخت محصولاتی که زندگی روزمره را ساده‌تر می‌کنند.', 'ر.م'),
    ('سارا کریمی', 'مدیر تجربه کاربری', 'طراحی تجربه‌ای که کار با بیو کلاب را لذت‌بخش می‌کند.', 'س.ک'),
]

STATS = [
    (2500, '۲۵۰۰+', 'کسب‌وکار فعال', 'store'),
    (120000, '۱۲۰هزار+', 'کاربر فعال', 'people'),
    (350000, '۳۵۰هزار+', 'رزرو موفق', 'event_available'),
    (98, '۹۸٪', 'رضایت کاربران', 'thumb_up'),
]

FAQS = [
    ('رزرو نوبت چگونه انجام می‌شود؟', '<p>کسب‌وکار را انتخاب کن، ساعت آزاد را برگزین و با پرداخت بیعانه نوبتت را قطعی کن. کد تایید برایت پیامک می‌شود.</p>'),
    ('بیعانه چه زمانی باز می‌گردد؟', '<p>اگر کسب‌وکار نوبت را لغو کند، بیعانه به‌صورت خودکار و کامل به حساب تو باز می‌گردد.</p>'),
    ('آیا کسب‌وکارها معتبر هستند؟', '<p>بله؛ همه کسب‌وکارها پیش از فعال‌شدن احراز هویت می‌شوند و وضعیتشان در پروفایلشان نمایش داده می‌شود.</p>'),
    ('چگونه نظر ثبت کنم؟', '<p>پس از انجام خدمت و تایید با کد، می‌توانی برای همان نوبت نظر و امتیاز ثبت کنی.</p>'),
    ('اپلیکیشن را از کجا دانلود کنم؟', '<p>از بخش دانلود همین صفحه یا مارکت‌های کافه‌بازار و مایکت.</p>'),
]

NAV_ITEMS = [
    ('features', 'ویژگی‌ها'), ('howto', 'نحوه کار'), ('services', 'خدمات'),
    ('about', 'درباره ما'), ('team', 'تیم'), ('faq', 'سوالات متداول'),
    ('contact', 'تماس با ما'),
]

FOOTER_GROUPS = [
    ('دسترسی سریع', [('#', 'خانه'), ('#services', 'خدمات'), ('#download', 'دانلود اپلیکیشن')]),
    ('پشتیبانی', [('#faq', 'سوالات متداول'), ('#contact', 'تماس با ما')]),
]

TRUST_BADGES = [
    ('پرداخت امن', 'lock'),
    ('احراز هویت کاربران', 'verified_user'),
    ('تضمین کیفیت', 'workspace_premium'),
]


class Command(BaseCommand):
    help = 'ایجاد محتوای پیش‌فرض بخش‌های لندینگ (idempotent)'

    def _singleton(self, model):
        obj = model.objects.first()
        if obj is None:
            obj = model.objects.create()
        return obj

    def handle(self, *args, **options):
        features_section = self._singleton(FeaturesSection)
        howto_section = self._singleton(HowToSection)
        services_section = self._singleton(ServicesSection)
        about_section = self._singleton(AboutSection)
        team_section = self._singleton(TeamSection)
        stats_section = self._singleton(StatsSection)
        faq_section = self._singleton(FAQSection)
        self._singleton(HeroSection)
        self._singleton(ContactSection)
        self._singleton(DownloadSection)

        for i, (icon, title, desc, color) in enumerate(FEATURES):
            Feature.objects.get_or_create(
                section=features_section, title=title,
                defaults={'icon': icon, 'description': desc, 'color': color, 'order': i},
            )
        for n, icon, title, desc in HOWTO:
            HowToStep.objects.get_or_create(
                section=howto_section, step_number=n,
                defaults={'icon': icon, 'title': title, 'description': desc, 'order': n},
            )
        for i, (name, icon, count) in enumerate(SERVICES):
            ServiceCategory.objects.get_or_create(
                section=services_section, name=name,
                defaults={'icon': icon, 'count': count, 'order': i},
            )
        for i, (icon, title, desc) in enumerate(ABOUT_POINTS):
            AboutPoint.objects.get_or_create(
                section=about_section, title=title,
                defaults={'icon': icon, 'description': desc, 'order': i},
            )
        for i, (name, role, desc, initials) in enumerate(TEAM):
            TeamMember.objects.get_or_create(
                section=team_section, full_name=name,
                defaults={'role': role, 'description': desc, 'initials': initials, 'order': i},
            )
        for i, (value, display, label, icon) in enumerate(STATS):
            StatItem.objects.get_or_create(
                section=stats_section, label=label,
                defaults={'value': value, 'display_text': display, 'icon': icon, 'order': i},
            )
        for i, (question, answer) in enumerate(FAQS):
            FAQItem.objects.get_or_create(
                section=faq_section, question=question,
                defaults={'answer': answer, 'order': i},
            )
        for i, (anchor, label) in enumerate(NAV_ITEMS):
            NavItem.objects.get_or_create(anchor=anchor, defaults={'label': label, 'order': i})
        for gi, (title, links) in enumerate(FOOTER_GROUPS):
            group, _ = FooterLinkGroup.objects.get_or_create(title=title, defaults={'order': gi})
            for li, (url, label) in enumerate(links):
                FooterLink.objects.get_or_create(group=group, label=label, defaults={'url': url, 'order': li})
        for i, (name, icon) in enumerate(TRUST_BADGES):
            TrustBadge.objects.get_or_create(name=name, defaults={'icon': icon, 'order': i})

        self.stdout.write(self.style.SUCCESS('✅ محتوای پیش‌فرض لندینگ ایجاد/تکمیل شد.'))