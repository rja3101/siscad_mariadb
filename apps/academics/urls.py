# apps/academics/urls.py
from django.urls import path
from .views import academics_index, my_performance

urlpatterns = [
    path("", academics_index, name="academics_index"),
    path("student/performance/", my_performance, name="my_performance"),
]
