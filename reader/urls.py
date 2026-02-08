from django.urls import path

from . import views

urlpatterns = [
    path('', views.book_list, name='book-list'),
    path('htmx/word/<int:pk>/', views.word_detail_partial, name='word-detail-partial'),
    path('htmx/<str:osis_id>/<int:chapter>/', views.verse_list_partial, name='verse-list-partial'),
    path('<str:osis_id>/', views.chapter_list, name='chapter-list'),
    path('<str:osis_id>/<int:chapter>/', views.chapter_view, name='chapter-view'),
]
