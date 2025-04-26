from django.urls import path

from .views import (DeleteOrganizationView, DeleteUserView,
                    EditOrganizationView, EditUserView, LoginView, LogoutView,
                    OrganizationCreateView, OrganizationListView,
                    OrganizationUsersView, UserProfileCreateView,
                    accept_patient, end_session_patient, home)

app_name = "accounts"

urlpatterns = [
    path("", home, name="home"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "organization/create/",
        OrganizationCreateView.as_view(),
        name="create_organization",
    ),
    path("user/create/", UserProfileCreateView.as_view(), name="create_user"),
    path("organization/list", OrganizationListView.as_view(), name="list"),
    path("<int:organization_id>/users/", OrganizationUsersView.as_view(), name="users"),
    path(
        "<int:organization_id>/edit/",
        EditOrganizationView.as_view(),
        name="edit_organization",
    ),
    path(
        "<int:organization_id>/delete/",
        DeleteOrganizationView.as_view(),
        name="delete_organization",
    ),
    path("users/<int:user_id>/edit/", EditUserView.as_view(), name="edit_user"),
    path("users/<int:user_id>/delete/", DeleteUserView.as_view(), name="delete_user"),
    path("accept-patient/<int:pk>/", accept_patient, name="accept_patient"),
    path(
        "end-session-patient/<int:pk>/", end_session_patient, name="end_session_patient"
    ),
]
