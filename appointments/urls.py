from django.urls import path
from .views import (
    PendingDiscountsListView,
    approve_discount,
    reject_discount,
    get_consultancy_fees,
    ConsultancyCreateView, 
    DailyReportView, 
    ExportExcelView, 
    ExportPDFView, 
    SessionCreateView, 
    get_consultancies,
    get_pending_discounts_count
)
app_name='appointments'

urlpatterns = [
    path('consultation/create/', ConsultancyCreateView.as_view(), name='consultancy_create'),
    path('session/create/', SessionCreateView.as_view(), name='session_create'),
    path('report/', DailyReportView.as_view(), name='daily_report'),
    path('export-pdf/', ExportPDFView.as_view(), name='export_pdf'),
    path('export-excel/', ExportExcelView.as_view(), name='export_excel'),
    path('get-consultancies/', get_consultancies, name='get_consultancies'),
    path('get-consultancy_fees/', get_consultancy_fees, name='get_consultancy_fees'),
    path('pending-discounts/', PendingDiscountsListView.as_view(), name='pending_discounts_list'),
    path('approve-discount/<str:item_type>/<int:pk>/', approve_discount, name='approve_discount'),
    path('reject-discount/<str:item_type>/<int:pk>/', reject_discount, name='reject_discount'),
    path('pending-discounts-count/', get_pending_discounts_count, name='pending_discounts_count'),
]
