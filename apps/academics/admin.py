# apps/academics/admin.py
from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import IntegerWidget
from import_export.admin import ImportExportModelAdmin

from .models import Course, CourseGroup, Enrollment, Assessment, Grade

# ---------- Resources (import/export) ----------

class CourseResource(resources.ModelResource):
    # Permite importar 'teacher_username' y 'semester'
    teacher_username = fields.Field(column_name="teacher_username")
    semester = fields.Field(column_name="semester", widget=IntegerWidget())

    class Meta:
        model = Course
        fields = ("code", "name", "semester", "credits", "teacher_username")
        import_id_fields = ("code",)

    def before_save_instance(self, instance, using_transactions, dry_run):
        # mapear teacher_username -> FK
        if hasattr(instance, "_cached_teacher_username"):
            return
        username = self.row.get("teacher_username")
        if username:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            instance.teacher = User.objects.filter(username=username).first()
        instance._cached_teacher_username = True  # evita repetir

class EnrollmentResource(resources.ModelResource):
    class Meta:
        model = Enrollment
        fields = (
            "student__username",
            "course_group__course__code",
            "course_group__section",
            "created_at",
        )
        export_order = fields

class GradeResource(resources.ModelResource):
    class Meta:
        model = Grade
        fields = (
            "student__username",
            "assessment__course_group__course__code",
            "assessment__title",
            "score",
        )
        export_order = fields


# ---------- Admins ----------

@admin.register(Course)
class CourseAdmin(ImportExportModelAdmin):
    resource_class = CourseResource
    list_display = ("code", "name", "semester_display", "credits", "teacher")
    list_filter = ("semester", "credits", "teacher")
    search_fields = ("code", "name", "teacher__username")

    @admin.display(ordering="semester", description="Semester")
    def semester_display(self, obj):
        # Muestra la etiqueta del choice (o el valor), nunca “–”
        # get_semester_display ya devuelve "1", "2", … (por ser choices)
        return obj.get_semester_display() or obj.semester or ""

@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ("course", "section", "is_lab", "capacity", "enrolled_count")
    list_filter = ("is_lab", "course")
    search_fields = ("course__code", "course__name", "section")

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

@admin.register(Grade)
class GradeAdmin(ImportExportModelAdmin):
    resource_class = GradeResource
    list_display = ("student", "assessment", "score")
    search_fields = ("student__username", "assessment__title")
    list_filter = ("assessment__course_group__course__code", "assessment__kind")
