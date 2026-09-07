from django.urls import path
from .views import (
    CreateReviewView,
    BusinessReviewsView,
    UserReviewsView,
    CanReviewCheckView,
    BusinessReviewReplyView,
    PendingReviewsView,
    BusinessTagVotesView,
    ToggleTagVoteView,
)

app_name = 'reviews'

urlpatterns = [
    path('create/', CreateReviewView.as_view(), name='create-review'),
    path('business/<int:business_id>/', BusinessReviewsView.as_view(), name='business-reviews'),
    path('my-reviews/', UserReviewsView.as_view(), name='my-reviews'),
    path('can-review/<int:appointment_id>/', CanReviewCheckView.as_view(), name='can-review'),
    path('reply/', BusinessReviewReplyView.as_view(), name='create-reply'),
    path('pending/', PendingReviewsView.as_view(), name='pending-reviews'),
    # ✅ جدید: لایک/دیسلایک تگ‌ها
    path('tag-votes/<int:business_id>/', BusinessTagVotesView.as_view(), name='tag-votes'),
    path('tag-vote/', ToggleTagVoteView.as_view(), name='toggle-tag-vote'),
]