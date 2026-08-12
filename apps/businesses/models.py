"""
کسب‌وکارها — با PostGIS
"""
import secrets
from django.db import models, transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from apps.core.models import BaseModel


class Business(BaseModel):
    """کسب‌وکار"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی'
        APPROVED = 'approved', 'تایید شده'
        REJECTED = 'rejected', 'رد شده'

    # ═══════════ مالک ═══════════
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='businesses',
        verbose_name='مالک',
    )

    # ═══════════ اطلاعات پایه ═══════════
    name = models.CharField('نام کسب‌وکار', max_length=100)
    category = models.ForeignKey(
        'categories.BusinessCategory',
        on_delete=models.PROTECT,
        related_name='businesses',
        verbose_name='نوع کسب‌وکار',
    )
    province = models.ForeignKey(
        'locations.Province',
        on_delete=models.PROTECT,
        verbose_name='استان',
    )
    city = models.ForeignKey(
        'locations.City',
        on_delete=models.PROTECT,
        verbose_name='شهر',
    )
    address = models.TextField('آدرس')
    phone = models.CharField('شماره تماس', max_length=20, blank=True, default='')
    working_hours = models.CharField('ساعات کاری', max_length=100, blank=True, default='')
    about = models.TextField('درباره کسب‌وکار', blank=True, default='')

    # ═══════════ تصاویر ═══════════
    cover_image = models.ImageField(
        'تصویر کاور',
        upload_to='businesses/covers/',
        null=True,
        blank=True,
    )
    owner_photo = models.ImageField(
        'عکس مالک',
        upload_to='businesses/owners/',
        null=True,
        blank=True,
    )
    logo = models.ImageField(
        'لوگو',
        upload_to='businesses/logos/',
        null=True,
        blank=True,
    )

    # ═══════════ موقعیت جغرافیایی (PostGIS) ═══════════
    latitude = models.DecimalField(
        'عرض جغرافیایی',
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        'طول جغرافیایی',
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    location = gis_models.PointField(
        'موقعیت جغرافیایی',
        null=True,
        blank=True,
        geography=True,
        help_text='موقعیت جغرافیایی به فرمت PostGIS',
    )

    # ═══════════ وضعیت تایید ═══════════
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField('دلیل رد', blank=True, default='')

    # ═══════════ احراز هویت ═══════════
    national_id = models.CharField('کد ملی', max_length=10, blank=True, default='')
    verified_name = models.CharField('نام تایید شده', max_length=100, blank=True, default='')
    is_national_id_verified = models.BooleanField('کد ملی تایید شده', default=False)

    # ═══════════ حساب بانکی ═══════════
    bank_owner_name = models.CharField('نام صاحب حساب', max_length=100, blank=True, default='')
    bank_national_id = models.CharField('کد ملی صاحب حساب', max_length=10, blank=True, default='')
    bank_name = models.CharField('نام بانک', max_length=100, blank=True, default='')
    bank_id = models.CharField('شناسه بانک', max_length=20, blank=True, default='')
    bank_sheba = models.CharField('شماره شبا', max_length=26, blank=True, default='')
    bank_card_number = models.CharField('شماره کارت', max_length=16, blank=True, default='')
    bank_account_number = models.CharField('شماره حساب', max_length=30, blank=True, default='')
    bank_info_registered = models.BooleanField('اطلاعات بانکی ثبت شده', default=False)
    bank_info_verified = models.BooleanField('اطلاعات بانکی تایید شده', default=False)

    # ═══════════ لینک رزرو ═══════════
    booking_slug = models.SlugField('اسلاگ رزرو', unique=True)
    booking_link_clicks = models.IntegerField('کلیک‌های لینک رزرو', default=0)
    booking_link_bookings = models.IntegerField('رزروهای لینک رزرو', default=0)

    # ═══════════ آمار ═══════════
    rating = models.DecimalField('میانگین امتیاز', max_digits=2, decimal_places=1, default=0)
    reviews_count = models.IntegerField('تعداد نظرات', default=0)

    # ═══════════ VIP ═══════════
    is_vip = models.BooleanField('VIP', default=False)
    vip_expires_at = models.DateTimeField('انقضای VIP', null=True, blank=True)

    class Meta:
        db_table = 'businesses'
        verbose_name = '🏪 کسب‌وکار'
        verbose_name_plural = '🏪 کسب‌وکارها'
        ordering = ['-rating', '-created_at']
        indexes = [
            models.Index(fields=['status', 'city']),
            models.Index(fields=['province', 'city']),
        ]

    def __str__(self):
        return self.name

    @transaction.atomic
    def save(self, *args, **kwargs):
        """ذخیره با تولید slug و booking_slug و به‌روزرسانی location"""

        # ═══ به‌روزرسانی location از lat/lng ═══
        if self.latitude is not None and self.longitude is not None:
            self.location = Point(
                float(self.longitude),  # longitude اول
                float(self.latitude),   # latitude دوم
                srid=4326,
            )
        elif self.location is not None:
            # اگر location هست ولی lat/lng نیست، از location بخوان
            self.latitude = self.location.y
            self.longitude = self.location.x

        # ═══ تولید booking_slug ═══
        if not self.booking_slug:
            base_slug = slugify(self.name, allow_unicode=True)[:50]
            slug = base_slug
            counter = 1
            while True:
                exists = Business.objects.select_for_update().filter(
                    booking_slug=slug
                ).exclude(pk=self.pk).exists()
                if not exists:
                    break
                slug = f'{base_slug}-{counter}'
                counter += 1
                if counter > 100:
                    slug = f'{base_slug}-{secrets.token_hex(3)}'
                    break
            self.booking_slug = slug

        super().save(*args, **kwargs)

    def calculate_distance(self, user_lat, user_lng):
        """محاسبه فاصله تا کاربر (متر) — با PostGIS"""
        if self.location is None:
            return None
        user_point = Point(float(user_lng), float(user_lat), srid=4326)
        # distance با geography=True به متر برمی‌گردد
        return self.location.distance(user_point)

    @classmethod
    def nearby(cls, lat, lng, radius_km=10):
        """دریافت کسب‌وکارهای نزدیک — با PostGIS"""
        point = Point(float(lng), float(lat), srid=4326)
        return cls.objects.filter(
            location__distance_lte=(point, D(km=radius_km)),
            status=cls.Status.APPROVED,
            is_active=True,
        ).distance(point).order_by('distance')


class BusinessGallery(BaseModel):
    """گالری تصاویر کسب‌وکار (حداکثر ۳ تصویر)"""
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='gallery',
        verbose_name='کسب‌وکار',
    )
    image = models.ImageField(
        'تصویر',
        upload_to='businesses/gallery/',
    )
    sort_order = models.IntegerField('ترتیب', default=0)

    class Meta:
        db_table = 'business_gallery'
        verbose_name = '🖼️ تصویر گالری'
        verbose_name_plural = '🖼️ گالری تصاویر'
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.business.name} - تصویر {self.sort_order}'

    def clean(self):
        if self.pk is None and self.business.gallery.count() >= 3:
            raise ValidationError('حداکثر ۳ تصویر مجاز است')


class BusinessTeamMember(BaseModel):
    """اعضای تیم کسب‌وکار"""
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='team_members',
        verbose_name='کسب‌وکار',
    )
    name = models.CharField('نام', max_length=100)
    phone = models.CharField('شماره تماس', max_length=11)
    services = models.ManyToManyField(
        'services.Service',
        blank=True,
        related_name='team_members',
        verbose_name='خدمات',
    )

    class Meta:
        db_table = 'business_team_members'
        verbose_name = '👤 عضو تیم'
        verbose_name_plural = '👤 اعضای تیم'
        unique_together = ['business', 'phone']

    def __str__(self):
        return f'{self.business.name} - {self.name}'