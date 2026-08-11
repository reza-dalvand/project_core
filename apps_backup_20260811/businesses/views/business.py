"""
Views مربوط به ثبت و مدیریت کسب‌وکار
✅ بهینه‌شده: Cache برای داده‌های استاتیک
"""
import logging
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.core.cache import cache
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


class ProvinceListView(APIView, StandardResponseMixin):
    """
    ✅ بهینه: Cache کردن provinces (تغییر نمی‌کنند)
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=ProvinceSerializer(many=True),
        tags=['Business Registration'],
        summary='لیست استان‌ها',
    )
    def get(self, request):
        cache_key = 'provinces_list'
        provinces_data = cache.get(cache_key)

        if not provinces_data:
            provinces = Province.objects.all().order_by('order', 'name')
            serializer = ProvinceSerializer(provinces, many=True)
            provinces_data = serializer.data
            cache.set(cache_key, provinces_data, timeout=86400)  # ۲۴ ساعت

        return self.success_response(
            data=provinces_data,
            meta={'count': len(provinces_data)}
        )


class CityListView(APIView, StandardResponseMixin):
    """
    ✅ بهینه: Cache کردن cities per province
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=CitySerializer(many=True),
        tags=['Business Registration'],
        summary='لیست شهرها',
    )
    def get(self, request, province_id):
        cache_key = f'cities_list_{province_id}'
        cities_data = cache.get(cache_key)

        if not cities_data:
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
            cities_data = {
                'data': serializer.data,
                'province': province.name,
            }
            cache.set(cache_key, cities_data, timeout=86400)

        return self.success_response(
            data=cities_data['data'],
            meta={
                'count': len(cities_data['data']),
                'province': cities_data['province']
            }
        )


class CategoryListView(APIView, StandardResponseMixin):
    """
    ✅ بهینه: Cache کردن categories + prefetch subcategories
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=CategorySerializer(many=True),
        tags=['Business Registration'],
        summary='لیست دسته‌بندی‌ها',
    )
    def get(self, request):
        cache_key = 'categories_list'
        categories_data = cache.get(cache_key)

        if not categories_data:
            categories = Category.objects.filter(
                is_active=True
            ).prefetch_related(
                'subcategories'
            ).order_by('order', 'name')

            serializer = CategorySerializer(categories, many=True)
            categories_data = serializer.data
            cache.set(cache_key, categories_data, timeout=3600)  # ۱ ساعت

        return self.success_response(
            data=categories_data,
            meta={'count': len(categories_data)}
        )


# بقیه views بدون تغییر...
class NationalIdVerificationView(APIView, StandardResponseMixin):
    """استعلام کد ملی از سامانه شاهکار"""
    permission_classes = [AllowAnyVerified]

    @extend_schema(
        request=NationalIdVerificationSerializer,
        responses=NationalIdVerificationResponseSerializer,
        tags=['Business Registration'],
        summary='استعلام کد ملی',
    )
    def post(self, request):
        serializer = NationalIdVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        national_id = serializer.validated_data['national_id']
        user = request.user

        try:
            result = ShahkarService.verify(national_id, user.phone)
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


class BusinessCreateView(APIView, StandardResponseMixin):
    """ثبت کسب‌وکار جدید"""
    permission_classes = [AllowAnyVerified]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        request=BusinessCreateSerializer,
        responses=BusinessDetailSerializer,
        tags=['Business Registration'],
        summary='ثبت کسب‌وکار',
    )
    def post(self, request):
        serializer = BusinessCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        try:
            business = serializer.save()
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


class BusinessStatusView(APIView, StandardResponseMixin):
    """وضعیت کسب‌وکار کاربر"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=BusinessStatusSerializer,
        tags=['Business Registration'],
        summary='وضعیت کسب‌وکار',
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


class BusinessDetailView(APIView, StandardResponseMixin):
    """جزئیات و بروزرسانی کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(responses=BusinessDetailSerializer, tags=['Business Management'], summary='جزئیات کسب‌وکار')
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

    @extend_schema(request=BusinessUpdateSerializer, responses=BusinessDetailSerializer, tags=['Business Management'], summary='بروزرسانی کسب‌وکار')
    def put(self, request):
        user = request.user
        if not hasattr(user, 'business'):
            return self.error_response(
                message='شما کسب‌وکاری ثبت نکرده‌اید',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND
            )
        business = user.business
        if business.status == Business.Status.PENDING:
            return self.error_response(
                message='کسب‌وکار شما در حال بررسی است و قابل ویرایش نیست',
                code='PENDING_REVIEW',
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = BusinessUpdateSerializer(business, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_business = serializer.save()
        if business.status == Business.Status.REJECTED:
            updated_business.status = Business.Status.PENDING
            updated_business.rejection_reason = ''
            updated_business.save()
        return self.success_response(
            data=BusinessDetailSerializer(updated_business).data,
            message='کسب‌وکار با موفقیت بروزرسانی شد'
        )


class ImageUploadView(APIView, StandardResponseMixin):
    """آپلود تصاویر کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=ImageUploadSerializer, responses=ImageUploadResponseSerializer, tags=['Business Management'], summary='آپلود تصویر')
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
            return self.success_response(
                data={'success': True, 'image_url': image_url, 'image_type': image_type, 'message': 'تصویر با موفقیت آپلود شد'},
                message='تصویر با موفقیت آپلود شد'
            )
        except Exception as e:
            logger.error(f"Image upload failed: {e}")
            return self.error_response(
                message='خطا در آپلود تصویر',
                code='UPLOAD_FAILED',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BusinessDeleteView(APIView, StandardResponseMixin):
    """حذف کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Business Management'], summary='حذف کسب‌وکار')
    def delete(self, request):
        user = request.user
        if not hasattr(user, 'business'):
            return self.error_response(
                message='شما کسب‌وکاری ثبت نکرده‌اید',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND
            )
        business = user.business

        from apps.bookings.models import Appointment
        active_count = Appointment.objects.filter(
            business=business,
            status__in=[Appointment.Status.RESERVED, Appointment.Status.CONFIRMED]
        ).count()

        if active_count > 0:
            return self.error_response(
                message=f'شما {active_count} نوبت فعال دارید. ابتدا تمام نوبت‌ها را لغو کنید',
                code='ACTIVE_APPOINTMENTS',
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            business_name = business.name
            business.delete()
            logger.info(f"Business deleted: {business_name} by {user.phone}")
            return self.success_response(message='کسب‌وکار با موفقیت حذف شد')
        except Exception as e:
            logger.error(f"Business deletion failed: {e}")
            return self.error_response(
                message='خطا در حذف کسب‌وکار',
                code='DELETION_FAILED',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )