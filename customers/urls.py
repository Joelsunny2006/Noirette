from django.urls import path
from . import views

urlpatterns = [
    path('user_status/<int:user_id>/', views.user_status, name='user_status'),
    path('customer/', views.customer, name='customer'),
    path('blocked/<int:user_id>',views.user_blocked,name='user_blocked'),
    path('unblock/<int:user_id>',views.user_unblocked,name='user_unblock'),
]