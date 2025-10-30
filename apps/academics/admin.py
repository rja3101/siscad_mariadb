from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Course, CourseGroup, Enrollment, Assessment, Grade

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "credits", "teacher")
    search_fields = ("code", "name", "teacher__username")
    list_filter = ("credits",)

@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ("course", "section", "is_lab", "capacity", "enrolled_count")
    list_filter = ("is_lab", "course")
    search_fields = ("course__code", "course__name", "section")

class EnrollmentResource(resources.ModelResource):
    class Meta:
        model = Enrollment
        fields = ("student__username", "course_group__course__code", "course_group__section", "created_at",)
        export_order = fields

@admin.register(Enrollment)
class EnrollmentAdmin(ImportExportModelAdmin):
    resource_class = EnrollmentResource
    list_display = ("student", "course_group", "created_at")
    search_fields = ("student__username", "course_group__course__code", "course_group__section")
    list_filter = ("course_group__course__code", "created_at")

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("course_group", "title", "kind", "weight", "total_points")
    list_filter = ("kind", "course_group__course__code")
    search_fields = ("title", "course_group__course__name")

class GradeResource(resources.ModelResource):
    class Meta:
        model = Grade
        fields = ("student__username", "assessment__course_group__course__code",
                  "assessment__title", "score")
        export_order = fields

@admin.register(Grade)
class GradeAdmin(ImportExportModelAdmin):
    resource_class = GradeResource
    list_display = ("student", "assessment", "score")
    search_fields = ("student__username", "assessment__title")
    list_filter = ("assessment__course_group__course__code", "assessment__kind")
