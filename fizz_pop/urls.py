"""
URL configuration for fizz_pop project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('admin_panel/', include('admin_panel.urls')), 
    path('accounts/', include('allauth.urls')), 
    path('product/', include('product.urls')),
    path('category/', include('category.urls')),
    path('customers/', include('customers.urls')),
    path('order/', include('order.urls')),
    path('cart/', include('cart.urls')),
    path('coupon/', include('coupon.urls')),
    path('reports/', include('reports.urls')),
    path('wallet/', include('wallet.urls')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)