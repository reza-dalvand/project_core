"""
Views برای کسب‌وکار — نسخه نهایی (فاز ۴)
"""
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404
from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.businesses.models import Business, BusinessGallery
from apps.businesses.serializers.business import (
    BusinessCreateSerializer,
    BusinessDetailSerializer,
    BusinessUpdateSerializer,
    BusinessBankInfoSerializer,
    BusinessGallerySerializer,
)


class BusinessCreateView(APIView, StandardResponseMixin):
    """ثبت کسب‌وکار جدید"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        request=BusinessCreateSerializer,
        responses={201: BusinessDetailSerializer},
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
            return self.success_response(
                data=BusinessDetailSerializer(business).data,
                message='کسب‌وکار شما با موفقیت ثبت شد و در انتظار تایید است',
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return self.error_response(
                message='خطا در ثبت کسب‌وکار',
                code='CREATION_FAILED',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BusinessListView(generics.ListAPIView, StandardResponseMixin):
    """لیست عمومی کسب‌وکارها"""
    permission_classes = [permissions.AllowAny]
    serializer_class = BusinessDetailSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Business.objects.filter(
            status=Business.Status.APPROVED,
            is_active=True,
             is_suspended=False,
        ).select_related('category', 'city', 'province')

        # ۱. فیلتر دسته‌بندی
        category_id = self.request.query_params.get('category_id')
        if category_id:
            # ✅ اصلاح: فیلتر بر اساس ServiceCategory از طریق services
            queryset = queryset.filter(
                services__category_id=category_id,
                services__is_active=True,
            ).distinct()

        # ۲. فیلترهای مکانی (استان/شهر و GPS)
        province_id = self.request.query_params.get('province_id')
        city_id = self.request.query_params.get('city_id')
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')

        if lat and lng:
            try:
                from django.contrib.gis.geos import Point
                from django.contrib.gis.measure import D
                from django.contrib.gis.db.models.functions import Distance
                lat, lng = float(lat), float(lng)
                radius = float(self.request.query_params.get('radius', 10))
                point = Point(lng, lat, srid=4326)
                
                queryset = queryset.filter(
                    location__isnull=False,
                    location__distance_lte=(point, D(km=radius))
                ).annotate(distance=Distance('location', point)).order_by('distance')
            except (ValueError, TypeError, Exception):
                queryset = queryset.order_by('-rating', '-created_at')
        elif province_id:
            queryset = queryset.filter(province_id=province_id)
            if city_id:
                queryset = queryset.filter(city_id=city_id)
            queryset = queryset.order_by('-rating', '-created_at')
        else:
            queryset = queryset.order_by('-rating', '-created_at')

        return queryset

    
class BusinessStatusView(APIView, StandardResponseMixin):
    """وضعیت کسب‌وکار کاربر"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
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
    """جزئیات کسب‌وکار کاربر"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        responses={200: BusinessDetailSerializer},
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

    @extend_schema(
        request=BusinessUpdateSerializer,
        responses={200: BusinessDetailSerializer},
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
        if business.status == Business.Status.REJECTED:
            updated_business.status = Business.Status.PENDING
            updated_business.rejection_reason = ''
            updated_business.save(update_fields=['status', 'rejection_reason'])
        return self.success_response(
            data=BusinessDetailSerializer(updated_business).data,
            message='کسب‌وکار با موفقیت بروزرسانی شد',
        )


class BusinessBankInfoView(APIView, StandardResponseMixin):
    """
    مدیریت اطلاعات بانکی کسب‌وکار

    ✅ تغییر: پرمیشن از IsApprovedBusinessOwner به IsAuthenticated تغییر کرد.
    ✅ تغییر: فیلتر status='approved' از کوئری کسب‌وکار حذف شد.
    ✅ حالا فقط چک می‌شود کاربر لاگین است و حداقل یک کسب‌وکار فعال دارد.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: BusinessBankInfoSerializer},
        tags=['Business Management'],
        summary='دریافت اطلاعات بانکی',
    )
    def get(self, request):
        business = request.user.businesses.filter(
            is_active=True,
        ).first()
        if not business:
            return self.error_response(
                message='کسب‌وکار یافت نشد',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = BusinessBankInfoSerializer(business)
        return self.success_response(data=serializer.data)

    @extend_schema(
        request=BusinessBankInfoSerializer,
        responses={200: BusinessBankInfoSerializer},
        tags=['Business Management'],
        summary='ثبت/ویرایش اطلاعات بانکی',
    )
    def put(self, request):
        business = request.user.businesses.filter(
            is_active=True,
        ).first()
        if not business:
            return self.error_response(
                message='کسب‌وکار یافت نشد',
                code='NO_BUSINESS',
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
        updated.bank_info_registered = True
        updated.save(update_fields=['bank_info_registered'])
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
        from apps.appointments.models import Appointment
        active_count = Appointment.objects.filter(
            business=business,
            status__in=[Appointment.Status.RESERVED],
        ).count()
        if active_count > 0:
            return self.error_response(
                message=f'شما {active_count} نوبت فعال دارید. ابتدا تمام نوبت‌ها را لغو کنید',
                code='ACTIVE_APPOINTMENTS',
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            business.is_active = False
            business.save(update_fields=['is_active'])
            return self.success_response(message='کسب‌وکار با موفقیت حذف شد')
        except Exception as e:
            return self.error_response(
                message='خطا در حذف کسب‌وکار',
                code='DELETION_FAILED',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PublicBusinessDetailView(APIView, StandardResponseMixin):
    """جزئیات عمومی کسب‌وکار"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: BusinessDetailSerializer},
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
                is_suspended=False, 
            )
        except Business.DoesNotExist:
            return self.error_response(
                message='کسب‌وکار مورد نظر یافت نشد',
                code='BUSINESS_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )
        from django.db.models import F
        Business.objects.filter(pk=business.pk).update(
            booking_link_clicks=F('booking_link_clicks') + 1
        )
        serializer = BusinessDetailSerializer(business)
        return self.success_response(data=serializer.data)


class BusinessGalleryListView(APIView, StandardResponseMixin):
    """لیست تصاویر گالری"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        responses={200: BusinessGallerySerializer(many=True)},
        tags=['Business Management'],
        summary='لیست تصاویر گالری',
    )
    def get(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        if not business:
            return self.error_response(
                message='کسب‌وکار تایید شده یافت نشد',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )
        gallery = business.gallery.all().order_by('sort_order')
        serializer = BusinessGallerySerializer(
            gallery, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': gallery.count()},
        )


class BusinessGalleryUploadView(APIView, StandardResponseMixin):
    """آپلود تصویر گالری"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=['Business Management'],
        summary='آپلود تصویر گالری',
    )
    def post(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        if not business:
            return self.error_response(
                message='کسب‌وکار تایید شده یافت نشد',
                code='NO_BUSINESS',
                status=status.HTTP_404_NOT_FOUND,
            )
        if business.gallery.count() >= 3:
            return self.error_response(
                message='حداکثر ۳ تصویر در گالری مجاز است',
                code='GALLERY_LIMIT_REACHED',
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.businesses.serializers.business import BusinessGallerySerializer as BGS
        image = request.data.get('image')
        sort_order = int(request.data.get('sort_order', 0))
        try:
            gallery_item = BusinessGallery.objects.create(
                business=business,
                image=image,
                sort_order=sort_order,
            )
            return self.success_response(
                data=BGS(gallery_item, context={'request': request}).data,
                message='تصویر با موفقیت به گالری اضافه شد',
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return self.error_response(
                message='خطا در آپلود تصویر',
                code='UPLOAD_ERROR',
            )


class BusinessGalleryDeleteView(APIView, StandardResponseMixin):
    """حذف تصویر گالری"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Business Management'],
        summary='حذف تصویر گالری',
    )
    def delete(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        try:
            gallery_item = BusinessGallery.objects.get(id=pk, business=business)
            gallery_item.image.delete(save=False)
            gallery_item.delete()
            return self.success_response(message='تصویر از گالری حذف شد')
        except BusinessGallery.DoesNotExist:
            return self.error_response(
                message='تصویر گالری یافت نشد',
                code='GALLERY_ITEM_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )


class BusinessGalleryReorderView(APIView, StandardResponseMixin):
    """تغییر ترتیب تصاویر گالری"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Business Management'],
        summary='تغییر ترتیب تصاویر گالری',
    )
    def post(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        order = request.data.get('order', [])
        if not order:
            return self.error_response(
                message='لیست ترتیب تصاویر الزامی است',
                code='ORDER_REQUIRED',
            )
        try:
            for index, gallery_id in enumerate(order):
                BusinessGallery.objects.filter(
                    id=gallery_id, business=business
                ).update(sort_order=index)
            return self.success_response(
                message='ترتیب تصاویر گالری بروزرسانی شد',
            )
        except Exception as e:
            return self.error_response(
                message='خطا در تغییر ترتیب تصاویر',
                code='REORDER_ERROR',
            )