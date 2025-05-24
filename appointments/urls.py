from django.urls import path
from django.views.generic import TemplateView

from .views import (
    ConsultancyCreateView,
    DailyReportView,
    DoctorReportView,
    ExportExcelView,
    ExportPDFView,
    FeedbackDialogView,
    PendingDiscountsListView,
    ReceptionistConsultancyListView,
    ReceptionistConsultancyUpdateView,
    SessionCreateView,
    approve_discount,
    get_consultancies,
    get_doctor_by_consultancy,
    get_doctors_by_organization,
    get_pending_discounts_count,
    get_session_feedback_form,
    reject_discount,
    submit_session_feedback,
    trigger_home_refresh,
)

app_name = "appointments"

urlpatterns = [
    path(
        "consultation/create/",
        ConsultancyCreateView.as_view(),
        name="consultancy_create",
    ),
    path("session/create/", SessionCreateView.as_view(), name="session_create"),
    path("report/", DailyReportView.as_view(), name="daily_report"),
    path("export-pdf/", ExportPDFView.as_view(), name="export_pdf"),
    path("export-excel/", ExportExcelView.as_view(), name="export_excel"),
    path("doctor-report/", DoctorReportView.as_view(), name="doctor_report"),
    path("get-consultancies/", get_consultancies, name="get_consultancies"),
    path(
        "pending-discounts/",
        PendingDiscountsListView.as_view(),
        name="pending_discounts_list",
    ),
    path(
        "approve-discount/<str:item_type>/<int:pk>/",
        approve_discount,
        name="approve_discount",
    ),
    path(
        "reject-discount/<str:item_type>/<int:pk>/",
        reject_discount,
        name="reject_discount",
    ),
    path(
        "pending-discounts-count/",
        get_pending_discounts_count,
        name="pending_discounts_count",
    ),
    path("trigger-home-refresh/", trigger_home_refresh, name="trigger_home_refresh"),
    path(
        "get-doctors-by-organization/",
        get_doctors_by_organization,
        name="get_doctors_by_organization",
    ),
    path(
        "session/<int:session_id>/feedback-form/",
        get_session_feedback_form,
        name="get_session_feedback_form",
    ),
    path(
        "session/<int:session_id>/submit-feedback/",
        submit_session_feedback,
        name="submit_session_feedback",
    ),
    path(
        "session/<int:session_id>/feedback/",
        FeedbackDialogView.as_view(),
        name="feedback_dialog",
    ),
    path(
        "consultancy/save/",
        ReceptionistConsultancyListView.as_view(),
        name="receptionist_consultancy_list",
    ),
    path(
        "consultancy/save/<int:pk>/",
        ReceptionistConsultancyUpdateView.as_view(),
        name="receptionist_consultancy_update",
    ),
    path(
        "get-doctor-by-consultancy/",
        get_doctor_by_consultancy,
        name="get_doctor_by_consultancy",
    ),
]
