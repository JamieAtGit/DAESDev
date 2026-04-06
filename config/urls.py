from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('marketplace.urls')),
    path('api/', include('marketplace.api_urls')),
]
