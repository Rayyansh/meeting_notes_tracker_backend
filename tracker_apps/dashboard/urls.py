from django.urls import path

from tracker_apps.dashboard.controllers.dashboard import DashboardViewController

urlpatterns = [
    path("summary/", DashboardViewController.summary, name="dashboard_summary"),
]
