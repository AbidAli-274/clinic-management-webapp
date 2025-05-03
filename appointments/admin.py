from django.contrib import admin

from appointments.models import Consultancy, Session


class SessionAdmin(admin.ModelAdmin):
    list_display = ("patient", "date_time", "status")
    list_filter = ("status",)
    search_fields = ("patient__name", "date_time")


admin.site.register(Consultancy)
admin.site.register(Session, SessionAdmin)
