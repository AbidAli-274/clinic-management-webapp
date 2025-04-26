from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from accounts.models import Organization, UserProfile


def reset_password_to_default(modeladmin, request, queryset):
    for user in queryset:
        user.set_password('defaultpassword123')
        user.save()
    messages.success(request, "Selected users' passwords have been reset to 'defaultpassword123'.")
reset_password_to_default.short_description = "Reset password to default ('defaultpassword123')"


@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    model = UserProfile
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    actions = [reset_password_to_default]
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email', 'age', 'contact', 'gender', 'organization')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'role')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location')
    search_fields = ('name', 'location')
    list_filter = ('location',)
