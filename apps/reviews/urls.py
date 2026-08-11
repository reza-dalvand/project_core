from django.urls import path
from .views import (
    CreateReviewView,
    BusinessReviewsView,
    UserReviewsView,
    CanReviewCheckView,
    BusinessReviewReplyView,
)

app_name = 'reviews'

urlpatterns = [
    # ═══════════ Public Endpoints ═══════════
    path('create/', CreateReviewView.as_view(), name='create-review'),
    path('business/<int:business_id>/', BusinessReviewsView.as_view(), name='business-reviews'),
    path('my-reviews/', UserReviewsView.as_view(), name='my-reviews'),
    path('can-review/<int:appointment_id>/', CanReviewCheckView.as_view(), name='can-review'),

    # ═══════════ Business Endpoints ═══════════
    path('reply/', BusinessReviewReplyView.as_view(), name='create-reply'),
]