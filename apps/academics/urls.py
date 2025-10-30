from django.urls import path
from .views import (
    academics_index,
    coursegroup_stats,
    group_stats_view,
    my_performance,
    export_group_grades_csv,
)

urlpatterns = [
    path("", academics_index, name="academics_index"),
    path("group/<int:group_id>/stats/", coursegroup_stats, name="coursegroup_stats_json"),
    path("group/<int:group_id>/stats/view/", group_stats_view, name="coursegroup_stats_view"),
    path("group/<int:group_id>/grades.csv", export_group_grades_csv, name="export_group_grades_csv"),
    path("me/performance/", my_performance, name="my_performance"),
]
