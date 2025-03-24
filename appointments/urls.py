from django.urls import path
from .views import ConsultancyCreateView, DailyReportView, ExportExcelView, ExportPDFView, SessionCreateView, get_consultancies

app_name='appointments'

urlpatterns = [
    path('consultation/create/', ConsultancyCreateView.as_view(), name='consultancy_create'),
    path('session/create/', SessionCreateView.as_view(), name='session_create'),
    path('report/', DailyReportView.as_view(), name='daily_report'),
    path('export-pdf/', ExportPDFView.as_view(), name='export_pdf'),
    path('export-excel/', ExportExcelView.as_view(), name='export_excel'),
    path('get-consultancies/', get_consultancies, name='get_consultancies'),
]
