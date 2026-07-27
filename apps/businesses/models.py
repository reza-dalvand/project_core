"""
مدل‌های کسب‌وکارها و خدمات
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from apps.core.storage import get_business_image_storage, get_user_avatar_storage


# بروزرسانی توابع مسیر تصاویر
def business_logo_path(instance, filename):
    """مسیر ذخیره لوگوی کسب‌وکار"""
    import os
    from django.utils.text import slugify
    ext = filename.split('.')[-1]
    business_slug = slugify(instance.name, allow_unicode=True)[:50]
    return f'businesses/{instance.id}/logo_{business_slug}.{ext}'


def business_cover_path(instance, filename):
    """مسیر ذخیره کاور کسب‌وکار"""
    import os
    from django.utils.text import slugify
    ext = filename.split('.')[-1]
    business_slug = slugify(instance.name, allow_unicode=True)[:50]
    return f'businesses/{instance.id}/cover_{business_slug}.{ext}'


def business_owner_photo_path(instance, filename):
    """مسیر ذخیره عکس صاحب کسب‌وکار"""
    import os
    ext = filename.split('.')[-1]
    return f'businesses/{instance.id}/owner_photo.{ext}'


def portfolio_image_path(instance, filename):
    """مسیر ذخیره تصاویر نمونه‌کار"""
    ext = filename.split('.')[-1]
    # استفاده از portfolio_id برای جلوگیری از خطای کوئری در زمان آپلود اولیه
    portfolio_id = instance.portfolio_id if instance.portfolio_id else 'temp'
    return f'businesses/portfolios/{portfolio_id}/{filename}'
# ═══════════════════════════════════════════════════════════
#                    دسته‌بندی‌ها
# ═══════════════════════════════════════════════════════════
class Category(models.Model):
    """دسته‌بندی اصلی خدمات"""

    name = models.CharField('نام دسته‌بندی', max_length=100, unique=True)
    slug = models.SlugField('اسلاگ', max_length=100, unique=True, blank=True)
    icon = models.CharField('آیکون', max_length=50, default='spa')
    color = models.CharField('رنگ', max_length=7, default='#A88B7D')
    description = models.TextField('توضیحات', blank=True, default='')
    order = models.PositiveIntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)

    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = '🏷️ دسته‌بندی'
        verbose_name_plural = '🏷️ دسته‌بندی‌ها'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class SubCategory(models.Model):
    """زیردسته‌بندی (نوع خدمت)"""

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name='دسته‌بندی اصلی',
    )
    name = models.CharField('نام زیردسته', max_length=100)
    slug = models.SlugField('اسلاگ', max_length=100, blank=True)
    order = models.PositiveIntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '📂 زیردسته'
        verbose_name_plural = '📂 زیردسته‌ها'
        ordering = ['order', 'name']
        unique_together = [('category', 'name')]

    def __str__(self):
        return f'{self.category.name} > {self.name}'


# ═══════════════════════════════════════════════════════════
#                    کسب‌وکارها
# ═══════════════════════════════════════════════════════════
class Province(models.Model):
    """استان"""
    name = models.CharField('نام استان', max_length=50, unique=True)
    slug = models.SlugField('اسلاگ', max_length=50, unique=True, blank=True)
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = '📍 استان'
        verbose_name_plural = '📍 استان‌ها'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class City(models.Model):
    """شهر"""
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name='cities',
        verbose_name='استان',
    )
    name = models.CharField('نام شهر', max_length=50)
    slug = models.SlugField('اسلاگ', max_length=50, blank=True)
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = '🏙️ شهر'
        verbose_name_plural = '🏙️ شهرها'
        ordering = ['order', 'name']
        unique_together = [('province', 'name')]

    def __str__(self):
        return f'{self.province.name} > {self.name}'


class Business(models.Model):
    """کسب‌وکار (سالن، کلینیک، مرکز لیزر و...)"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی'
        APPROVED = 'approved', 'تایید شده'
        REJECTED = 'rejected', 'رد شده'
        SUSPENDED = 'suspended', 'معلق'

    # ─── مالک ───
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='business',
        verbose_name='مالک',
    )

    # ─── اطلاعات پایه ───
    name = models.CharField('نام کسب‌وکار', max_length=150)
    slug = models.SlugField('اسلاگ', max_length=150, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='businesses',
        verbose_name='دسته‌بندی',
    )

    # ─── موقعیت مکانی ───
    province = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        related_name='businesses',
        verbose_name='استان',
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='businesses',
        verbose_name='شهر',
    )
    address = models.TextField('آدرس', max_length=500)
    latitude = models.DecimalField(
        'عرض جغرافیایی',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        'طول جغرافیایی',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    # ─── اطلاعات تماس ───
    phone = models.CharField('شماره تماس', max_length=20, blank=True, default='')

    # ─── تصاویر با Storage سفارشی ───
    logo = models.ImageField(
        'لوگو',
        upload_to=business_logo_path,
        storage=get_business_image_storage,
        blank=True,
        null=True,
    )
    cover = models.ImageField(
        'تصویر کاور',
        upload_to=business_cover_path,
        storage=get_business_image_storage,
        blank=True,
        null=True,
    )
    owner_photo = models.ImageField(
        'عکس مالک',
        upload_to=business_owner_photo_path,
        storage=get_business_image_storage,
        blank=True,
        null=True,
    )

    # ─── توضیحات ───
    about = models.TextField('درباره کسب‌وکار', blank=True, default='')
    working_hours_text = models.CharField(
        'ساعات کاری (متنی)',
        max_length=200,
        blank=True,
        default='',
        help_text='مثال: شنبه تا پنجشنبه ۱۰ الی ۲۰',
    )

    # ─── وضعیت ───
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    is_vip = models.BooleanField('VIP', default=False)
    is_featured = models.BooleanField('ویژه (نمایش در اسلایدر)', default=False)
    rejection_reason = models.TextField('دلیل رد', blank=True, default='')

    # ─── آمار (کش شده) ───
    rating_avg = models.DecimalField(
        'میانگین امتیاز',
        max_digits=3,
        decimal_places=2,
        default=0,
    )
    rating_count = models.PositiveIntegerField('تعداد نظرات', default=0)
    services_count = models.PositiveIntegerField('تعداد خدمات', default=0)
    bookings_count = models.PositiveIntegerField('تعداد رزروها', default=0)

    # ─── لینک رزرو ───
    booking_link = models.CharField(
        'لینک اختصاصی رزرو',
        max_length=100,
        blank=True,
        unique=True,
        null=True,
    )

    # ─── تاریخ‌ها ───
    approved_at = models.DateTimeField('تاریخ تایید', null=True, blank=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('تاریخ بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = '🏪 کسب‌وکار'
        verbose_name_plural = '🏪 کسب‌وکارها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['province', 'city']),
            models.Index(fields=['category']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Business.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug

        if not self.booking_link:
            import secrets
            self.booking_link = secrets.token_urlsafe(8)

        super().save(*args, **kwargs)

    def update_stats(self):
        """بروزرسانی آمار کش شده"""
        from apps.reviews.models import Review
        from django.db.models import Avg, Count

        reviews = Review.objects.filter(appointment__service__business=self)
        stats = reviews.aggregate(
            avg=Avg('rating'),
            count=Count('id'),
        )

        self.rating_avg = stats['avg'] or 0
        self.rating_count = stats['count'] or 0
        self.services_count = self.services.filter(is_active=True).count()
        self.save(update_fields=['rating_avg', 'rating_count', 'services_count'])


class SocialMedia(models.Model):
    """شبکه‌های اجتماعی کسب‌وکار"""

    class Platform(models.TextChoices):
        INSTAGRAM = 'instagram', 'اینستاگرام'
        TELEGRAM = 'telegram', 'تلگرام'
        WHATSAPP = 'whatsapp', 'واتساپ'
        BALE = 'bale', 'بله'
        EITAA = 'eitaa', 'ایتا'
        TWITTER = 'twitter', 'توییتر'

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='social_medias',
        verbose_name='کسب‌وکار',
    )
    platform = models.CharField(
        'پلتفرم',
        max_length=20,
        choices=Platform.choices,
    )
    username = models.CharField('نام کاربری / شماره', max_length=100)
    url = models.URLField('لینک', blank=True, default='')
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = '🌐 شبکه اجتماعی'
        verbose_name_plural = '🌐 شبکه‌های اجتماعی'
        unique_together = [('business', 'platform')]

    def __str__(self):
        return f'{self.business.name} - {self.get_platform_display()}'


# ═══════════════════════════════════════════════════════════
#                    خدمات
# ═══════════════════════════════════════════════════════════
class Service(models.Model):
    """خدمت ارائه شده توسط کسب‌وکار"""

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name='کسب‌وکار',
    )
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.PROTECT,
        related_name='services',
        verbose_name='زیردسته',
        null=True,
        blank=True,
    )

    name = models.CharField('نام خدمت', max_length=150)
    description = models.TextField('توضیحات', blank=True, default='', max_length=500)

    # ─── قیمت‌گذاری ───
    original_price = models.PositiveIntegerField(
        'قیمت اصلی (تومان)',
        validators=[MinValueValidator(0)],
    )
    discount_percent = models.PositiveIntegerField(
        'درصد تخفیف',
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # ─── بیعانه ───
    has_deposit = models.BooleanField('نیاز به بیعانه', default=True)
    deposit_amount = models.PositiveIntegerField(
        'مبلغ بیعانه (تومان)',
        default=0,
        validators=[MinValueValidator(0)],
    )

    # ─── مدت زمان ───
    duration_minutes = models.PositiveIntegerField(
        'مدت زمان (دقیقه)',
        default=60,
        validators=[MinValueValidator(15), MaxValueValidator(480)],
    )

    # ─── وضعیت ───
    is_active = models.BooleanField('فعال', default=True)

    # ─── یادآوری ───
    reminder_days = models.PositiveIntegerField(
        'یادآوری چند روز قبل',
        default=0,
        validators=[MaxValueValidator(30)],
        help_text='0 یعنی غیرفعال',
    )

    # ─── تاریخ‌ها ───
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('تاریخ بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = '💆 خدمت'
        verbose_name_plural = '💆 خدمات'
        ordering = ['name']
        indexes = [
            models.Index(fields=['business', 'is_active']),
        ]

    def __str__(self):
        return f'{self.business.name} - {self.name}'

    @property
    def final_price(self):
        """قیمت نهایی بعد از تخفیف"""
        discount_amount = int(self.original_price * self.discount_percent / 100)
        return max(0, self.original_price - discount_amount)

    def clean(self):
        if self.has_deposit and self.deposit_amount > self.final_price:
            raise ValidationError('مبلغ بیعانه نمی‌تواند بیشتر از قیمت نهایی باشد')


# ═══════════════════════════════════════════════════════════
#                    کارمندان
# ═══════════════════════════════════════════════════════════
class Employee(models.Model):
    """کارمند کسب‌وکار (اختیاری - مالک هم می‌تواند خدمت ارائه دهد)"""

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='employees',
        verbose_name='کسب‌وکار',
    )
    services = models.ManyToManyField(
        Service,
        related_name='employees',
        verbose_name='خدمات',
        blank=True,
    )

    name = models.CharField('نام', max_length=100)
    phone = models.CharField('شماره تماس', max_length=11, blank=True, default='')
    avatar = models.ImageField('عکس', upload_to='businesses/employees/', blank=True, null=True)
    role = models.CharField('نقش', max_length=50, blank=True, default='')
    experience = models.CharField('سابقه کار', max_length=50, blank=True, default='')
    bio = models.TextField('توضیحات', blank=True, default='')

    is_active = models.BooleanField('فعال', default=True)
    order = models.PositiveIntegerField('ترتیب', default=0)

    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = '👤 کارمند'
        verbose_name_plural = '👤 کارمندان'
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.business.name} - {self.name}'


# ═══════════════════════════════════════════════════════════
#                    نمونه‌کارها
# ═══════════════════════════════════════════════════════════
class Portfolio(models.Model):
    """نمونه‌کار کسب‌وکار"""

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='portfolios',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name='portfolios',
        verbose_name='خدمت مرتبط',
        null=True,
        blank=True,
    )

    title = models.CharField('عنوان', max_length=150)
    description = models.TextField('توضیحات', blank=True, default='', max_length=500)

    is_active = models.BooleanField('فعال', default=True)
    order = models.PositiveIntegerField('ترتیب', default=0)

    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = '🖼️ نمونه‌کار'
        verbose_name_plural = '🖼️ نمونه‌کارها'
        ordering = ['order', '-created_at']

    def __str__(self):
        return f'{self.business.name} - {self.title}'

    @property
    def cover_image(self):
        """اولین تصویر به عنوان کاور"""
        first_image = self.images.order_by('order').first()
        return first_image.image if first_image else None


class PortfolioImage(models.Model):
    """تصاویر نمونه‌کار (حداکثر ۵ تصویر)"""

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='نمونه‌کار',
    )
    image = models.ImageField('تصویر', upload_to=portfolio_image_path)
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = '📷 تصویر نمونه‌کار'
        verbose_name_plural = '📷 تصاویر نمونه‌کار'
        ordering = ['order']

    def __str__(self):
        return f'{self.portfolio.title} - تصویر {self.order}'

    def clean(self):
        # حداکثر ۵ تصویر
        if not self.pk and self.portfolio.images.count() >= 5:
            raise ValidationError('حداکثر ۵ تصویر برای هر نمونه‌کار مجاز است')


# ═══════════════════════════════════════════════════════════
#                    ساعات کاری
# ═══════════════════════════════════════════════════════════
class WorkingHours(models.Model):
    """ساعات کاری روزانه کسب‌وکار"""

    class WeekDay(models.IntegerChoices):
        SATURDAY = 0, 'شنبه'
        SUNDAY = 1, 'یکشنبه'
        MONDAY = 2, 'دوشنبه'
        TUESDAY = 3, 'سه‌شنبه'
        WEDNESDAY = 4, 'چهارشنبه'
        THURSDAY = 5, 'پنجشنبه'
        FRIDAY = 6, 'جمعه'

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='working_hours',
        verbose_name='کسب‌وکار',
    )
    weekday = models.PositiveSmallIntegerField(
        'روز هفته',
        choices=WeekDay.choices,
    )
    is_working = models.BooleanField('روز کاری', default=True)
    start_time = models.TimeField('ساعت شروع', null=True, blank=True)
    end_time = models.TimeField('ساعت پایان', null=True, blank=True)

    class Meta:
        verbose_name = '🕐 ساعات کاری'
        verbose_name_plural = '🕐 ساعات کاری'
        unique_together = [('business', 'weekday')]
        ordering = ['weekday']

    def __str__(self):
        day_name = self.get_weekday_display()
        return f'{self.business.name} - {day_name}'


class WorkingHoursBreak(models.Model):
    """بازه استراحت در ساعات کاری"""

    working_hours = models.ForeignKey(
        WorkingHours,
        on_delete=models.CASCADE,
        related_name='breaks',
        verbose_name='ساعات کاری',
    )
    start_time = models.TimeField('شروع استراحت')
    end_time = models.TimeField('پایان استراحت')

    class Meta:
        verbose_name = '☕ بازه استراحت'
        verbose_name_plural = '☕ بازه‌های استراحت'
        ordering = ['start_time']

    def __str__(self):
        return f'{self.working_hours} - استراحت {self.start_time} تا {self.end_time}'


# ═══════════════════════════════════════════════════════════
#                    آگهی اجاره لاین
# ═══════════════════════════════════════════════════════════
class LineRentalAd(models.Model):
    """آگهی اجاره لاین"""

    class CollabType(models.TextChoices):
        PERCENT = 'percent', 'درصدی'
        FIXED = 'fixed', 'اجاره ثابت'
        HOURLY = 'hourly', 'ساعتی'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'فعال'
        INACTIVE = 'inactive', 'غیرفعال'
        EXPIRED = 'expired', 'منقضی'

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='line_rental_ads',
        verbose_name='کسب‌وکار',
    )

    title = models.CharField('عنوان آگهی', max_length=150)
    description = models.TextField('توضیحات', max_length=500)

    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name='line_rental_ads',
        verbose_name='خدمت مرتبط',
        null=True,
        blank=True,
    )

    collab_type = models.CharField(
        'نوع همکاری',
        max_length=20,
        choices=CollabType.choices,
    )

    # ─── قیمت‌ها (بسته به نوع همکاری) ───
    percent_salon = models.PositiveIntegerField(
        'سهم سالن (%)',
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    percent_partner = models.PositiveIntegerField(
        'سهم همکار (%)',
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    fixed_amount = models.PositiveIntegerField(
        'مبلغ اجاره ماهانه',
        null=True,
        blank=True,
    )
    fixed_deposit = models.PositiveIntegerField(
        'رهن / ودیعه',
        null=True,
        blank=True,
        default=0,
    )
    hourly_rate = models.PositiveIntegerField(
        'نرخ ساعتی',
        null=True,
        blank=True,
    )

    # ─── تصویر ───
    image = models.ImageField('تصویر لاین', upload_to='businesses/line-rentals/')

    # ─── وضعیت ───
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # ─── تاریخ‌ها ───
    expires_at = models.DateTimeField('تاریخ انقضا')
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('تاریخ بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = '🏬 آگهی اجاره لاین'
        verbose_name_plural = '🏬 آگهی‌های اجاره لاین'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.business.name} - {self.title}'

    def clean(self):
        if self.collab_type == self.CollabType.PERCENT:
            if self.percent_salon and self.percent_partner:
                if self.percent_salon + self.percent_partner != 100:
                    raise ValidationError('مجموع درصدها باید ۱۰۰٪ باشد')

    @property
    def price_display(self):
        """متن نمایشی قیمت"""
        if self.collab_type == self.CollabType.PERCENT:
            return f'{self.percent_salon}-{self.percent_partner}٪'
        elif self.collab_type == self.CollabType.FIXED:
            if self.fixed_deposit:
                return f'{self.fixed_amount:,} + {self.fixed_deposit:,} رهن'
            return f'{self.fixed_amount:,} تومان'
        elif self.collab_type == self.CollabType.HOURLY:
            return f'{self.hourly_rate:,} / ساعت'
        return ''


# ═══════════════════════════════════════════════════════════
#                    درخواست مدل
# ═══════════════════════════════════════════════════════════
class ModelRequest(models.Model):
    """درخواست مدل برای نمونه‌کار"""

    class CostType(models.TextChoices):
        PAID = 'paid', 'با هزینه'
        MATERIAL_COST = 'material_cost', 'با هزینه مواد'
        FREE = 'free', 'رایگان'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'فعال'
        INACTIVE = 'inactive', 'غیرفعال'
        EXPIRED = 'expired', 'منقضی'

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='model_requests',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name='model_requests',
        verbose_name='خدمت',
        null=True,
        blank=True,
    )

    title = models.CharField('عنوان', max_length=150)
    description = models.TextField('توضیحات', max_length=500)
    image = models.ImageField('تصویر خدمت', upload_to='businesses/model-requests/')

    cost_type = models.CharField(
        'نوع هزینه',
        max_length=20,
        choices=CostType.choices,
        default=CostType.MATERIAL_COST,
    )

    discount_percent = models.PositiveIntegerField(
        'درصد تخفیف',
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    is_urgent = models.BooleanField('فوری', default=False)
    contact_phone = models.CharField('شماره تماس', max_length=11)

    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    expires_at = models.DateTimeField('تاریخ انقضا')
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('تاریخ بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = '👤 درخواست مدل'
        verbose_name_plural = '👤 درخواست‌های مدل'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.business.name} - {self.title}'