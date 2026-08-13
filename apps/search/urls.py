from django.urls import path
from .views import GlobalSearchView, SearchSuggestionsView, SearchHistoryView 

app_name = 'search'

urlpatterns = [
    path('', GlobalSearchView.as_view(), name='global-search'),
    path('suggestions/', SearchSuggestionsView.as_view(), name='suggestions'),
    path('history/', SearchHistoryView.as_view(), name='search-history'),
]