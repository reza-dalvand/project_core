"""
Views مربوط به ثبت و مدیریت کسب‌وکار
"""
import logging
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsCustomer, AllowAnyVerified
from apps.core.utils import mask_phone
from apps.accounts.services.shahkar_service import ShahkarService
from apps.businesses.models import Business, Category, Province, City
from apps.businesses.serializers.business import (
    ProvinceSerializer,
    CitySerializer,
    CategorySerializer,
    NationalIdVerificationSerializer,
    NationalIdVerificationResponseSerializer,
    BusinessCreateSerializer,
    BusinessDetailSerializer,
    BusinessUpdateSerializer,
    BusinessStatusSerializer,
    ImageUploadSerializer,
    ImageUploadResponseSerializer,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#   Lookup Endpoints (برای Dropdown ها)
# ═══════════════════════════════════════════════

class ProvinceListView(APIView, StandardResponseMixin):
    """لیست استان‌ها"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=ProvinceSerializer(many=True),
        tags=['Business Registration'],
        summary='لیست استان‌ها',
        description='دریافت لیست تمام استان‌های فعال برای انتخاب در فرم ثبت کسب‌وکار'
    )
    def get(self, request):
        provinces = Province.objects.all().order_by('order', 'name')
        serializer = ProvinceSerializer(provinces, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': provinces.count()}
        )


class CityListView(APIView, StandardResponseMixin):
    """لیست شهرهای یک استان"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=CitySerializer(many=True),
        tags=['Business Registration'],
        summary='لیست شهرها',
        description='دریافت لیست شهرهای یک استان خاص'
    )
    def get(self, request, province_id):
        try:
            province = Province.objects.get(id=province_id)
        except Province.DoesNotExist:
            return self.error_response(
                message='استان مورد نظر یافت نشد',
                code='PROVINCE_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND
            )

        cities = City.objects.filter(province=province).order_by('order', 'name')
        serializer = CitySerializer(cities, many=True)
        return self.success_response(
            data=serializer.data,
            meta={
                'count': cities.count(),
                'province': province.name
            }
        )


class CategoryListView(APIView, StandardResponseMixin):
    """لیست دسته‌بندی‌ها با زیردسته‌ها"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=CategorySerializer(many=True),
        tags=['Business Registration'],
        summary='لیست دسته‌بندی‌ها',
        description='دریافت لیست تمام دسته‌بندی‌های فعال به همراه زیردسته‌های آن‌ها'
    )
    def get(self, request):
        categories = Category.objects.filter(is_active=True).order_by('order', 'name')
        serializer = CategorySerializer(categories, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'count': categories.count()}
        )


# ═══════════════════════════════════════════════
#   National ID Verification
# ═══════════════════════════════════════════════

class NationalIdVerificationView(APIView, StandardResponseMixin):
    """استعلام کد ملی از سامانه شاهکار"""
    permission_classes = [AllowAnyVerified]

    @extend_schema(
        request=NationalIdVerificationSerializer,
        responses=NationalIdVerificationResponseSerializer,
        tags=['Business Registration'],
        summary='استعلام کد ملی',
        description='تطبیق کد ملی با شماره موبایل ثبت‌نام شده از طریق سامانه شاهکار'
    )
    def post(self, request):
        serializer = NationalIdVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        national_id = serializer.validated_data['national_id']
        user = request.user

        try:
            # استعلام از شاهکار
            result = ShahkarService.verify(national_id, user.phone)

            # ذخیره نتیجه در کاربر
            user.national_id = national_id
            user.national_id_verified = True
            user.verified_name = result.get('verified_name', '')
            user.save(update_fields=['national_id', 'national_id_verified', 'verified_name'])

            return self.success_response(
                data={
                    'success': True,
                    'verified_name': result['verified_name'],
                    'national_id': national_id,
                    'phone_display': mask_phone(user.phone),
                    'message': 'کد ملی با موفقیت تایید شد'
                },
                message='هویت شما با موفقیت تایید شد'
            )

        except Exception as e:
            logger.error(f"National ID verification failed: {e}")
            return self.error_response(
                message=str(e),
                code='VERIFICATION_FAILED',
                status=status.HTTP_400_BAD_REQUEST
            )


# ═══════════════════════════════════════════════
#   Business Creation
# ═══════════════════════════════════════════════

class BusinessCreateView(APIView, StandardResponseMixin):
    """ثبت کسب‌وکار جدید"""
    permission_classes = [AllowAnyVerified]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        request=BusinessCreateSerializer,
        responses=BusinessDetailSerializer,
        tags=['Business Registration'],
        summary='ثبت کسب‌وکار',
        description='ثبت کسب‌وکار جدید با اطلاعات پایه و احراز هویت'
    )
    def post(self, request):
        serializer = BusinessCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        try:
            business = serializer.save()

            # ارسال نوتیفیکیشن به ادمین‌ها (بعداً پیاده‌سازی می‌شود)
            # NotificationService.notify_admins_new_business(business)

            logger.info(f"New business created: {business.name} by {request.user.phone}")

            return self.success_response(
                data=BusinessDetailSerializer(business).data,
                message='کسب‌وکار شما با موفقیت ثبت شد و در انتظار تایید است',
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Business creation failed: {e}")
            return self.error_response(
                message='خطا در ثبت کسب‌وکار',
                code='CREATION_FAILED',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ═══════════════════════════════════════════════
#   Business Status
# ═══════════════════════════════════════════════

class BusinessStatusView(APIView, StandardResponseMixin):
    """وضعیت کسب‌وکار کاربر"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=BusinessStatusSerializer,
        tags=['Business Registration'],
        summary='وضعیت کسب‌وکار',
        description='دریافت وضعیت کسب‌وکار کاربر (آیا دارد؟ وضعیت تایید چیست؟)'
    )
    def get(self, request):
        user = request.user

        if hasattr(user, 'business'):
            business = user.business
            return self.success_response(
                data={
                    'has_business': True,
                    'business_id': business.id,
                    'status': business.status,
                    'status_display': business.get_status_display(),
                    'rejection_reason': business.rejection_reason if business.status == Business.Status.REJECTED else None,
                    'approved_at': business.approved_at,
                    'created_at': business.created_at,
                }
            )
        else:
            return self.success_response(
                data={
                    'has_business': False,
                    'business_id': None,
                    'status': None,
                    'status_display': None,
                    'rejection_reason': None,
                    'approved_at': None,
                    'created_at': None,
                }
            )


# ═══════════════════════════════════════════════
#   Business Detail & Update
# ═══════════════════════════════════════════════

class BusinessDetailView(APIView, StandardResponseMixin):
    """جزئیات و بروزرسانی کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        responses=BusinessDetailSerializer,
        tags=['Business Management'],
        summary='جزئیات کسب‌وکار',
        description='دریافت جزئیات کسب‌وکار کاربر'
    )
    def get(self, request):
        user = request.user

        if not hasattr(user, 'business'):
            return self.error_response(
                message='شما کسب‌وکاری ثبت نکرده‌اید',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND
            )

        business = user.business
        serializer = BusinessDetailSerializer(business)
        return self.success_response(data=serializer.data)

    @extend_schema(
        request=BusinessUpdateSerializer,
        responses=BusinessDetailSerializer,
        tags=['Business Management'],
        summary='بروزرسانی کسب‌وکار',
        description='بروزرسانی اطلاعات کسب‌وکار'
    )
    def put(self, request):
        user = request.user

        if not hasattr(user, 'business'):
            return self.error_response(
                message='شما کسب‌وکاری ثبت نکرده‌اید',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND
            )

        business = user.business

        # فقط کسب‌وکارهای تایید شده یا رد شده قابل ویرایش هستند
        if business.status == Business.Status.PENDING:
            return self.error_response(
                message='کسب‌وکار شما در حال بررسی است و قابل ویرایش نیست',
                code='PENDING_REVIEW',
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = BusinessUpdateSerializer(
            business,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)

        updated_business = serializer.save()

        # اگر کسب‌وکار قبلاً رد شده بود، وضعیت را به pending تغییر بده
        if business.status == Business.Status.REJECTED:
            updated_business.status = Business.Status.PENDING
            updated_business.rejection_reason = ''
            updated_business.save()

        return self.success_response(
            data=BusinessDetailSerializer(updated_business).data,
            message='کسب‌وکار با موفقیت بروزرسانی شد'
        )


# ═══════════════════════════════════════════════
#   Image Upload
# ═══════════════════════════════════════════════

class ImageUploadView(APIView, StandardResponseMixin):
    """آپلود تصاویر کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=ImageUploadSerializer,
        responses=ImageUploadResponseSerializer,
        tags=['Business Management'],
        summary='آپلود تصویر',
        description='آپلود تصاویر کسب‌وکار (کاور، لوگو، عکس صاحب کسب‌وکار)'
    )
    def post(self, request):
        user = request.user

        if not hasattr(user, 'business'):
            return self.error_response(
                message='شما کسب‌وکاری ثبت نکرده‌اید',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND
            )

        business = user.business

        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image = serializer.validated_data['image']
        image_type = serializer.validated_data['image_type']

        try:
            # ذخیره تصویر بر اساس نوع
            if image_type == 'cover':
                business.cover = image
                business.save(update_fields=['cover'])
                image_url = business.cover.url
            elif image_type == 'logo':
                business.logo = image
                business.save(update_fields=['logo'])
                image_url = business.logo.url
            elif image_type == 'owner_photo':
                business.owner_photo = image
                business.save(update_fields=['owner_photo'])
                image_url = business.owner_photo.url
            else:
                return self.error_response(
                    message='نوع تصویر نامعتبر است',
                    code='INVALID_IMAGE_TYPE',
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Image uploaded: {image_type} for business {business.id}")

            return self.success_response(
                data={
                    'success': True,
                    'image_url': image_url,
                    'image_type': image_type,
                    'message': 'تصویر با موفقیت آپلود شد'
                },
                message='تصویر با موفقیت آپلود شد'
            )

        except Exception as e:
            logger.error(f"Image upload failed: {e}")
            return self.error_response(
                message='خطا در آپلود تصویر',
                code='UPLOAD_FAILED',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ═══════════════════════════════════════════════
#   Business Delete
# ═══════════════════════════════════════════════

class BusinessDeleteView(APIView, StandardResponseMixin):
    """حذف کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Business Management'],
        summary='حذف کسب‌وکار',
        description='حذف کامل کسب‌وکار و تمام اطلاعات مرتبط'
    )
    def delete(self, request):
        user = request.user

        if not hasattr(user, 'business'):
            return self.error_response(
                message='شما کسب‌وکاری ثبت نکرده‌اید',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND
            )

        business = user.business

        # بررسی نوبت‌های فعال
        from apps.bookings.models import Appointment
        active_appointments = Appointment.objects.filter(
            business=business,
            status__in=[Appointment.Status.RESERVED, Appointment.Status.CONFIRMED]
        ).count()

        if active_appointments > 0:
            return self.error_response(
                message=f'شما {active_appointments} نوبت فعال دارید. ابتدا تمام نوبت‌ها را لغو کنید',
                code='ACTIVE_APPOINTMENTS',
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            business_name = business.name
            business.delete()

            logger.info(f"Business deleted: {business_name} by {user.phone}")

            return self.success_response(
                message='کسب‌وکار با موفقیت حذف شد'
            )

        except Exception as e:
            logger.error(f"Business deletion failed: {e}")
            return self.error_response(
                message='خطا در حذف کسب‌وکار',
                code='DELETION_FAILED',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )