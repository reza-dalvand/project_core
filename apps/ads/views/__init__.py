"""
Views برای آگهی‌ها (مدلینگ + اجاره لاین)
"""
import logging
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.ads.models import ModelRequest, LineRental
from apps.ads.serializers import (
    ModelRequestListSerializer,
    ModelRequestDetailSerializer,
    ModelRequestCreateSerializer,
    ModelRequestUpdateSerializer,
    LineRentalListSerializer,
    LineRentalDetailSerializer,
    LineRentalCreateSerializer,
    LineRentalUpdateSerializer,
)



logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#   Model Requests
# ═══════════════════════════════════════════════

class ModelRequestListView(APIView, StandardResponseMixin):
    """لیست درخواست‌های مدل (عمومی) + فیلتر فاصله"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page', type=int, required=False),
            # ═══ 🆕 فاز ۳: پارامترهای فاصله ═══
            OpenApiParameter(
                name='lat', type=float, required=False,
                description='عرض جغرافیایی کاربر'
            ),
            OpenApiParameter(
                name='lng', type=float, required=False,
                description='طول جغرافیایی کاربر'
            ),
            OpenApiParameter(
                name='radius', type=float, required=False,
                description='شعاع جستجو (کیلومتر، پیش‌فرض ۱۰)'
            ),
        ],
        responses={200: ModelRequestListSerializer(many=True)},
        tags=['Ads'],
        summary='لیست درخواست‌های مدل',
    )
    def get(self, request):
        queryset = ModelRequest.objects.filter(
            business__status='approved',
            business__is_active=True,
        ).select_related(
            'business', 'service',
        ).order_by('-is_urgent', '-created_at')

        # ═══ 🆕 فاز ۳: فیلتر فاصله ═══
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        if lat and lng:
            try:
                from django.contrib.gis.geos import Point
                from django.contrib.gis.measure import D
                lat, lng = float(lat), float(lng)
                radius = float(request.query_params.get('radius', 10))
                point = Point(lng, lat, srid=4326)
                queryset = queryset.filter(
                    location__isnull=False,
                    location__distance_lte=(point, D(km=radius))
                ).distance(point).order_by('distance')
            except (ValueError, TypeError):
                pass

        pagination = StandardResultsSetPagination()
        page = pagination.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ModelRequestListSerializer(
                page, many=True, context={'request': request}
            )
            return pagination.get_paginated_response(serializer.data)

        serializer = ModelRequestListSerializer(
            queryset, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': queryset.count()},
        )


class ModelRequestDetailView(APIView, StandardResponseMixin):
    """جزئیات درخواست مدل"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: ModelRequestDetailSerializer},
        tags=['Ads'],
        summary='جزئیات درخواست مدل',
    )
    def get(self, request, pk):
        model_request = get_object_or_404(
            ModelRequest.objects.select_related('business', 'service'),
            id=pk,
            business__status='approved',
            business__is_active=True,
        )
        serializer = ModelRequestDetailSerializer(
            model_request, context={'request': request}
        )
        return self.success_response(data=serializer.data)


class BusinessModelRequestCreateView(APIView, StandardResponseMixin):
    """ایجاد درخواست مدل"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        request=ModelRequestCreateSerializer,
        responses={201: ModelRequestDetailSerializer},
        tags=['Ads'],
        summary='ایجاد درخواست مدل',
    )
    def post(self, request):
        serializer = ModelRequestCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        try:
            model_request = serializer.save()
            return self.success_response(
                data=ModelRequestDetailSerializer(
                    model_request, context={'request': request}
                ).data,
                message='درخواست مدل ایجاد شد',
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Create model request error: {e}")
            return self.error_response(
                message='خطا در ایجاد درخواست',
                code='CREATE_ERROR',
            )


class BusinessModelRequestListView(APIView, StandardResponseMixin):
    """لیست درخواست‌های مدل کسب‌وکار من"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Ads'],
        summary='درخواست‌های مدل من',
    )
    def get(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        requests_list = ModelRequest.objects.filter(
            business=business,
        ).select_related('service').order_by('-created_at')

        serializer = ModelRequestListSerializer(
            requests_list, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': requests_list.count()},
        )


class BusinessModelRequestDeleteView(APIView, StandardResponseMixin):
    """حذف درخواست مدل"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Ads'],
        summary='حذف درخواست مدل',
    )
    def delete(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        try:
            model_request = ModelRequest.objects.get(id=pk, business=business)
            model_request.delete()
            return self.success_response(message='درخواست مدل حذف شد')
        except ModelRequest.DoesNotExist:
            return self.error_response(
                message='درخواست یافت نشد',
                code='MODEL_REQUEST_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )


# ═══════════════════════════════════════════════
#   Line Rentals
# ═══════════════════════════════════════════════

class LineRentalListView(APIView, StandardResponseMixin):
    """لیست آگهی‌های اجاره لاین (عمومی) + فیلتر فاصله"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page', type=int, required=False),
            # ═══ 🆕 فاز ۳: پارامترهای فاصله ═══
            OpenApiParameter(
                name='lat', type=float, required=False,
                description='عرض جغرافیایی کاربر'
            ),
            OpenApiParameter(
                name='lng', type=float, required=False,
                description='طول جغرافیایی کاربر'
            ),
            OpenApiParameter(
                name='radius', type=float, required=False,
                description='شعاع جستجو (کیلومتر، پیش‌فرض ۱۰)'
            ),
        ],
        responses={200: LineRentalListSerializer(many=True)},
        tags=['Ads'],
        summary='لیست آگهی‌های اجاره لاین',
    )
    def get(self, request):
        queryset = LineRental.objects.filter(
            business__status='approved',
            business__is_active=True,
        ).select_related(
            'business', 'service_category', 'sub_service',
        ).order_by('-created_at')

        # ═══ 🆕 فاز ۳: فیلتر فاصله ═══
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        if lat and lng:
            try:
                from django.contrib.gis.geos import Point
                from django.contrib.gis.measure import D
                lat, lng = float(lat), float(lng)
                radius = float(request.query_params.get('radius', 10))
                point = Point(lng, lat, srid=4326)
                queryset = queryset.filter(
                    location__isnull=False,  # ✅ اضافه شد: فقط رکوردهایی که موقعیت دارند
                    location__distance_lte=(point, D(km=radius))
                ).distance(point).order_by('distance')
            except (ValueError, TypeError):
                pass

        pagination = StandardResultsSetPagination()
        page = pagination.paginate_queryset(queryset, request)
        if page is not None:
            serializer = LineRentalListSerializer(
                page, many=True, context={'request': request}
            )
            return pagination.get_paginated_response(serializer.data)

        serializer = LineRentalListSerializer(
            queryset, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': queryset.count()},
        )

class LineRentalDetailView(APIView, StandardResponseMixin):
    """جزئیات آگهی اجاره لاین"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: LineRentalDetailSerializer},
        tags=['Ads'],
        summary='جزئیات آگهی اجاره لاین',
    )
    def get(self, request, pk):
        line_rental = get_object_or_404(
            LineRental.objects.select_related(
                'business', 'service_category', 'sub_service',
            ),
            id=pk,
            business__status='approved',
            business__is_active=True,
        )
        serializer = LineRentalDetailSerializer(
            line_rental, context={'request': request}
        )
        return self.success_response(data=serializer.data)


class BusinessLineRentalCreateView(APIView, StandardResponseMixin):
    """ایجاد آگهی اجاره لاین"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        request=LineRentalCreateSerializer,
        responses={201: LineRentalDetailSerializer},
        tags=['Ads'],
        summary='ایجاد آگهی اجاره لاین',
    )
    def post(self, request):
        serializer = LineRentalCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            line_rental = serializer.save()
            return self.success_response(
                data=LineRentalDetailSerializer(
                    line_rental, context={'request': request}
                ).data,
                message='آگهی اجاره لاین ایجاد شد',
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Create line rental error: {e}", exc_info=True)  # ✅ exc_info اضافه شد
            return self.error_response(
                message='خطا در ایجاد آگهی',
                code='CREATE_ERROR',
            )


class BusinessLineRentalListView(APIView, StandardResponseMixin):
    """لیست آگهی‌های اجاره لاین من"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Ads'],
        summary='آگهی‌های اجاره لاین من',
    )
    def get(self, request):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        rentals = LineRental.objects.filter(
            business=business,
        ).select_related(
            'service_category', 'sub_service',
        ).order_by('-created_at')

        serializer = LineRentalListSerializer(
            rentals, many=True, context={'request': request}
        )
        return self.success_response(
            data=serializer.data,
            meta={'count': rentals.count()},
        )


class BusinessLineRentalDeleteView(APIView, StandardResponseMixin):
    """حذف آگهی اجاره لاین"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Ads'],
        summary='حذف آگهی اجاره لاین',
    )
    def delete(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()

        try:
            line_rental = LineRental.objects.get(id=pk, business=business)
            line_rental.delete()
            return self.success_response(message='آگهی حذف شد')
        except LineRental.DoesNotExist:
            return self.error_response(
                message='آگهی یافت نشد',
                code='LINE_RENTAL_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )


class BusinessModelRequestUpdateView(APIView, StandardResponseMixin):
    """ویرایش درخواست مدل"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @extend_schema(
        request=ModelRequestUpdateSerializer,
        responses={200: ModelRequestDetailSerializer},
        tags=['Ads'],
        summary='ویرایش درخواست مدل',
    )
    def put(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        
        try:
            model_request = ModelRequest.objects.get(id=pk, business=business)
        except ModelRequest.DoesNotExist:
            return self.error_response(
                message='درخواست مدل یافت نشد',
                code='MODEL_REQUEST_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = ModelRequestUpdateSerializer(
            model_request,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            updated = serializer.save()
            return self.success_response(
                data=ModelRequestDetailSerializer(
                    updated, context={'request': request}
                ).data,
                message='درخواست مدل با موفقیت ویرایش شد',
            )
        except Exception as e:
            logger.error(f"Update model request error: {e}")
            return self.error_response(
                message='خطا در ویرایش درخواست',
                code='UPDATE_ERROR',
            )


class BusinessLineRentalUpdateView(APIView, StandardResponseMixin):
    """ویرایش آگهی اجاره لاین"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @extend_schema(
        request=LineRentalUpdateSerializer,
        responses={200: LineRentalDetailSerializer},
        tags=['Ads'],
        summary='ویرایش آگهی اجاره لاین',
    )
    def put(self, request, pk):
        business = request.user.businesses.filter(
            is_active=True, status='approved'
        ).first()
        
        try:
            line_rental = LineRental.objects.get(id=pk, business=business)
        except LineRental.DoesNotExist:
            return self.error_response(
                message='آگهی اجاره لاین یافت نشد',
                code='LINE_RENTAL_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = LineRentalUpdateSerializer(
            line_rental,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            updated = serializer.save()
            return self.success_response(
                data=LineRentalDetailSerializer(
                    updated, context={'request': request}
                ).data,
                message='آگهی اجاره لاین با موفقیت ویرایش شد',
            )
        except Exception as e:
            logger.error(f"Update line rental error: {e}")
            return self.error_response(
                message='خطا در ویرایش آگهی',
                code='UPDATE_ERROR',
            )