from django.contrib import admin
from accounts.models import Organization, UserProfile


admin.site.register(Organization)
admin.site.register(UserProfile)
