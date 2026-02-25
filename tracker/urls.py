from django.urls import path
from . import views
from .views import register
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('attendance/', views.mark_attendance, name='mark_attendance'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='tracker/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("edit-attendance/<int:record_id>/", views.edit_attendance, name="edit_attendance"),
    path("delete-attendance/<int:record_id>/", views.delete_attendance, name="delete_attendance"),
]
