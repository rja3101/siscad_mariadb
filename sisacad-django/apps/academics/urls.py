from django.urls import path
from .views import (
    academics_index,
    student_views,
    secretary_views,
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

    # Rutas de estudiante
    path('offerings/', student_views.offerings_view, name='offerings'),
    path('cart/', student_views.cart_view, name='cart_view'),
    path('cart/add/<int:group_id>/', student_views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:group_id>/', student_views.remove_from_cart, name='remove_from_cart'),
    path('cart/confirm/', student_views.confirm_cart, name='confirm_cart'),
    path('me/enrollments/', student_views.my_enrollments_view, name='my_enrollments'),
    path('enrollment/drop/<int:enrollment_id>/', student_views.drop_enrollment_view, name='drop_enrollment'),
    path('enrollment/swap/<int:enrollment_id>/', student_views.swap_section_view, name='swap_section'),
    
    # Rutas de secretaría (staff only)
    path('secretary/import/students/', secretary_views.import_students_view, name='import_students'),
    path('secretary/import/enrollments/', secretary_views.import_enrollments_view, name='import_enrollments'),
    path('secretary/reports/occupancy/', secretary_views.occupancy_report_view, name='occupancy_report'),
    path('secretary/reports/occupancy.csv', secretary_views.occupancy_report_csv, name='occupancy_report_csv'),
]
]
