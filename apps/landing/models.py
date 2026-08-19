

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
try:
    from django_ckeditor_5.fields import CKEditor5Field
except ImportError:
    from django.db import models
    class CKEditor5Field(models.TextField):
        def __init__(self, *args, **kwargs):
            kwargs.pop('config_name', None)
            super().__init__(*args, **kwargs)
        pass

# ═══════════════════════════════════════════════════════════════
#                    تنظیمات کلی سایت
# ═══════════════════════════════════════════════════════════════

class SiteSettings(models.Model):
    """تنظیمات عمومی سایت - فقط یک رکورد"""

    # ─── برندینگ ───
    site_name = models.CharField(
        'نام سایت',
        max_length=100,
        default='بیو کلاب',
    )
    site_slogan = models.CharField(
        'شعار سایت',
        max_length=200,
        default='رزرو آنلاین خدمات زیبایی و سلامت',
    )
    logo = models.ImageField(
        'لوگو',
        upload_to='branding/',
        blank=True,
        null=True,
    )
    logo_icon = models.CharField(
        'آیکون لوگو (Material Icon)',
        max_length=50,
        default='spa',
        help_text='نام آیکون از Material Icons گوگل',
    )
    favicon = models.ImageField(
        'فاویکون',
        upload_to='branding/',
        blank=True,
        null=True,
    )

    # ─── رنگ‌بندی ───
    primary_color = models.CharField(
        'رنگ اصلی',
        max_length=7,
        default='#A88B7D',
        help_text='رنگ اصلی سایت (فرمت HEX)',
    )
    primary_dark_color = models.CharField(
        'رنگ اصلی تیره',
        max_length=7,
        default='#8D7468',
    )
    primary_light_color = models.CharField(
        'رنگ اصلی روشن',
        max_length=7,
        default='#C5AE9F',
    )
    background_color = models.CharField(
        'رنگ پس‌زمینه',
        max_length=7,
        default='#F5F0EC',
    )

    # ─── سئو ───
    meta_description = models.TextField(
        'توضیحات متا',
        default='بیو کلاب - رزرو آنلاین خدمات زیبایی و سلامت. بهترین سالن‌های زیبایی، کلینیک‌های پوست و مراکز لیزر در یک اپلیکیشن',
        max_length=300,
    )
    meta_keywords = models.CharField(
        'کلمات کلیدی',
        max_length=500,
        default='رزرو آنلاین, سالن زیبایی, خدمات زیبایی, لیزر, پوست, ناخن, میکاپ',
    )

    # ─── اطلاعات تماس ───
    phone = models.CharField(
        'شماره تلفن',
        max_length=20,
        default='۰۲۱-۹۱۰۰۱۲۳۴',
    )
    email = models.EmailField(
        'ایمیل',
        default='support@beau.app',
    )
    address = models.CharField(
        'آدرس',
        max_length=300,
        default='تهران، سعادت‌آباد',
    )
    working_hours = models.CharField(
        'ساعات کاری',
        max_length=100,
        default='شنبه تا پنجشنبه ۹ تا ۱۸',
    )

    # ─── لینک‌های دانلود ───
    cafebazaar_url = models.URLField(
        'لینک کافه‌بازار',
        blank=True,
        default='#',
    )
    myket_url = models.URLField(
        'لینک مایکت',
        blank=True,
        default='#',
    )
    google_play_url = models.URLField(
        'لینک گوگل‌پلی',
        blank=True,
        default='#',
        help_text='خالی بگذارید تا نمایش داده نشود',
    )
    app_store_url = models.URLField(
        'لینک اپ‌استور',
        blank=True,
        default='#',
        help_text='خالی بگذارید تا نمایش داده نشود',
    )

    # ─── شبکه‌های اجتماعی ───
    instagram_url = models.URLField('اینستاگرام', blank=True, default='#')
    telegram_url = models.URLField('تلگرام', blank=True, default='#')
    whatsapp_url = models.URLField('واتساپ', blank=True, default='#')
    twitter_url = models.URLField('توییتر', blank=True, default='#')

    # ─── ای‌نماد ───
    enamad_image = models.ImageField(
        'تصویر ای‌نماد',
        upload_to='trust-badges/',
        blank=True,
        null=True,
    )
    enamad_code = models.TextField(
        'کد ای‌نماد (HTML)',
        blank=True,
        help_text='کد HTML ای‌نماد را اینجا پیست کنید',
    )

    # ─── فوتر ───
    footer_text = models.CharField(
        'متن فوتر',
        max_length=200,
        default='تمامی حقوق برای بیو کلاب محفوظ است. ساخته شده با ❤️ در ایران',
    )
    copyright_year = models.CharField(
        'سال کپی‌رایت',
        max_length=10,
        default='۱۴۰۵',
    )

    # ─── وضعیت ───
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '⚙️ تنظیمات سایت'
        verbose_name_plural = '⚙️ تنظیمات سایت'

    def __str__(self):
        return f'تنظیمات سایت: {self.site_name}'

    def save(self, *args, **kwargs):
        # فقط یک رکورد اجازه دارد
        if not self.pk and SiteSettings.objects.exists():
            existing = SiteSettings.objects.first()
            existing.delete()
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════
#                    بخش هیرو (بالای صفحه)
# ═══════════════════════════════════════════════════════════════

class HeroSection(models.Model):
    """بخش هیرو - بنر بالای صفحه"""

    badge_text = models.CharField(
        'متن بج',
        max_length=100,
        default='✨ نسل جدید رزرو خدمات زیبایی',
    )
    title = models.CharField(
        'عنوان اصلی',
        max_length=200,
        default='زیبایی و سلامت، فقط با یک لمس',
    )
    title_highlight = models.CharField(
        'بخش هایلایت عنوان',
        max_length=100,
        default='فقط با یک لمس',
        help_text='بخشی از عنوان که با رنگ گرادیانت نمایش داده می‌شود',
    )
    description = models.TextField(
        'توضیحات',
        default='با بیو کلاب، بهترین سالن‌های زیبایی، کلینیک‌های پوست و مو، و مراکز تخصصی شهر خود را پیدا کنید و در کم‌تر از ۳۰ ثانیه نوبت رزرو کنید.',
    )

    # ─── دکمه‌ها ───
    primary_btn_text = models.CharField(
        'متن دکمه اصلی',
        max_length=50,
        default='دانلود رایگان',
    )
    primary_btn_icon = models.CharField(
        'آیکون دکمه اصلی',
        max_length=50,
        default='download',
    )
    secondary_btn_text = models.CharField(
        'متن دکمه دوم',
        max_length=50,
        default='نحوه کار',
    )
    secondary_btn_icon = models.CharField(
        'آیکون دکمه دوم',
        max_length=50,
        default='play_circle',
    )

    # ─── آمار هیرو ───
    stat1_value = models.CharField('مقدار آمار ۱', max_length=20, default='۲۵۰۰+')
    stat1_label = models.CharField('برچسب آمار ۱', max_length=50, default='کسب‌وکار فعال')
    stat1_icon = models.CharField('آیکون آمار ۱', max_length=50, default='store')

    stat2_value = models.CharField('مقدار آمار ۲', max_length=20, default='۱۲۰هزار+')
    stat2_label = models.CharField('برچسب آمار ۲', max_length=50, default='کاربر فعال')
    stat2_icon = models.CharField('آیکون آمار ۲', max_length=50, default='people')

    stat3_value = models.CharField('مقدار آمار ۳', max_length=20, default='۴.۸')
    stat3_label = models.CharField('برچسب آمار ۳', max_length=50, default='امتیاز کاربران')
    stat3_icon = models.CharField('آیکون آمار ۳', max_length=50, default='star')

    # ─── تصویر ───
    hero_image = models.ImageField(
        'تصویر هیرو (ماکاپ موبایل)',
        upload_to='hero/',
        blank=True,
        null=True,
        help_text='اگر خالی باشد، ماکاپ موبایل پیش‌فرض نمایش داده می‌شود',
    )

    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '🎯 بخش هیرو'
        verbose_name_plural = '🎯 بخش هیرو'

    def __str__(self):
        return f'هیرو: {self.title}'

    def save(self, *args, **kwargs):
        if not self.pk and HeroSection.objects.exists():
            HeroSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════
#                    ویژگی‌ها
# ═══════════════════════════════════════════════════════════════

class FeaturesSection(models.Model):
    """تنظیمات بخش ویژگی‌ها"""

    badge_text = models.CharField('متن بج', max_length=100, default='چرا بیو کلاب؟')
    badge_icon = models.CharField('آیکون بج', max_length=50, default='auto_awesome')
    title = models.CharField('عنوان', max_length=200, default='ویژگی‌هایی که تجربه‌ات را متفاوت می‌کنند')
    subtitle = models.TextField(
        'توضیحات',
        default='بیو کلاب با ترکیب فناوری روز و درک عمیق از نیازهای کاربران، تجربه‌ای بی‌نظیر از رزرو خدمات زیبایی را برایت رقم می‌زند.',
    )

    is_active = models.BooleanField('نمایش بخش', default=True)
    order = models.IntegerField('ترتیب نمایش', default=2)

    class Meta:
        verbose_name = '⭐ تنظیمات بخش ویژگی‌ها'
        verbose_name_plural = '⭐ تنظیمات بخش ویژگی‌ها'

    def __str__(self):
        return f'بخش ویژگی‌ها: {self.title}'

    def save(self, *args, **kwargs):
        if not self.pk and FeaturesSection.objects.exists():
            FeaturesSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


class Feature(models.Model):
    """هر ویژگی"""
    section = models.ForeignKey(
        'FeaturesSection',
        on_delete=models.CASCADE,
        related_name='features',
        null=True, blank=True,
        verbose_name='بخش ویژگی‌ها'
    )
    title = models.CharField('عنوان', max_length=100)
    description = models.TextField('توضیحات')
    icon = models.CharField(
        'آیکون (Material Icon)',
        max_length=50,
        help_text='نام آیکون از Material Icons گوگل',
    )
    color = models.CharField('رنگ آیکون', max_length=7, default='#A88B7D')
    order = models.IntegerField('ترتیب نمایش', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '✨ ویژگی'
        verbose_name_plural = '✨ ویژگی‌ها'
        ordering = ['order']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.section_id:
            self.section = FeaturesSection.objects.first()
            if not self.section:
                self.section = FeaturesSection.objects.create()
        super().save(*args, **kwargs)

# ═══════════════════════════════════════════════════════════════
#                    نحوه کار
# ═══════════════════════════════════════════════════════════════

class HowToSection(models.Model):
    """تنظیمات بخش نحوه کار"""

    badge_text = models.CharField('متن بج', max_length=100, default='مسیر ساده')
    badge_icon = models.CharField('آیکون بج', max_length=50, default='route')
    title = models.CharField('عنوان', max_length=200, default='رزرو نوبت در ۴ قدم')
    subtitle = models.TextField(
        'توضیحات',
        default='فرآیند رزرو در بیو کلاب به گونه‌ای طراحی شده که ساده، سریع و لذت‌بخش باشد.',
    )

    is_active = models.BooleanField('نمایش بخش', default=True)
    order = models.IntegerField('ترتیب نمایش', default=3)

    class Meta:
        verbose_name = '🔄 تنظیمات بخش نحوه کار'
        verbose_name_plural = '🔄 تنظیمات بخش نحوه کار'

    def __str__(self):
        return f'بخش نحوه کار: {self.title}'

    def save(self, *args, **kwargs):
        if not self.pk and HowToSection.objects.exists():
            HowToSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


class HowToStep(models.Model):
    """هر مرحله از نحوه کار"""
    section = models.ForeignKey(
        'HowToSection',
        on_delete=models.CASCADE,
        related_name='steps',
        null=True, blank=True,
        verbose_name='بخش نحوه کار'
    )
    step_number = models.IntegerField(
        'شماره مرحله',
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    title = models.CharField('عنوان', max_length=100)
    description = models.TextField('توضیحات')
    icon = models.CharField('آیکون (Material Icon)', max_length=50)
    order = models.IntegerField('ترتیب نمایش', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '📋 مرحله نحوه کار'
        verbose_name_plural = '📋 مراحل نحوه کار'
        ordering = ['order', 'step_number']

    def __str__(self):
        return f'مرحله {self.step_number}: {self.title}'

    def save(self, *args, **kwargs):
        if not self.section_id:
            self.section = HowToSection.objects.first()
            if not self.section:
                self.section = HowToSection.objects.create()
        super().save(*args, **kwargs)

# ═══════════════════════════════════════════════════════════════
#                    خدمات
# ═══════════════════════════════════════════════════════════════

class ServicesSection(models.Model):
    """تنظیمات بخش خدمات"""

    badge_text = models.CharField('متن بج', max_length=100, default='تنوع بی‌نظیر')
    badge_icon = models.CharField('آیکون بج', max_length=50, default='category')
    title = models.CharField('عنوان', max_length=200, default='دسته‌بندی خدمات زیبایی و سلامت')
    subtitle = models.TextField(
        'توضیحات',
        default='از میکاپ و ناخن گرفته تا لیزر و فیشیال - هر خدمتی که نیاز داری، در بیو کلاب پیدا می‌کنی.',
    )

    is_active = models.BooleanField('نمایش بخش', default=True)
    order = models.IntegerField('ترتیب نمایش', default=4)

    class Meta:
        verbose_name = '💅 تنظیمات بخش خدمات'
        verbose_name_plural = '💅 تنظیمات بخش خدمات'

    def __str__(self):
        return f'بخش خدمات: {self.title}'

    def save(self, *args, **kwargs):
        if not self.pk and ServicesSection.objects.exists():
            ServicesSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


class ServiceCategory(models.Model):
    """دسته‌بندی خدمت"""
    section = models.ForeignKey(
        'ServicesSection',
        on_delete=models.CASCADE,
        related_name='categories',
        null=True, blank=True,
        verbose_name='بخش خدمات'
    )
    name = models.CharField('نام خدمت', max_length=100)
    count = models.CharField('تعداد کسب‌وکار', max_length=20, default='۱۸۰+ کسب‌وکار')
    icon = models.CharField('آیکون (Material Icon)', max_length=50)
    order = models.IntegerField('ترتیب نمایش', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '🏷️ دسته‌بندی خدمت'
        verbose_name_plural = '🏷️ دسته‌بندی‌های خدمات'
        ordering = ['order']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.section_id:
            self.section = ServicesSection.objects.first()
            if not self.section:
                self.section = ServicesSection.objects.create()
        super().save(*args, **kwargs)

# ═══════════════════════════════════════════════════════════════
#                    درباره ما
# ═══════════════════════════════════════════════════════════════

class AboutSection(models.Model):
    """بخش درباره ما"""

    badge_text = models.CharField('متن بج', max_length=100, default='درباره ما')
    title = models.CharField(
        'عنوان',
        max_length=200,
        default='ما اینجاییم تا زیبایی رو برای همه ساده‌تر کنیم',
    )
    description = models.TextField(
        'توضیحات اصلی',
        default='بیو کلاب یک پلتفرم هوشمند رزرو آنلاین خدمات زیبایی و سلامته که سالن‌ها، کلینیک‌ها و متخصصان رو به کاربران متصل می‌کنه.',
    )

    # ─── کارت بصری ───
    card_title = models.CharField(
        'عنوان کارت',
        max_length=100,
        default='داستان بیو کلاب',
    )
    card_description = models.TextField(
        'توضیحات کارت',
        default='از سال ۱۴۰۱ با هدف ساده‌سازی تجربه رزرو خدمات زیبایی در ایران آغاز کردیم.',
    )

    # ─── آمار کارت ───
    card_stat1_value = models.CharField('مقدار آمار ۱', max_length=20, default='۳+')
    card_stat1_label = models.CharField('برچسب آمار ۱', max_length=50, default='سال تجربه')

    card_stat2_value = models.CharField('مقدار آمار ۲', max_length=20, default='۲۴')
    card_stat2_label = models.CharField('برچسب آمار ۲', max_length=50, default='شهر فعال')

    card_stat3_value = models.CharField('مقدار آمار ۳', max_length=20, default='۹۸٪')
    card_stat3_label = models.CharField('برچسب آمار ۳', max_length=50, default='رضایت کاربر')

    is_active = models.BooleanField('نمایش بخش', default=True)
    order = models.IntegerField('ترتیب نمایش', default=5)

    class Meta:
        verbose_name = '📖 بخش درباره ما'
        verbose_name_plural = '📖 بخش درباره ما'

    def __str__(self):
        return f'درباره ما: {self.title}'

    def save(self, *args, **kwargs):
        if not self.pk and AboutSection.objects.exists():
            AboutSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


class AboutPoint(models.Model):
    """نکات بخش درباره ما"""
    section = models.ForeignKey(
        'AboutSection',
        on_delete=models.CASCADE,
        related_name='points',
        null=True, blank=True,
        verbose_name='بخش درباره ما'
    )
    title = models.CharField('عنوان', max_length=100)
    description = models.TextField('توضیحات')
    icon = models.CharField('آیکون (Material Icon)', max_length=50)
    order = models.IntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '📌 نکته درباره ما'
        verbose_name_plural = '📌 نکات درباره ما'
        ordering = ['order']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.section_id:
            self.section = AboutSection.objects.first()
            if not self.section:
                self.section = AboutSection.objects.create()
        super().save(*args, **kwargs)
# ═══════════════════════════════════════════════════════════════
#                    تیم
# ═══════════════════════════════════════════════════════════════

class TeamSection(models.Model):
    """تنظیمات بخش تیم"""

    badge_text = models.CharField('متن بج', max_length=100, default='تیم ما')
    badge_icon = models.CharField('آیکون بج', max_length=50, default='groups')
    title = models.CharField('عنوان', max_length=200, default='افراد پشت بیو کلاب')
    subtitle = models.TextField(
        'توضیحات',
        default='تیمی متعهد و متخصص که با عشق به زیبایی و فناوری، بیو کلاب را برای شما می‌سازند.',
    )

    is_active = models.BooleanField('نمایش بخش', default=True)
    order = models.IntegerField('ترتیب نمایش', default=6)

    class Meta:
        verbose_name = '👥 تنظیمات بخش تیم'
        verbose_name_plural = '👥 تنظیمات بخش تیم'

    def __str__(self):
        return f'بخش تیم: {self.title}'

    def save(self, *args, **kwargs):
        if not self.pk and TeamSection.objects.exists():
            TeamSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


class TeamMember(models.Model):
    """عضو تیم"""
    section = models.ForeignKey(
        'TeamSection',
        on_delete=models.CASCADE,
        related_name='members',
        null=True, blank=True,
        verbose_name='بخش تیم'
    )
    full_name = models.CharField('نام و نام خانوادگی', max_length=100)
    role = models.CharField('سمت', max_length=100)
    description = models.TextField('توضیحات', blank=True)
    avatar = models.ImageField('عکس پروفایل', upload_to='team/', blank=True, null=True)
    initials = models.CharField('حروف اختصاری', max_length=5, blank=True)
    email = models.EmailField('ایمیل', blank=True)
    linkedin_url = models.URLField('لینکدین', blank=True)
    twitter_url = models.URLField('توییتر', blank=True)
    order = models.IntegerField('ترتیب نمایش', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '👤 عضو تیم'
        verbose_name_plural = '👤 اعضای تیم'
        ordering = ['order']

    def __str__(self):
        return f'{self.full_name} - {self.role}'

    def get_initials(self):
        if self.initials:
            return self.initials
        parts = self.full_name.split()
        if len(parts) >= 2:
            return f'{parts[0][0]}.{parts[1][0]}'
        return self.full_name[:2] if self.full_name else '؟'

    def save(self, *args, **kwargs):
        if not self.section_id:
            self.section = TeamSection.objects.first()
            if not self.section:
                self.section = TeamSection.objects.create()
        super().save(*args, **kwargs)

# ═══════════════════════════════════════════════════════════════
#                    آمار و ارقام
# ═══════════════════════════════════════════════════════════════

class StatsSection(models.Model):
    """تنظیمات بخش آمار"""

    is_active = models.BooleanField('نمایش بخش', default=True)
    order = models.IntegerField('ترتیب نمایش', default=7)

    class Meta:
        verbose_name = '📊 تنظیمات بخش آمار'
        verbose_name_plural = '📊 تنظیمات بخش آمار'

    def __str__(self):
        return 'بخش آمار و ارقام'

    def save(self, *args, **kwargs):
        if not self.pk and StatsSection.objects.exists():
            StatsSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


class StatItem(models.Model):
    """آیتم آماری"""
    section = models.ForeignKey(
        'StatsSection',
        on_delete=models.CASCADE,
        related_name='stats',
        null=True, blank=True,
        verbose_name='بخش آمار'
    )
    value = models.IntegerField('مقدار عددی')
    display_text = models.CharField('متن نمایشی', max_length=50)
    label = models.CharField('برچسب', max_length=100)
    icon = models.CharField('آیکون (Material Icon)', max_length=50)
    order = models.IntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '📈 آیتم آماری'
        verbose_name_plural = '📈 آیتم‌های آماری'
        ordering = ['order']

    def __str__(self):
        return f'{self.display_text} - {self.label}'

    def save(self, *args, **kwargs):
        if not self.section_id:
            self.section = StatsSection.objects.first()
            if not self.section:
                self.section = StatsSection.objects.create()
        super().save(*args, **kwargs)

# ═══════════════════════════════════════════════════════════════
#                    سوالات متداول
# ═══════════════════════════════════════════════════════════════

class FAQSection(models.Model):
    """تنظیمات بخش سوالات متداول"""

    badge_text = models.CharField('متن بج', max_length=100, default='سوالات متداول')
    badge_icon = models.CharField('آیکون بج', max_length=50, default='help')
    title = models.CharField('عنوان', max_length=200, default='پاسخ سوالات شما')
    subtitle = models.TextField(
        'توضیحات',
        default='پاسخ رایج‌ترین پرسش‌های کاربران بیو کلاب را اینجا بخوانید.',
    )

    is_active = models.BooleanField('نمایش بخش', default=True)
    order = models.IntegerField('ترتیب نمایش', default=8)

    class Meta:
        verbose_name = '❓ تنظیمات بخش سوالات'
        verbose_name_plural = '❓ تنظیمات بخش سوالات'

    def __str__(self):
        return f'بخش سوالات: {self.title}'

    def save(self, *args, **kwargs):
        if not self.pk and FAQSection.objects.exists():
            FAQSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


class FAQItem(models.Model):
    """سوال متداول"""
    section = models.ForeignKey(
        'FAQSection',
        on_delete=models.CASCADE,
        related_name='faqs',
        null=True, blank=True,
        verbose_name='بخش سوالات'
    )
    question = models.CharField('سوال', max_length=300)
    answer = CKEditor5Field('پاسخ', config_name='default')
    order = models.IntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '💬 سوال متداول'
        verbose_name_plural = '💬 سوالات متداول'
        ordering = ['order']

    def __str__(self):
        return self.question

    def save(self, *args, **kwargs):
        if not self.section_id:
            self.section = FAQSection.objects.first()
            if not self.section:
                self.section = FAQSection.objects.create()
        super().save(*args, **kwargs)

# ═══════════════════════════════════════════════════════════════
#                    تماس با ما
# ═══════════════════════════════════════════════════════════════

class ContactSection(models.Model):
    """تنظیمات بخش تماس"""

    badge_text = models.CharField('متن بج', max_length=100, default='ارتباط با ما')
    badge_icon = models.CharField('آیکون بج', max_length=50, default='headset_mic')
    title = models.CharField('عنوان', max_length=200, default='با ما در تماس باشید')
    subtitle = models.TextField(
        'توضیحات',
        default='تیم پشتیبانی بیو کلاب آماده پاسخگویی به سوالات و حل مشکلات شماست.',
    )

    # ─── کارت اطلاعات ───
    card_title = models.CharField('عنوان کارت', max_length=100, default='راه‌های ارتباطی')
    card_description = models.TextField(
        'توضیحات کارت',
        default='از هر طریقی که راحت‌ترید با ما در ارتباط باشید.',
    )

    # ─── فرم تماس ───
    form_title = models.CharField('عنوان فرم', max_length=100, default='ارسال پیام')
    form_description = models.TextField(
        'توضیحات فرم',
        default='پیام خود را بنویسید، در اسرع وقت پاسخ می‌دهیم.',
    )
    form_success_message = models.TextField(
        'پیام موفقیت',
        default='پیام شما با موفقیت ارسال شد. به زودی با شما تماس خواهیم گرفت.',
    )

    is_active = models.BooleanField('نمایش بخش', default=True)
    order = models.IntegerField('ترتیب نمایش', default=9)

    class Meta:
        verbose_name = '📞 تنظیمات بخش تماس'
        verbose_name_plural = '📞 تنظیمات بخش تماس'

    def __str__(self):
        return f'بخش تماس: {self.title}'

    def save(self, *args, **kwargs):
        if not self.pk and ContactSection.objects.exists():
            ContactSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


class ContactMessage(models.Model):
    """پیام‌های دریافتی از فرم تماس"""

    full_name = models.CharField('نام و نام خانوادگی', max_length=100)
    phone = models.CharField('شماره تماس', max_length=20)
    email = models.EmailField('ایمیل', blank=True)
    subject = models.CharField('موضوع', max_length=200)
    message = models.TextField('پیام')

    is_read = models.BooleanField('خوانده شده', default=False)
    is_replied = models.BooleanField('پاسخ داده شده', default=False)
    admin_note = models.TextField('یادداشت ادمین', blank=True)

    created_at = models.DateTimeField('تاریخ ارسال', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = '📨 پیام تماس'
        verbose_name_plural = '📨 پیام‌های تماس'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} - {self.subject}'


# ═══════════════════════════════════════════════════════════════
#                    بخش دانلود
# ═══════════════════════════════════════════════════════════════

class DownloadSection(models.Model):
    """تنظیمات بخش دانلود"""

    title = models.CharField('عنوان', max_length=200, default='همین حالا بیو کلاب را نصب کنید')
    description = models.TextField(
        'توضیحات',
        default='اپلیکیشن بیو کلاب را از مارکت‌های معتبر دانلود کنید و به جمع هزاران کاربر راضی بپیوندید.',
    )
    hint_text = models.CharField(
        'متن راهنما',
        max_length=100,
        default='✨ رایگان • بدون تبلیغات • همیشه به‌روز',
    )

    # ─── کنترل نمایش استورها ───
    show_cafebazaar = models.BooleanField('نمایش کافه‌بازار', default=True)
    show_myket = models.BooleanField('نمایش مایکت', default=True)
    show_google_play = models.BooleanField('نمایش گوگل‌پلی', default=False)
    show_app_store = models.BooleanField('نمایش اپ‌استور', default=False)

    is_active = models.BooleanField('نمایش بخش', default=True)
    order = models.IntegerField('ترتیب نمایش', default=10)

    class Meta:
        verbose_name = '📱 تنظیمات بخش دانلود'
        verbose_name_plural = '📱 تنظیمات بخش دانلود'

    def __str__(self):
        return f'بخش دانلود: {self.title}'

    def save(self, *args, **kwargs):
        if not self.pk and DownloadSection.objects.exists():
            DownloadSection.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════
#                    نمادهای اعتماد
# ═══════════════════════════════════════════════════════════════

class TrustBadge(models.Model):
    """نماد اعتماد"""

    name = models.CharField('نام نماد', max_length=100)
    icon = models.CharField(
        'آیکون (Material Icon)',
        max_length=50,
        default='verified',
    )
    image = models.ImageField(
        'تصویر نماد',
        upload_to='trust-badges/',
        blank=True,
        null=True,
    )
    link_url = models.URLField('لینک', blank=True)
    code = models.TextField(
        'کد HTML',
        blank=True,
        help_text='اگر نماد کد HTML خاصی دارد اینجا قرار دهید',
    )
    order = models.IntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '🛡️ نماد اعتماد'
        verbose_name_plural = '🛡️ نمادهای اعتماد'
        ordering = ['order']

    def __str__(self):
        return self.name


# ═══════════════════════════════════════════════════════════════
#                    آیتم‌های ناوبری (Navbar)
# ═══════════════════════════════════════════════════════════════

class NavItem(models.Model):
    """آیتم ناوبری"""

    label = models.CharField('عنوان', max_length=50)
    anchor = models.CharField(
        'لنگر (Anchor)',
        max_length=50,
        help_text='شناسه بخش مقصد (مثلاً: features)',
    )
    order = models.IntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '🔗 آیتم ناوبری'
        verbose_name_plural = '🔗 آیتم‌های ناوبری'
        ordering = ['order']

    def __str__(self):
        return self.label


# ═══════════════════════════════════════════════════════════════
#                    لینک‌های فوتر
# ═══════════════════════════════════════════════════════════════

class FooterLinkGroup(models.Model):
    """گروه لینک‌های فوتر"""

    title = models.CharField('عنوان گروه', max_length=50)
    order = models.IntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = '🔗 گروه لینک فوتر'
        verbose_name_plural = '🔗 گروه‌های لینک فوتر'
        ordering = ['order']

    def __str__(self):
        return self.title


class FooterLink(models.Model):
    """لینک فوتر"""

    group = models.ForeignKey(
        FooterLinkGroup,
        on_delete=models.CASCADE,
        related_name='links',
        verbose_name='گروه',
    )
    label = models.CharField('عنوان لینک', max_length=50)
    url = models.CharField(
        'آدرس',
        max_length=200,
        help_text='لینک یا #anchor',
    )
    order = models.IntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '🔗 لینک فوتر'
        verbose_name_plural = '🔗 لینک‌های فوتر'
        ordering = ['order']

    def __str__(self):
        return f'{self.group.title} > {self.label}'