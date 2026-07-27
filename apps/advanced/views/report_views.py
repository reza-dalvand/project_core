"""
Views گزارشات
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.advanced.services.report_service import ReportService
from apps.advanced.serializers import (
    ReportRequestSerializer,
    ReportSerializer,
)
from apps.advanced.models import Report


class ReportCreateView(APIView, StandardResponseMixin):
    """ایجاد گزارش"""

    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        request=ReportRequestSerializer,
        responses=ReportSerializer,
        tags=['Reports'],
        summary='ایجاد گزارش',
        description='تولید گزارش از تراکنش‌ها، نوبت‌ها یا نظرات',
    )
    def post(self, request):
        serializer = ReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        filters = {
            k: v for k, v in serializer.validated_data.items()
            if k not in ['report_type', 'format']
        }

        report = ReportService.create_report(
            user=request.user,
            report_type=serializer.validated_data['report_type'],
            format_type=serializer.validated_data['format'],
            filters=filters,
        )

        if report.is_ready:
            return self.success_response(
                data=ReportSerializer(
                    report, context={'request': request}
                ).data,
                message='گزارش با موفقیت تولید شد',
            )
        else:
            return self.error_response(
                message=f'خطا در تولید گزارش: {report.error_message}',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReportListView(APIView, StandardResponseMixin):
    """لیست گزارشات"""

    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        responses=ReportSerializer(many=True),
        tags=['Reports'],
        summary='لیست گزارشات',
    )
    def get(self, request):
        reports = Report.objects.filter(
            user=request.user,
            is_ready=True,
        ).order_by('-created_at')[:20]

        return self.success_response(
            data=ReportSerializer(
                reports, many=True, context={'request': request}
            ).data
        )


class ReportDeleteView(APIView, StandardResponseMixin):
    """حذف گزارش"""

    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        tags=['Reports'],
        summary='حذف گزارش',
    )
    def delete(self, request, pk):
        deleted_count, _ = Report.objects.filter(
            id=pk,
            user=request.user,
        ).delete()

        if deleted_count:
            return self.success_response(message='گزارش حذف شد')

        return self.error_response(
            message='گزارش یافت نشد',
            status=status.HTTP_404_NOT_FOUND,
        )