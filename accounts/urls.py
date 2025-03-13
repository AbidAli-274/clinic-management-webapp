from django.urls import path
from .views import LoginView, LogoutView, OrganizationCreateView, UserProfileCreateView,home

app_name = "accounts"

urlpatterns = [
    path("", home, name="home"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("organization/create/", OrganizationCreateView.as_view(), name="create_organization"),
    path("user/create/", UserProfileCreateView.as_view(), name="create_user"),
]
