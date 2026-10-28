from django.urls import path

from tracker_apps.meeting.controllers.meeting import MeetingViewController

urlpatterns = [
    path("create/", MeetingViewController.create, name="meeting_create"),
    path("update/", MeetingViewController.update, name="meeting_update"),
    path("get/", MeetingViewController.get, name="meeting_get"),
    path("get_all/", MeetingViewController.get_all, name="meeting_get_all"),
    path("delete/", MeetingViewController.delete, name="meeting_delete"),
]
