from django.urls import path

from tracker_apps.action_item.controllers.action_item import ActionItemViewController

urlpatterns = [
    path("create/", ActionItemViewController.create, name="action_item_create"),
    path("update/", ActionItemViewController.update, name="action_item_update"),
    path("get/", ActionItemViewController.get, name="action_item_get"),
    path("get_all/", ActionItemViewController.get_all, name="action_item_get_all"),
    path("delete/", ActionItemViewController.delete, name="action_item_delete"),
]
