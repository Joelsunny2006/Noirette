from django.urls import path
from . import views

urlpatterns = [
    path('category/', views.category, name='category'),
    path('add_category/', views.add_category, name='add_category'),
    path('update-category/<int:category_id>/', views.update_category, name='update_category'),
    path('delete_category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('toggle_category/<int:category_id>/',views.toggle_category,name='toggle_category')
]   