"""
Views مربوط به ثبت و مدیریت کسب‌وکار
هر کاربر فقط یک کسب‌وکار
"""
import logging
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import OpenApiParameter, extend_schema
from django.contrib.gis.measure import D
from django.contrib.gis.geos import Point
from apps.core.mixins import StandardResponseMixin
from apps.core.pagination import StandardResultsSetPagination
from apps.core.permissions import AllowAnyVerified, IsApprovedBusinessOwner
from apps.core.utils import mask_phone
from apps.businesses.models import Business
from apps.businesses.serializers.business import (
    BusinessCreateSerializer,
    BusinessDetailSerializer,
    BusinessUpdateSerializer,
    BusinessBankInfoSerializer,
    BusinessStatusSerializer,
    BusinessListSerializer,
)

logger = logging.getLogger(__name__)


class BusinessCreateView(APIView, StandardResponseMixin):
    """ثبت کسب‌وکار جدید — هر کاربر فقط یک کسب‌وکار"""
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
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        try:
            business = serializer.save()
            logger.info(f"New business created: {business.name} by {request.user.phone}")

            return self.success_response(
                data=BusinessDetailSerializer(business).data,
                message='کسب‌وکار شما با موفقیت ثبت شد و در انتظار تایید است',
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Business creation failed: {e}")
            return self.error_response(
                message='خطا در ثبت کسب‌وکار',
                code='CREATION_FAILED',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BusinessListView(APIView, StandardResponseMixin):
    """لیست عمومی کسب‌وکارها با فیلترهای مختلف + nearby"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='province_id', type=int, required=False),
            OpenApiParameter(name='city_id', type=int, required=False),
            OpenApiParameter(name='category_id', type=int, required=False),
            OpenApiParameter(name='search', type=str, required=False),
            OpenApiParameter(name='lat', type=float, required=False,
                           description='عرض جغرافیایی کاربر'),
            OpenApiParameter(name='lng', type=float, required=False,
                           description='طول جغرافیایی کاربر'),
            OpenApiParameter(name='radius', type=float, required=False,
                           description='شعاع جستجو (کیلومتر، پیش‌فرض ۱۰)'),
            OpenApiParameter(name='page', type=int, required=False),
            OpenApiParameter(name='page_size', type=int, required=False),
        ],
        responses={200: BusinessListSerializer(many=True)},
        tags=['Businesses'],
        summary='لیست کسب‌وکارها',
    )
    def get(self, request):
        qs = Business.objects.filter(
            status=Business.Status.APPROVED,
            is_active=True,
        ).select_related('category', 'city', 'province')

        # ─── فیلترهای ساده ───
        province_id = request.query_params.get('province_id')
        if province_id:
            qs = qs.filter(province_id=province_id)

        city_id = request.query_params.get('city_id')
        if city_id:
            qs = qs.filter(city_id=city_id)

        category_id = request.query_params.get('category_id')
        if category_id:
            qs = qs.filter(category_id=category_id)

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(about__icontains=search) |
                Q(address__icontains=search)
            )

        # ─── Nearby Search ───
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        if lat and lng:
            try:
                lat, lng = float(lat), float(lng)
                radius = float(request.query_params.get('radius', 10))
                point = Point(lng, lat, srid=4326)
                qs = qs.filter(
                    location__distance_lte=(point, D(km=radius))
                ).distance(point).order_by('distance')
            except (ValueError, TypeError):
                pass
        else:
            qs = qs.order_by('-rating', '-created_at')

        # ─── Pagination ───
        pagination = StandardResultsSetPagination()
        page = pagination.paginate_queryset(qs, request)
        if page is not None:
            serializer = BusinessListSerializer(
                page, many=True, context={'request': request}
            )
            return pagination.get_paginated_response(serializer.data)

        serializer = BusinessListSerializer(
            qs, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': qs.count()},
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
        business = request.user.businesses.filter(is_active=True).first()

        if business:
            return self.success_response(
                data={
                    'has_business': True,
                    'business_id': business.id,
                    'status': business.status,
                    'status_display': business.get_status_display(),
                    'rejection_reason': business.rejection_reason if business.status == Business.Status.REJECTED else None,
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
                    'created_at': None,
                }
            )


class BusinessDetailView(APIView, StandardResponseMixin):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        responses=BusinessDetailSerializer,
        tags=['Business Management'],
        summary='جزئیات کسب‌وکار',
    )
    def get(self, request):
        business = request.user.businesses.filter(is_active=True).first()
        if not business:
            return self.error_response(
                message='شما کسب‌وکاری ثبت نکرده‌اید',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = BusinessDetailSerializer(business)
        return self.success_response(data=serializer.data)

    # ✅ متد PUT اضافه شد
    @extend_schema(
        request=BusinessUpdateSerializer,
        responses=BusinessDetailSerializer,
        tags=['Business Management'],
        summary='بروزرسانی کسب‌وکار',
    )
    def put(self, request):
        business = request.user.businesses.filter(is_active=True).first()
        if not business:
            return self.error_response(
                message='شما کسب‌وکاری ثبت نکرده‌اید',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BusinessUpdateSerializer(
            business, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated_business = serializer.save()

        # ✅ اگر rejected بوده، دوباره به pending برگردد
        if business.status == Business.Status.REJECTED:
            updated_business.status = Business.Status.PENDING
            updated_business.rejection_reason = ''
            updated_business.save(update_fields=['status', 'rejection_reason'])

        return self.success_response(
            data=BusinessDetailSerializer(updated_business).data,
            message='کسب‌وکار با موفقیت بروزرسانی شد',
        )

class BusinessBankInfoView(APIView, StandardResponseMixin):
    """مدیریت اطلاعات بانکی کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        responses=BusinessBankInfoSerializer,
        tags=['Business Management'],
        summary='دریافت اطلاعات بانکی',
    )
    def get(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            return self.error_response(
                message='کسب‌وکار تایید شده یافت نشد',
                code='NO_APPROVED_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BusinessBankInfoSerializer(business)
        return self.success_response(data=serializer.data)

    @extend_schema(
        request=BusinessBankInfoSerializer,
        responses=BusinessBankInfoSerializer,
        tags=['Business Management'],
        summary='ثبت/ویرایش اطلاعات بانکی',
    )
    def put(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        if not business:
            return self.error_response(
                message='کسب‌وکار تایید شده یافت نشد',
                code='NO_APPROVED_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BusinessBankInfoSerializer(
            business,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        return self.success_response(
            data=BusinessBankInfoSerializer(updated).data,
            message='اطلاعات بانکی با موفقیت ثبت شد',
        )


class BusinessDeleteView(APIView, StandardResponseMixin):
    """حذف کسب‌وکار"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Business Management'],
        summary='حذف کسب‌وکار',
    )
    def delete(self, request):
        business = request.user.businesses.filter(is_active=True).first()

        if not business:
            return self.error_response(
                message='شما کسب‌وکاری ثبت نکرده‌اید',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )

        # بررسی نوبت‌های فعال
        from apps.appointments.models import Appointment
        active_count = Appointment.objects.filter(
            business=business,
            status__in=[
                Appointment.Status.RESERVED,
            ],
        ).count()

        if active_count > 0:
            return self.error_response(
                message=f'شما {active_count} نوبت فعال دارید. ابتدا تمام نوبت‌ها را لغو کنید',
                code='ACTIVE_APPOINTMENTS',
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            business_name = business.name
            business.is_active = False
            business.save(update_fields=['is_active'])

            logger.info(f"Business deleted: {business_name} by {request.user.phone}")

            return self.success_response(
                message='کسب‌وکار با موفقیت حذف شد',
            )
        except Exception as e:
            logger.error(f"Business deletion failed: {e}")
            return self.error_response(
                message='خطا در حذف کسب‌وکار',
                code='DELETION_FAILED',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PublicBusinessDetailView(APIView, StandardResponseMixin):
    """جزئیات عمومی کسب‌وکار (برای مشتریان)"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=BusinessDetailSerializer,
        tags=['Public'],
        summary='جزئیات عمومی کسب‌وکار',
    )
    def get(self, request, booking_slug):
        try:
            business = Business.objects.select_related(
                'category', 'province', 'city', 'owner'
            ).prefetch_related('gallery').get(
                booking_slug=booking_slug,
                status='approved',
                is_active=True,
            )
        except Business.DoesNotExist:
            return self.error_response(
                message='کسب‌وکار مورد نظر یافت نشد',
                code='BUSINESS_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        # افزایش شمارنده کلیک
        business.booking_link_clicks += 1
        business.save(update_fields=['booking_link_clicks'])

        serializer = BusinessDetailSerializer(business)
        return self.success_response(data=serializer.data)