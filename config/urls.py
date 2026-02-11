from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('bible/', include('reader.urls')),
    path('niger-congo/', include('comparisons.urls')),
]
