from django.urls import path

from . import views

urlpatterns = [
    path('', views.comparison_list, name='comparison-list'),
    path('<slug:slug>/', views.comparison_detail, name='comparison-detail'),
]
