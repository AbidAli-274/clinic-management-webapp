from django.urls import path
from .views import ConsultancyCreateView, SessionCreateView

app_name='appointments'

urlpatterns = [
    path('consultation/create/', ConsultancyCreateView.as_view(), name='consultancy_create'),
    path('session/create/', SessionCreateView.as_view(), name='session_create'),
]
