from django.urls import path
from .views import GlobalSearchView, SearchSuggestionsView

app_name = 'search'

urlpatterns = [
    path('', GlobalSearchView.as_view(), name='global-search'),
    path('suggestions/', SearchSuggestionsView.as_view(), name='suggestions'),
]