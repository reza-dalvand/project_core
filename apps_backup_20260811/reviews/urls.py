"""
URL configuration for reviews app
"""
from django.urls import path
from .views.review import (
    ReviewTagListView,
    CreateReviewView,
    BusinessReviewsView,
    UserReviewsView,
    CanReviewCheckView,
    BusinessReviewResponseView,
    BusinessReviewsManagementView,
)

app_name = 'reviews'

urlpatterns = [
    # ═══════════ Public Endpoints ═══════════
    path('tags/', ReviewTagListView.as_view(), name='review-tags'),
    path('create/', CreateReviewView.as_view(), name='create-review'),
    path('business/<int:business_id>/', BusinessReviewsView.as_view(), name='business-reviews'),
    path('my-reviews/', UserReviewsView.as_view(), name='my-reviews'),
    path('can-review/<int:appointment_id>/', CanReviewCheckView.as_view(), name='can-review'),

    # ═══════════ Business Endpoints ═══════════
    path('response/', BusinessReviewResponseView.as_view(), name='create-response'),
    path('response/<int:review_id>/', BusinessReviewResponseView.as_view(), name='manage-response'),
    path('business-management/', BusinessReviewsManagementView.as_view(), name='business-management'),
]