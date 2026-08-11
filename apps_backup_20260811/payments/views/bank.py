"""
Views برای مدیریت حساب بانکی
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.payments.models import BankAccount
from apps.payments.serializers.bank import (
    BankAccountSerializer,
    BankAccountCreateSerializer,
    BankAccountUpdateSerializer,
)

logger = logging.getLogger(__name__)


class BankAccountView(APIView, StandardResponseMixin):
    """
    مدیریت حساب بانکی کسب‌وکار

    GET  /api/v1/payments/business/bank-account/   - دریافت
    POST /api/v1/payments/business/bank-account/   - ثبت جدید
    PUT  /api/v1/payments/business/bank-account/   - ویرایش
    """
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        responses={200: BankAccountSerializer},
        tags=['Bank Account'],
        summary='دریافت حساب بانکی',
    )
    def get(self, request):
        try:
            bank_account = BankAccount.objects.get(
                user=request.user,
                is_active=True,
            )
            serializer = BankAccountSerializer(bank_account)
            return self.success_response(data=serializer.data)
        except BankAccount.DoesNotExist:
            return self.success_response(
                data={
                    'is_registered': False,
                    'is_verified': False,
                },
                message='حساب بانکی ثبت نشده است',
            )

    @extend_schema(
        request=BankAccountCreateSerializer,
        responses={201: BankAccountSerializer},
        tags=['Bank Account'],
        summary='ثبت حساب بانکی',
    )
    def post(self, request):
        serializer = BankAccountCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        bank_account = serializer.save()

        return self.success_response(
            data=BankAccountSerializer(bank_account).data,
            message='حساب بانکی با موفقیت ثبت شد. در انتظار تایید کارشناسان.',
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=BankAccountUpdateSerializer,
        responses={200: BankAccountSerializer},
        tags=['Bank Account'],
        summary='ویرایش حساب بانکی',
    )
    def put(self, request):
        try:
            bank_account = BankAccount.objects.get(
                user=request.user,
                is_active=True,
            )
        except BankAccount.DoesNotExist:
            return self.error_response(
                message='حساب بانکی یافت نشد',
                code='BANK_ACCOUNT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BankAccountUpdateSerializer(
            bank_account,
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        updated = serializer.save()

        return self.success_response(
            data=BankAccountSerializer(updated).data,
            message='حساب بانکی بروزرسانی شد. مجدداً وارد چرخه تایید خواهد شد.',
        )