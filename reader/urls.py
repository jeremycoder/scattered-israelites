from django.urls import path

from . import views

urlpatterns = [
    path('', views.book_list, name='book-list'),
    # HTMX partials (before slug routes to avoid ambiguity)
    path('htmx/word/<int:pk>/', views.word_detail_partial, name='word-detail-partial'),
    path('htmx/<slug:book_slug>/<int:chapter>/', views.verse_list_partial, name='verse-list-partial'),
    # Full pages
    path('<slug:book_slug>/', views.chapter_list, name='chapter-list'),
    path('<slug:book_slug>/<int:chapter>/', views.chapter_view, name='chapter-view'),
    path('<slug:book_slug>/<int:chapter>/<int:verse_num>/', views.verse_view, name='verse-view'),
    path('<slug:book_slug>/<int:chapter>/<int:verse_num>/<slug:word_slug>/', views.word_view, name='word-view'),
]
