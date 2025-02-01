# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('product/<str:serial_number>/', views.product_view, name='product'),
    path('products/', views.product_list, name='product_list'),  # Renamed from 'product'
    path('add_product/', views.add_product, name='add_product'),
    path('update_product/<int:product_id>/', views.update_product, name='update_product'),
    path('delete_product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('brand/', views.brand_list, name='brand'),
    path('add_brand/', views.add_brand, name='add_brand'),
    path('delete_brand/<int:brand_id>/', views.delete_brand, name='delete_brand'),
    path('edit_brand/<int:brand_id>/', views.edit_brand, name='edit_brand'),
    path('remove-product-image/<int:image_id>/', views.remove_product_image, name='remove_product_image'),
] 