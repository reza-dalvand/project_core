"""
Views برای نظرات — ساده‌سازی شده
"""
import logging
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from django.utils import timezone  
from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.reviews.models import Review
from apps.reviews.serializers import (
    ReviewListSerializer,
    ReviewDetailSerializer,
    CreateReviewSerializer,
    CreateReviewReplySerializer,
)
from apps.reviews.services.review_service import ReviewService, ReviewException

logger = logging.getLogger(__name__)


class CreateReviewView(APIView, StandardResponseMixin):
    """ثبت نظر جدید"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=CreateReviewSerializer,
        responses=ReviewDetailSerializer,
        tags=['Reviews'],
        summary='ثبت نظر',
    )
    def post(self, request):
        serializer = CreateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            review = ReviewService.create_review(
                customer=request.user,
                appointment_id=serializer.validated_data['appointment_id'],
                rating=serializer.validated_data['rating'],
                comment=serializer.validated_data.get('comment', ''),
                tags=serializer.validated_data.get('tags', []),
            )

            return self.success_response(
                data=ReviewDetailSerializer(review).data,
                message='نظر شما با موفقیت ثبت شد',
                status=status.HTTP_201_CREATED,
            )
        except ReviewException as e:
            return e.as_response()


class BusinessReviewsView(generics.ListAPIView, StandardResponseMixin):
    """لیست نظرات یک کسب‌وکار"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ReviewListSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Reviews'],
        summary='نظرات کسب‌وکار',
    )
    def get_queryset(self):
        business_id = self.kwargs.get('business_id')
        return Review.objects.filter(
            business_id=business_id,
        ).select_related('customer', 'service').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # محاسبه میانگین امتیاز
        from django.db.models import Avg
        avg_rating = queryset.aggregate(avg=Avg('rating'))['avg'] or 0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['avg_rating'] = float(avg_rating)
            return response

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            data=serializer.data,
            meta={'avg_rating': float(avg_rating)},
        )


class UserReviewsView(generics.ListAPIView, StandardResponseMixin):
    """لیست نظرات ثبت‌شده توسط کاربر"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReviewDetailSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Reviews'],
        summary='نظرات من',
    )
    def get_queryset(self):
        return Review.objects.filter(
            customer=self.request.user,
        ).select_related('business', 'service').order_by('-created_at')


class CanReviewCheckView(APIView, StandardResponseMixin):
    """بررسی امکان ثبت نظر"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Reviews'],
        summary='بررسی امکان ثبت نظر',
    )
    def get(self, request, appointment_id):
        from apps.appointments.models import Appointment

        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return self.error_response(
                message='نوبت مورد نظر یافت نشد',
                code='APPOINTMENT_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        can_review = ReviewService.can_review(request.user, appointment)
        return self.success_response(
            data={'can_review': can_review},
        )


class BusinessReviewReplyView(APIView, StandardResponseMixin):
    """ثبت پاسخ کسب‌وکار به نظر"""
    permission_classes = [permissions.IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        request=CreateReviewReplySerializer,
        tags=['Reviews - Business'],
        summary='ثبت پاسخ به نظر',
    )
    def post(self, request):
        serializer = CreateReviewReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            business = request.user.businesses.filter(
                is_active=True, status='approved'
            ).first()

            review = Review.objects.get(
                id=serializer.validated_data['review_id'],
                business=business,
            )

            if review.reply:
                return self.error_response(
                    message='شما قبلاً به این نظر پاسخ داده‌اید',
                    code='REPLY_ALREADY_EXISTS',
                )

            review.reply = serializer.validated_data['reply']
            review.replied_at = timezone.now()
            review.save(update_fields=['reply', 'replied_at'])

            return self.success_response(
                data=ReviewDetailSerializer(review).data,
                message='پاسخ شما با موفقیت ثبت شد',
                status=status.HTTP_201_CREATED,
            )
        except Review.DoesNotExist:
            return self.error_response(
                message='نظر مورد نظر یافت نشد',
                code='REVIEW_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return self.error_response(
                message=str(e),
                code='REPLY_ERROR',
            )