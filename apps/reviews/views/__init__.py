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
                comment=serializer.validated_data.get('comment', ''),
                tag_votes=serializer.validated_data.get('tag_votes', []), 
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
        request=CreateReviewSerializer,
        tags=['Reviews - Business'],
        summary='ثبت پاسخ به نظر',
    )
    def post(self, request):
        serializer = CreateReviewSerializer(data=request.data)
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


class PendingReviewsView(APIView, StandardResponseMixin):
    """
    لیست نوبت‌های آماده نظردهی
    منطق جدید:
    - برای هر کسب‌وکار که کاربر نظر نداده، آخرین نوبت DONE را برمی‌گرداند
    - اگر کاربر برای کسب‌وکار نظر داده باشد، هیچ نوبتی از آن کسب‌وکار برگردانده نمی‌شود
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Reviews'],
        summary='نوبت‌های آماده نظردهی',
    )
    def get(self, request):
        from apps.appointments.models import Appointment
        from apps.appointments.serializers import AppointmentListSerializer
        from apps.reviews.models import Review
        from datetime import timedelta
        from django.utils import timezone as django_timezone

        # ✅ کسب‌وکارهایی که کاربر قبلاً برای آن‌ها نظر ثبت کرده
        reviewed_business_ids = Review.objects.filter(
            customer=request.user,
        ).values_list('business_id', flat=True)

        # ✅ نوبت‌های DONE کاربر که کسب‌وکارشان در لیست نظر داده‌شده‌ها نیست
        appointments = Appointment.objects.filter(
            customer=request.user,
            status=Appointment.Status.DONE,
            done_at__isnull=False,
        ).exclude(
            business_id__in=reviewed_business_ids,
        ).select_related('business', 'service').order_by('-done_at')

        now = django_timezone.now()
        pending_reviews = []
        added_business_ids = set()  # فقط آخرین نوبت برای هر کسب‌وکار

        for apt in appointments:
            # فقط آخرین نوبت DONE برای هر کسب‌وکار
            # (چون appointments مرتب شده بر اساس -done_at، اولین بار که می‌بینیم = آخرین)
            if apt.business_id in added_business_ids:
                continue

            review_available_time = apt.done_at + timedelta(hours=6)
            if now >= review_available_time:
                pending_reviews.append(apt)
                added_business_ids.add(apt.business_id)

        serializer = AppointmentListSerializer(
            pending_reviews, many=True, context={'request': request}
        )

        return self.success_response(
            data=serializer.data,
            meta={'count': len(pending_reviews)},
        )


    
class BusinessTagVotesView(APIView, StandardResponseMixin):
    """دریافت آمار تگ‌ها — فقط آخرین رای هر کاربر شمرده می‌شود (منطق ویرایش)"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, business_id):
        from apps.reviews.models import ReviewTagVote

        # دریافت تمام رای‌های این کسب‌وکار به ترتیب جدیدترین
        all_votes = ReviewTagVote.objects.filter(
            review__business_id=business_id
        ).select_related('review').order_by('-created_at')

        # ✅ استخراج آخرین رای هر کاربر برای هر تگ (جلوگیری از شمارش تکراری)
        user_latest_votes = {} # key: (user_id, tag_id), value: vote_type
        for vote in all_votes:
            key = (vote.user_id, vote.tag_id)
            if key not in user_latest_votes:
                user_latest_votes[key] = vote.vote_type

        all_tags = ['clean', 'punctual', 'quality', 'polite', 'fair_price', 'recommend']
        result = {tag: {'selected_count': 0, 'likes': 0, 'dislikes': 0} for tag in all_tags}

        # محاسبه آمار نهایی
        for (user_id, tag_id), vote_type in user_latest_votes.items():
            if tag_id in result:
                result[tag_id]['selected_count'] += 1
                if vote_type == 'like':
                    result[tag_id]['likes'] += 1
                else:
                    result[tag_id]['dislikes'] += 1

        # رای فعلی کاربر لاگین کرده (برای نمایش در مدال در صورت نیاز)
        user_votes = {}
        if request.user.is_authenticated:
            for (uid, tid), vtype in user_latest_votes.items():
                if uid == request.user.id:
                    user_votes[tid] = vtype

        return self.success_response(data={'tag_stats': result, 'user_votes': user_votes})

    
class ToggleTagVoteView(APIView, StandardResponseMixin):
    """ثبت/تغییر لایک یا دیسلایک تگ"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Reviews'],
        summary='ثبت لایک/دیسلایک تگ',
    )
    def post(self, request):
        from apps.reviews.models import ReviewTagVote

        business_id = request.data.get('business_id')
        tag_id = request.data.get('tag_id')
        vote_type = request.data.get('vote_type')  # 'like' | 'dislike'

        if not all([business_id, tag_id, vote_type]):
            return self.error_response(
                message='business_id, tag_id و vote_type الزامی هستند',
                code='MISSING_PARAMS',
            )

        if vote_type not in ('like', 'dislike'):
            return self.error_response(
                message='vote_type باید like یا dislike باشد',
                code='INVALID_VOTE_TYPE',
            )

        valid_tags = ['clean', 'punctual', 'quality', 'polite', 'fair_price', 'recommend']
        if tag_id not in valid_tags:
            return self.error_response(
                message='تگ نامعتبر است',
                code='INVALID_TAG',
            )

        # ✅ اصلاح باگ: پیدا کردن آخرین نظر خود کاربر برای این کسب‌وکار
        review = Review.objects.filter(
            business_id=business_id,
            customer=request.user,
        ).order_by('-created_at').first()

        if not review:
            return self.error_response(
                message='شما هنوز نظری برای این کسب‌وکار ثبت نکرده‌اید',
                code='NO_USER_REVIEW',
            )

        # بررسی رای قبلی
        existing_vote = ReviewTagVote.objects.filter(
            review=review,
            tag_id=tag_id,
            user=request.user,
        ).first()

        if existing_vote:
            if existing_vote.vote_type == vote_type:
                existing_vote.delete()
                return self.success_response(
                    data={'action': 'removed', 'vote_type': None},
                    message='رای حذف شد',
                )
            else:
                existing_vote.vote_type = vote_type
                existing_vote.save(update_fields=['vote_type'])
                return self.success_response(
                    data={'action': 'changed', 'vote_type': vote_type},
                    message='رای تغییر کرد',
                )
        else:
            ReviewTagVote.objects.create(
                review=review,
                tag_id=tag_id,
                vote_type=vote_type,
                user=request.user,
            )
            return self.success_response(
                data={'action': 'created', 'vote_type': vote_type},
                message='رای ثبت شد',
            )