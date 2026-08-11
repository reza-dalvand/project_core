"""
Views برای نظرات و امتیازات
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsCustomer, IsApprovedBusinessOwner
from apps.core.pagination import StandardResultsSetPagination
from apps.reviews.models import Review, ReviewTag
from apps.businesses.models import Business
from apps.reviews.serializers.review import (
    ReviewListSerializer,
    ReviewDetailSerializer,
    CreateReviewSerializer,
    CreateReviewResponseSerializer,
    UpdateReviewResponseSerializer,
    ReviewTagSerializer,
    ReviewStatsSerializer,
    ReviewFilterSerializer,
)
from apps.reviews.services.review_service import (
    ReviewService,
    ReviewException,
)


class ReviewTagListView(APIView, StandardResponseMixin):
    """
    لیست تگ‌های آماده برای نظرات

    GET /api/v1/reviews/tags/
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=ReviewTagSerializer(many=True),
        tags=['Reviews'],
        summary='لیست تگ‌های نظر',
        description='دریافت لیست تگ‌های آماده برای استفاده در نظرات',
    )
    def get(self, request):
        tags = ReviewTag.objects.filter(is_active=True).order_by('order')
        serializer = ReviewTagSerializer(tags, many=True)

        return self.success_response(
            data=serializer.data,
            meta={'count': tags.count()},
        )


class CreateReviewView(APIView, StandardResponseMixin):
    """
    ثبت نظر جدید

    POST /api/v1/reviews/create/
    """
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        request=CreateReviewSerializer,
        responses=ReviewDetailSerializer,
        tags=['Reviews'],
        summary='ثبت نظر',
        description='ثبت نظر و امتیاز برای نوبت انجام‌شده',
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
                tag_ids=serializer.validated_data.get('tag_ids', []),
            )

            return self.success_response(
                data=ReviewDetailSerializer(review).data,
                message='نظر شما با موفقیت ثبت شد',
                status=status.HTTP_201_CREATED,
            )

        except ReviewException as e:
            return e.as_response()


class BusinessReviewsView(ListAPIView, StandardResponseMixin):
    """
    لیست نظرات یک کسب‌وکار

    GET /api/v1/reviews/business/<business_id>/?rating=5&page=1
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewListSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='rating',
                type=int,
                required=False,
                description='فیلتر بر اساس امتیاز (۱ تا ۵)',
            ),
        ],
        tags=['Reviews'],
        summary='نظرات کسب‌وکار',
        description='دریافت لیست نظرات یک کسب‌وکار با pagination',
    )
    def get(self, request, business_id, *args, **kwargs):
        # دریافت کسب‌وکار
        try:
            business = Business.objects.get(id=business_id)
        except Business.DoesNotExist:
            return self.error_response(
                message='کسب‌وکار مورد نظر یافت نشد',
                code='BUSINESS_NOT_FOUND',
                status=status.HTTP_404_NOT_FOUND,
            )

        # دریافت پارامترها
        rating_filter = request.query_params.get('rating')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        # اعتبارسنجی
        if rating_filter:
            try:
                rating_filter = int(rating_filter)
                if not (1 <= rating_filter <= 5):
                    raise ValueError()
            except ValueError:
                return self.error_response(
                    message='امتیاز باید بین ۱ تا ۵ باشد',
                    code='INVALID_RATING',
                )

        # دریافت نظرات
        result = ReviewService.get_business_reviews(
            business=business,
            page=page,
            page_size=page_size,
            rating_filter=rating_filter,
        )

        # Serialize نظرات
        reviews_data = ReviewListSerializer(
            result['reviews'],
            many=True,
            context={'request': request},
        ).data

        return self.success_response(
            data=reviews_data,
            meta={
                'total': result['total'],
                'page': result['page'],
                'page_size': result['page_size'],
                'avg_rating': result['avg_rating'],
                'rating_distribution': result['rating_distribution'],
            },
        )


class UserReviewsView(ListAPIView, StandardResponseMixin):
    """
    لیست نظرات ثبت‌شده توسط کاربر

    GET /api/v1/reviews/my-reviews/?page=1
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewDetailSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=['Reviews'],
        summary='نظرات من',
        description='دریافت لیست نظراتی که کاربر ثبت کرده است',
    )
    def get(self, request, *args, **kwargs):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        # دریافت نظرات کاربر
        result = ReviewService.get_user_reviews(
            user=request.user,
            page=page,
            page_size=page_size,
        )

        # Serialize نظرات
        reviews_data = ReviewDetailSerializer(
            result['reviews'],
            many=True,
            context={'request': request},
        ).data

        return self.success_response(
            data=reviews_data,
            meta={
                'total': result['total'],
                'page': result['page'],
                'page_size': result['page_size'],
            },
        )


class CanReviewCheckView(APIView, StandardResponseMixin):
    """
    بررسی اینکه آیا کاربر می‌تواند برای یک نوبت نظر بدهد

    GET /api/v1/reviews/can-review/<appointment_id>/
    """
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        tags=['Reviews'],
        summary='بررسی امکان ثبت نظر',
        description='بررسی اینکه آیا کاربر می‌تواند برای این نوبت نظر ثبت کند',
    )
    def get(self, request, appointment_id):
        from apps.bookings.models import Appointment

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
            data={
                'can_review': can_review,
                'appointment_id': appointment_id,
            },
        )


class BusinessReviewResponseView(APIView, StandardResponseMixin):
    """
    مدیریت پاسخ کسب‌وکار به نظرات

    POST /api/v1/reviews/response/ - ایجاد پاسخ
    PUT /api/v1/reviews/response/<review_id>/ - ویرایش پاسخ
    DELETE /api/v1/reviews/response/<review_id>/ - حذف پاسخ
    """
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]

    @extend_schema(
        request=CreateReviewResponseSerializer,
        responses=ReviewDetailSerializer,
        tags=['Reviews - Business'],
        summary='ثبت پاسخ به نظر',
        description='ثبت پاسخ کسب‌وکار به یک نظر',
    )
    def post(self, request):
        serializer = CreateReviewResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            response = ReviewService.create_business_response(
                business=request.user.business,
                review_id=serializer.validated_data['review_id'],
                text=serializer.validated_data['text'],
            )

            # دریافت نظر بروزرسانی‌شده
            review = response.review

            return self.success_response(
                data=ReviewDetailSerializer(review).data,
                message='پاسخ شما با موفقیت ثبت شد',
                status=status.HTTP_201_CREATED,
            )

        except ReviewException as e:
            return e.as_response()

    @extend_schema(
        request=UpdateReviewResponseSerializer,
        responses=ReviewDetailSerializer,
        tags=['Reviews - Business'],
        summary='ویرایش پاسخ',
        description='ویرایش پاسخ کسب‌وکار به یک نظر',
    )
    def put(self, request, review_id):
        serializer = UpdateReviewResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            response = ReviewService.update_business_response(
                business=request.user.business,
                review_id=review_id,
                text=serializer.validated_data['text'],
            )

            # دریافت نظر بروزرسانی‌شده
            review = response.review

            return self.success_response(
                data=ReviewDetailSerializer(review).data,
                message='پاسخ شما با موفقیت ویرایش شد',
            )

        except ReviewException as e:
            return e.as_response()

    @extend_schema(
        tags=['Reviews - Business'],
        summary='حذف پاسخ',
        description='حذف پاسخ کسب‌وکار به یک نظر',
    )
    def delete(self, request, review_id):
        try:
            ReviewService.delete_business_response(
                business=request.user.business,
                review_id=review_id,
            )

            return self.success_response(
                message='پاسخ شما با موفقیت حذف شد',
            )

        except ReviewException as e:
            return e.as_response()


class BusinessReviewsManagementView(ListAPIView, StandardResponseMixin):
    """
    مدیریت نظرات کسب‌وکار (برای صاحب کسب‌وکار)

    GET /api/v1/reviews/business-management/?rating=5&page=1
    """
    permission_classes = [IsAuthenticated, IsApprovedBusinessOwner]
    serializer_class = ReviewDetailSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='rating',
                type=int,
                required=False,
                description='فیلتر بر اساس امتیاز (۱ تا ۵)',
            ),
        ],
        tags=['Reviews - Business'],
        summary='مدیریت نظرات',
        description='دریافت لیست نظرات کسب‌وکار برای مدیریت و پاسخ‌دهی',
    )
    def get(self, request, *args, **kwargs):
        business = request.user.business

        # دریافت پارامترها
        rating_filter = request.query_params.get('rating')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        # اعتبارسنجی
        if rating_filter:
            try:
                rating_filter = int(rating_filter)
                if not (1 <= rating_filter <= 5):
                    raise ValueError()
            except ValueError:
                return self.error_response(
                    message='امتیاز باید بین ۱ تا ۵ باشد',
                    code='INVALID_RATING',
                )

        # دریافت نظرات
        result = ReviewService.get_business_reviews(
            business=business,
            page=page,
            page_size=page_size,
            rating_filter=rating_filter,
        )

        # Serialize نظرات
        reviews_data = ReviewDetailSerializer(
            result['reviews'],
            many=True,
            context={'request': request},
        ).data

        return self.success_response(
            data=reviews_data,
            meta={
                'total': result['total'],
                'page': result['page'],
                'page_size': result['page_size'],
                'avg_rating': result['avg_rating'],
                'rating_distribution': result['rating_distribution'],
            },
        )