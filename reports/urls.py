# urls.py
from django.urls import path
from .views import sales_report_api, download_sales_report,salesanalytics,get_date_range,sales_report

urlpatterns = [
    path('sales-report/', sales_report_api, name='sales_report_api'),
    path('download-sales-report/', download_sales_report, name='download_sales_report'),
    path('salesanalytics/', salesanalytics, name='salesanalytics'),
    path('get_date_range/', get_date_range, name='get_date_range'),
    path('sales-report/', sales_report, name='sales_report'),


]
    
