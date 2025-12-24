"""
URL configuration for project_self project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # API 문서화 (Swagger/OpenAPI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Django Admin
    path(
        'admin/analytics/',
        RedirectView.as_view(
            url=f"{settings.FRONTEND_ORIGIN}/admin/analytics",
            permanent=False
        ),
        name='admin-analytics-redirect'
    ),
    path('admin/', admin.site.urls),
    # 인증 모듈 (기본 auth + users 경로)
    path('', include('authentication.urls', namespace='authentication')),
    path('api/', include('products.urls')),
    path('api/sellers/', include('sellers.urls')),
    path('api/orders/', include('orders.urls')),
    # 추천 API (REC-005)
    path('api/recommendations/', include('products.recommendations_urls')),
]
