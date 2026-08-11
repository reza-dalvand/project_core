"""
Views برای مدیریت کارمندان
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404

from apps.businesses.models import Employee
from apps.businesses.serializers.employee import (
    EmployeeListSerializer,
    EmployeeDetailSerializer,
    EmployeeCreateSerializer,
    EmployeeUpdateSerializer,
)
from apps.core.permissions import IsApprovedBusinessOwner, IsBusinessOwnerOfObject
from apps.core.pagination import StandardResultsSetPagination
from django_filters.rest_framework import DjangoFilterBackend


class EmployeeListView(generics.ListCreateAPIView):
    """
    لیست و ایجاد کارمندان

    GET: دریافت لیست کارمندان
    POST: ایجاد کارمند جدید
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EmployeeCreateSerializer
        return EmployeeListSerializer

    def get_queryset(self):
        """دریافت کارمندان کسب‌وکار فعلی"""
        return Employee.objects.filter(
            business=self.request.user.business
        ).prefetch_related('services').order_by('order', 'name')

    @extend_schema(
        summary='لیست کارمندان',
        description='دریافت لیست تمام کارمندان کسب‌وکار شما',
        parameters=[
            OpenApiParameter(
                name='is_active',
                type=bool,
                description='فیلتر بر اساس وضعیت فعال/غیرفعال',
                required=False,
            ),
        ],
        responses={200: EmployeeListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='ایجاد کارمند جدید',
        description='ایجاد یک کارمند جدید برای کسب‌وکار شما',
        request=EmployeeCreateSerializer,
        responses={201: EmployeeDetailSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    جزئیات، بروزرسانی و حذف کارمند

    GET: دریافت جزئیات کارمند
    PUT/PATCH: بروزرسانی کارمند
    DELETE: حذف کارمند
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner, IsBusinessOwnerOfObject]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'pk'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return EmployeeUpdateSerializer
        return EmployeeDetailSerializer

    def get_queryset(self):
        """دریافت کارمندان کسب‌وکار فعلی"""
        return Employee.objects.filter(
            business=self.request.user.business
        ).prefetch_related('services')

    @extend_schema(
        summary='جزئیات کارمند',
        description='دریافت جزئیات کامل یک کارمند',
        responses={200: EmployeeDetailSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی کارمند',
        description='بروزرسانی اطلاعات یک کارمند',
        request=EmployeeUpdateSerializer,
        responses={200: EmployeeDetailSerializer}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='بروزرسانی جزئی کارمند',
        description='بروزرسانی بخشی از اطلاعات یک کارمند',
        request=EmployeeUpdateSerializer,
        responses={200: EmployeeDetailSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary='حذف کارمند',
        description='حذف یک کارمند از کسب‌وکار',
        responses={204: None}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class EmployeeToggleActiveView(APIView):
    """
    تغییر وضعیت فعال/غیرفعال کارمند
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        summary='تغییر وضعیت کارمند',
        description='فعال یا غیرفعال کردن یک کارمند',
        responses={200: EmployeeDetailSerializer}
    )
    def post(self, request, pk):
        employee = get_object_or_404(
            Employee,
            pk=pk,
            business=request.user.business
        )

        employee.is_active = not employee.is_active
        employee.save()

        serializer = EmployeeDetailSerializer(employee, context={'request': request})
        return Response({
            'success': True,
            'message': f'کارمند {employee.name} {"فعال" if employee.is_active else "غیرفعال"} شد',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class EmployeeAssignServicesView(APIView):
    """
    اختصاص خدمات به کارمند
    """
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        summary='اختصاص خدمات به کارمند',
        description='اختصاص یا حذف خدمات از یک کارمند',
        request={
            'type': 'object',
            'properties': {
                'service_ids': {
                    'type': 'array',
                    'items': {'type': 'integer'},
                    'description': 'لیست شناسه‌های خدمات'
                }
            },
            'required': ['service_ids']
        },
        responses={200: EmployeeDetailSerializer}
    )
    def post(self, request, pk):
        employee = get_object_or_404(
            Employee,
            pk=pk,
            business=request.user.business
        )

        service_ids = request.data.get('service_ids', [])

        # اعتبارسنجی خدمات
        from apps.businesses.models import Service
        services = Service.objects.filter(
            id__in=service_ids,
            business=request.user.business
        )

        if len(services) != len(service_ids):
            return Response({
                'success': False,
                'message': 'برخی از خدمات نامعتبر هستند یا متعلق به کسب‌وکار شما نیستند'
            }, status=status.HTTP_400_BAD_REQUEST)

        # اختصاص خدمات
        employee.services.set(services)

        serializer = EmployeeDetailSerializer(employee, context={'request': request})
        return Response({
            'success': True,
            'message': f'{len(services)} خدمت به {employee.name} اختصاص یافت',
            'data': serializer.data
        }, status=status.HTTP_200_OK)