from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "phone_number",
        "city",
        "gender",
        "organization",
        "created_at",
    )
    list_filter = ("gender", "city", "organization", "created_at")
    search_fields = ("name", "phone_number", "city")
    readonly_fields = ("created_at",)

    fieldsets = (
        ("Personal Info", {"fields": ("name", "phone_number", "gender", "city")}),
        ("Organization Info", {"fields": ("organization",)}),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    ordering = ("-created_at",)  # newest first

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("organization")
