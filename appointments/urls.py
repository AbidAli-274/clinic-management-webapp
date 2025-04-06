from django.urls import path
from .views import (
    PendingDiscountConsultancyListView,
    approve_discount_consultancy,
    reject_discount_consultancy,
    ConsultancyCreateView, 
    DailyReportView, 
    ExportExcelView, 
    ExportPDFView, 
    SessionCreateView, 
    get_consultancies
)
app_name='appointments'

urlpatterns = [
    path('consultation/create/', ConsultancyCreateView.as_view(), name='consultancy_create'),
    path('session/create/', SessionCreateView.as_view(), name='session_create'),
    path('report/', DailyReportView.as_view(), name='daily_report'),
    path('export-pdf/', ExportPDFView.as_view(), name='export_pdf'),
    path('export-excel/', ExportExcelView.as_view(), name='export_excel'),
    path('get-consultancies/', get_consultancies, name='get_consultancies'),
    path('pending-discount/', PendingDiscountConsultancyListView.as_view(), name='pending_discount_list'),
    path('pending-discount/<int:pk>/approve/', approve_discount_consultancy, name='approve_discount_consultancy'),
    path('pending-discount/<int:pk>/reject/', reject_discount_consultancy, name='reject_discount_consultancy'),
]
