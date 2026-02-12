from django.urls import path

from . import views

urlpatterns = [
    path('', views.comparison_list, name='comparison-list'),
    path('add/', views.add_comparison, name='comparison-add'),
    path('<slug:slug>/', views.comparison_detail, name='comparison-detail'),
]
