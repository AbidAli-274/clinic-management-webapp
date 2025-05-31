from django.contrib import admin

from .models import Consultancy, Session


@admin.register(Consultancy)
class ConsultancyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient",
        "date_time",
        "referred_doctor",
        "room",
        "consultancy_fee",
        "discount",
        "number_of_sessions",
        "status",
    )
    list_filter = ("status", "referred_doctor", "room", "date_time")
    search_fields = ("patient__name", "referred_doctor__user__username")
    date_hierarchy = "date_time"
    ordering = ("-date_time",)

    fieldsets = (
        ("Basic Info", {"fields": ("patient", "chief_complaint", "date_time")}),
        ("Doctor and Room", {"fields": ("referred_doctor", "room")}),
        (
            "Financials",
            {"fields": ("consultancy_fee", "discount", "number_of_sessions")},
        ),
        ("Status", {"fields": ("status",)}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("patient", "referred_doctor", "room")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient",
        "doctor",
        "consultancy",
        "date_time",
        "room",
        "session_fee",
        "further_discount",
        "status",
        "created_at",
    )
    list_filter = ("status", "doctor", "room", "date_time")
    search_fields = ("patient__name", "doctor__user__username")
    date_hierarchy = "date_time"
    readonly_fields = ("created_at",)
    ordering = ("-date_time",)

    fieldsets = (
        ("Patient & Consultancy", {"fields": ("patient", "consultancy")}),
        ("Doctor & Room", {"fields": ("doctor", "room")}),
        (
            "Session Details",
            {"fields": ("session_fee", "further_discount", "feedback", "date_time")},
        ),
        ("Status & Timestamps", {"fields": ("status", "created_at")}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("patient", "doctor", "room", "consultancy")
