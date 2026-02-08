from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookChaptersView,
    BookViewSet,
    ChapterVersesView,
    ExportBookCSVView,
    ExportBookJSONView,
    LexemeViewSet,
    WordDetailView,
)

router = DefaultRouter()
router.register(r'lexemes', LexemeViewSet, basename='lexeme')
router.register(r'books', BookViewSet, basename='book')

urlpatterns = [
    path('', include(router.urls)),
    path('books/<str:osis_id>/chapters/', BookChaptersView.as_view(), name='api-book-chapters'),
    path('books/<str:osis_id>/chapters/<int:chapter>/', ChapterVersesView.as_view(), name='api-chapter-verses'),
    path('words/<int:pk>/', WordDetailView.as_view(), name='api-word-detail'),
    path('export/<str:osis_id>.json', ExportBookJSONView.as_view(), name='api-export-json'),
    path('export/<str:osis_id>.csv', ExportBookCSVView.as_view(), name='api-export-csv'),
]
