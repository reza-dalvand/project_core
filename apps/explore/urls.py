from django.urls import path
from .views import (
    ExplorePostListView,
    ExplorePostDetailView,
    BusinessPostCreateView,
    BusinessPostListView,
    BusinessPostUpdateView,
    BusinessPostDeleteView,
)

app_name = 'explore'

urlpatterns = [
    # Public
    path('posts/', ExplorePostListView.as_view(), name='post-list'),
    path('posts/<int:pk>/', ExplorePostDetailView.as_view(), name='post-detail'),
    
    # Business
    path('my-posts/', BusinessPostListView.as_view(), name='my-post-list'),
    path('my-posts/create/', BusinessPostCreateView.as_view(), name='post-create'),
    path('my-posts/<int:pk>/update/', BusinessPostUpdateView.as_view(), name='post-update'),
    path('my-posts/<int:pk>/delete/', BusinessPostDeleteView.as_view(), name='post-delete'),
]