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

class PendingReviewsView(APIView, StandardResponseMixin):
    """لیست نوبت‌های آماده نظردهی (۶ ساعت بعد از نوبت)"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Reviews'],
        summary='نوبت‌های آماده نظردهی',
    )
    def get(self, request):
        from apps.appointments.models import Appointment
        from apps.appointments.serializers import AppointmentListSerializer
        import jdatetime
        from datetime import datetime, timedelta
        from django.utils import timezone as django_timezone
        
        # نوبت‌های انجام شده کاربر
        appointments = Appointment.objects.filter(
            customer=request.user,
            status=Appointment.Status.DONE,
            has_review=False,
        ).select_related('business', 'service').order_by('-created_at')
        
        pending_reviews = []
        now = django_timezone.now().replace(tzinfo=None)
        
        for apt in appointments:
            try:
                # تبدیل تاریخ جلالی به میلادی
                gregorian_date = jdatetime.date(
                    apt.jy, apt.jm, apt.jd
                ).togregorian()
                
                # ترکیب تاریخ و ساعت
                apt_datetime = datetime.combine(gregorian_date, apt.time_slot)
                
                # اضافه کردن ۶ ساعت
                review_available_time = apt_datetime + timedelta(hours=6)
                
                # بررسی آیا ۶ ساعت گذشته است
                if now >= review_available_time:
                    pending_reviews.append(apt)
            except Exception:
                continue
        
        serializer = AppointmentListSerializer(
            pending_reviews, many=True, context={'request': request}
        )
        
        return self.success_response(
            data=serializer.data,
            meta={'count': len(pending_reviews)},
        )


class BusinessTagVotesView(APIView, StandardResponseMixin):
    """دریافت تعداد لایک/دیسلایک تگ‌های یک کسب‌وکار"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Reviews'],
        summary='تعداد لایک/دیسلایک تگ‌ها',
    )
    def get(self, request, business_id):
        from apps.reviews.models import ReviewTagVote
        from django.db.models import Count, Q

        # تمام نظرات این کسب‌وکار
        review_ids = Review.objects.filter(
            business_id=business_id,
        ).values_list('id', flat=True)

        # شمارش تگ‌ها از نظرات (تعداد دفعاتی که هر تگ انتخاب شده)
        tag_select_counts = {}
        reviews = Review.objects.filter(business_id=business_id)
        for review in reviews:
            for tag in (review.tags or []):
                tag_select_counts[tag] = tag_select_counts.get(tag, 0) + 1

        # شمارش لایک/دیسلایک از ReviewTagVote
        votes = ReviewTagVote.objects.filter(
            review_id__in=review_ids,
        ).values('tag_id').annotate(
            likes=Count('id', filter=Q(vote_type='like')),
            dislikes=Count('id', filter=Q(vote_type='dislike')),
        )

        vote_map = {}
        for v in votes:
            vote_map[v['tag_id']] = {
                'likes': v['likes'],
                'dislikes': v['dislikes'],
            }

        # ساخت پاسخ نهایی
        all_tags = [
            'clean', 'punctual', 'quality', 'polite', 'fair_price', 'recommend'
        ]

        result = {}
        for tag_id in all_tags:
            result[tag_id] = {
                'selected_count': tag_select_counts.get(tag_id, 0),
                'likes': vote_map.get(tag_id, {}).get('likes', 0),
                'dislikes': vote_map.get(tag_id, {}).get('dislikes', 0),
            }

        # رای فعلی کاربر (اگر لاگین باشد)
        user_votes = {}
        if request.user.is_authenticated:
            my_votes = ReviewTagVote.objects.filter(
                review_id__in=review_ids,
                user=request.user,
            ).values('tag_id', 'vote_type')
            for mv in my_votes:
                user_votes[mv['tag_id']] = mv['vote_type']

        return self.success_response(
            data={
                'tag_stats': result,
                'user_votes': user_votes,
            },
        )


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

        # پیدا کردن یک نظر از این کسب‌وکار که این تگ را داشته باشد
        review = Review.objects.filter(
            business_id=business_id,
            tags__contains=[tag_id],
        ).first()

        if not review:
            # اگر هیچ نظری این تگ را نداشت، اولین نظر کسب‌وکار
            review = Review.objects.filter(
                business_id=business_id,
            ).first()

        if not review:
            return self.error_response(
                message='نظری برای این کسب‌وکار یافت نشد',
                code='NO_REVIEWS',
            )

        # بررسی رای قبلی
        existing_vote = ReviewTagVote.objects.filter(
            review=review,
            tag_id=tag_id,
            user=request.user,
        ).first()

        if existing_vote:
            if existing_vote.vote_type == vote_type:
                # همان رای → حذف (toggle off)
                existing_vote.delete()
                return self.success_response(
                    data={'action': 'removed', 'vote_type': None},
                    message='رای حذف شد',
                )
            else:
                # رای مخالف → تغییر
                existing_vote.vote_type = vote_type
                existing_vote.save(update_fields=['vote_type'])
                return self.success_response(
                    data={'action': 'changed', 'vote_type': vote_type},
                    message='رای تغییر کرد',
                )
        else:
            # رای جدید
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