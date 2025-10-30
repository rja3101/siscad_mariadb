from django.urls import path
from . import views

urlpatterns = [
    path("student/materials/", views.my_materials, name="my_materials"),
]
