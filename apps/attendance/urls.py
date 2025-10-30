from django.urls import path
from .views import my_schedule

urlpatterns = [
    path("me/schedule/", my_schedule, name="my_schedule"),
]
