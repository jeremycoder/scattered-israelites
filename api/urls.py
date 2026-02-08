from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LexemeViewSet

router = DefaultRouter()
router.register(r'lexemes', LexemeViewSet, basename='lexeme')

urlpatterns = [
    path('', include(router.urls)),
]
