# urls.py
from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
urlpatterns = [
    path('about/',views.about,name='about'),
    path('', views.home, name='home'),
    path('signup', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('verify-otp/<int:user_id>/', views.verify_otp, name='verify_otp'),
    path('resend-otp/<int:user_id>/', views.resend_otp, name='resend_otp'),
    path('contact/',views.contact,name='contact'),
    path('checkout/',views.checkout,name='checkout'),
    path('shop/',views.shop,name='shop'),
    path('user-profile/',views.user_profile,name="user_profile"),
    path('user-profile/edit/', views.edit_profile, name='edit_profile'),
    path('user-profile/change-password/', views.change_password, name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),   
    path('support', views.support, name='support'),
]