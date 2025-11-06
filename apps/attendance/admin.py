from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import Widget
from datetime import datetime, time

from .models import Schedule, Session, Attendance
from apps.academics.models import Course, CourseGroup

# ───────── Widgets ─────────
DAY_MAP = {
    "lunes": 1,
    "martes": 2,
    "miercoles": 3, "miércoles": 3,
    "jueves": 4,
    "viernes": 5,
}

class DayWidget(Widget):
    def clean(self, value, row=None, **kwargs):
        if value is None or f"{value}".strip() == "":
            return None
        key = f"{value}".strip().lower()
        if key in DAY_MAP:
            return DAY_MAP[key]
        raise ValueError(f"Valor de 'day_of_the_week' inválido: {value}")

    def render(self, value, obj=None):
        inv = {v: k.capitalize() for k, v in DAY_MAP.items()}
        return inv.get(value, value)

class TimeWidget(Widget):
    """Acepta HH:MM:SS (y fallback HH:MM)."""
    def clean(self, value, row=None, **kwargs):
        if value is None or f"{value}".strip() == "":
            return None
        txt = str(value).strip()
        try:
            return datetime.strptime(txt, "%H:%M:%S").time()
        except ValueError:
            return datetime.strptime(txt, "%H:%M").time()

    def render(self, value, obj=None):
        return value.strftime("%H:%M:%S") if isinstance(value, time) else ""

class CourseGroupByCodeSectionWidget(Widget):
    """
    Construye/resuelve CourseGroup leyendo del CSV:
      - column 'course_code' (obligatoria)
      - column 'section' (si falta, usa 'A')
    """
    def clean(self, value, row=None, **kwargs):
        code = (row.get("course_code") or "").strip()
        section = (row.get("section") or "").strip() or "A"
        if not code:
            raise ValueError("Falta 'course_code' en la fila.")

        course = Course.objects.filter(code=code).first()
        if not course:
            raise ValueError(f"Curso no encontrado (code): {code}")

        cg = CourseGroup.objects.filter(course=course, section__iexact=section).first()
        if not cg:
            cg = CourseGroup.objects.create(course=course, section=section)
        return cg

    def render(self, value, obj=None):
        # para exportar legible
        if obj and getattr(obj, "course_group", None):
            return obj.course_group.course.code
        return ""

# ───────── Resource para Schedule ─────────
class ScheduleResource(resources.ModelResource):
    # Leemos 'course_code' del CSV pero asignamos a 'course_group'
    course_group = fields.Field(
        column_name="course_code",
        attribute="course_group",
        widget=CourseGroupByCodeSectionWidget(),
    )
    day = fields.Field(column_name="day_of_the_week", attribute="day", widget=DayWidget())
    start_time = fields.Field(column_name="start_time", attribute="start_time", widget=TimeWidget())
    end_time = fields.Field(column_name="end_time", attribute="end_time", widget=TimeWidget())
    classroom = fields.Field(column_name="classroom", attribute="classroom")

    # Para exportación, que salga el code/section en columnas claras
    def dehydrate_course_group(self, obj):
        return obj.course_group.course.code if obj.course_group else ""

    def dehydrate_section(self, obj):
        return obj.course_group.section if obj.course_group else ""

    class Meta:
        model = Schedule
        import_id_fields = ("course_group", "day", "start_time", "classroom")
        fields = ("course_group", "day", "start_time", "end_time", "classroom")
        skip_unchanged = True

@admin.register(Schedule)
class ScheduleAdmin(ImportExportModelAdmin):
    resource_class = ScheduleResource
    # Mostrar columnas “amigables”
    list_display = ("id", "course_code", "section", "day", "start_time", "end_time", "classroom")
    list_filter = ("day", "classroom", "course_group__course")
    search_fields = (
        "course_group__course__code",
        "course_group__course__name",
        "course_group__section",
        "classroom",
    )

    @admin.display(description="course_code")
    def course_code(self, obj):
        return obj.course_group.course.code if obj.course_group else "-"

    @admin.display(description="section")
    def section(self, obj):
        return obj.course_group.section if obj.course_group else "-"

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "schedule", "date", "created_at")
    list_filter = ("date", "schedule__course_group__course")
    search_fields = ("schedule__course_group__course__name", "schedule__course_group__section")

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "session", "entry_time", "ip_address")
    list_filter = ("session__date", "student")
    search_fields = ("student__username", "ip_address")
