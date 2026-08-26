from django.urls import path
from .views import (
    FavoriteToggleView,
    FavoriteListView,
    FavoriteCountView,
)

app_name = 'favorites'

urlpatterns = [
    path('', FavoriteListView.as_view(), name='favorite-list'),
    path('toggle/', FavoriteToggleView.as_view(), name='favorite-toggle'),
    path('count/', FavoriteCountView.as_view(), name='favorite-count'),
]