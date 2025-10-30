from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.apps import apps
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import models

def pick_field(model, candidates):
    fields = {f.name for f in model._meta.get_fields() if hasattr(f, "name")}
    for c in candidates:
        if c in fields:
            return c
    return None

def create_section_safe(Section, course, docente):
    """
    Crea una Section con valores por defecto según los campos existentes,
    para evitar NOT NULL. Intenta usar:
      - identificador de texto: code/name/label/section/group
      - FK teacher si existe
      - FK term si existe (crea Term “2025-II” si hace falta)
      - otros campos típicos NOT NULL (nrc, capacity, campus, etc.) con defaults
    """
    fields = {f.name: f for f in Section._meta.get_fields() if hasattr(f, "name")}
    data = {}

    # FK al curso si existe
    if "course" in fields:
        data["course"] = course

    # Identificador legible
    id_name = pick_field(Section, ["code", "name", "label", "section", "group", "short_code"])
    if id_name:
        data[id_name] = "A"

    # Docente si la sección lo exige
    if "teacher" in fields:
        data["teacher"] = docente

    # Term si existe
    if "term" in fields:
        Term = apps.get_model("academics", "Term")
        term_obj, _ = Term.objects.get_or_create(
            defaults={"name": "2025-II"},
            **({"name": "2025-II"} if pick_field(Term, ["name", "code"]) == "name"
               else {pick_field(Term, ["code", "slug"]) or "code": "2025-II"})
        )
        data["term"] = term_obj

    # Algunos campos NUM/BOOL típicamente NOT NULL
    numeric_defaults = {
        "nrc": 1001,
        "capacity": 30,
        "vacancies": 30,
        "enrolled": 0,
    }
    for k, v in numeric_defaults.items():
        if k in fields:
            data.setdefault(k, v)

    if "campus" in fields:
        data.setdefault("campus", "Main")

    if "is_lab" in fields:
        data.setdefault("is_lab", False)

    # Rellena otros CharField/IntegerField NOT NULL sin default
    for name, f in fields.items():
        if isinstance(f, models.Field) and not f.auto_created:
            if getattr(f, "null", True) is False and f.has_default() is False:
                if name in data:
                    continue
                # Evita sobreescribir FKs ya atendidas
                if isinstance(f, (models.ForeignKey, models.OneToOneField)):
                    continue
                # Defaults genéricos
                if isinstance(f, (models.CharField, models.TextField)):
                    data[name] = "A"
                elif isinstance(f, (models.IntegerField, models.SmallIntegerField, models.PositiveIntegerField)):
                    data[name] = 1
                elif isinstance(f, models.BooleanField):
                    data[name] = False
                elif isinstance(f, models.DateField):
                    data[name] = timezone.localdate()
                elif isinstance(f, models.TimeField):
                    data[name] = timezone.now().time()

    # Busca si ya hay sección equivalente por (course + id_name)
    lookup = {}
    if "course" in data:
        lookup["course"] = data["course"]
    if id_name:
        lookup[id_name] = data[id_name]

    if lookup:
        obj, _ = Section.objects.get_or_create(defaults=data, **lookup)
    else:
        obj = Section.objects.create(**data)

    return obj

class Command(BaseCommand):
    help = "Crea datos de prueba mínimos para validar Persona C (Alumno: horario, desempeño, materiales)."

    def handle(self, *args, **options):
        User = get_user_model()
        Role = apps.get_model("users", "Role")

        Course = apps.get_model("academics", "Course")
        Enrollment = apps.get_model("academics", "Enrollment")
        Grade = apps.get_model("academics", "Grade")
        Materials = apps.get_model("materials", "CourseMaterial")
        Schedule = apps.get_model("attendance", "Schedule")

        Section = None
        CourseGroup = None
        try:
            Section = apps.get_model("academics", "Section")
        except Exception:
            pass
        try:
            CourseGroup = apps.get_model("academics", "CourseGroup")
        except Exception:
            pass

        # ---------- Usuarios / Roles ----------
        alumno_role, _ = Role.objects.get_or_create(name="Alumno")
        alumno, created = User.objects.get_or_create(
            username="alumno1",
            defaults={"email": "alumno1@example.com"},
        )
        if created:
            alumno.set_password("alumno1")
        alumno.role = alumno_role
        alumno.save()

        doc_role, _ = Role.objects.get_or_create(name="Docente")
        docente, created = User.objects.get_or_create(
            username="docente1",
            defaults={"email": "docente1@example.com", "is_staff": True},
        )
        if created:
            docente.set_password("docente1")
        docente.role = doc_role
        docente.save()

        # ---------- Course con teacher y defaults seguros ----------
        course_fields = {f.name for f in Course._meta.get_fields() if hasattr(f, "name")}
        course_defaults = {"name": "Algoritmos"}

        if "teacher" in course_fields:
            course_defaults["teacher"] = docente
        if "credits" in course_fields:
            course_defaults.setdefault("credits", 4)
        if "semester" in course_fields:
            course_defaults.setdefault("semester", "2025-II")
        if "status" in course_fields:
            course_defaults.setdefault("status", "ACTIVE")
        if "slug" in course_fields:
            course_defaults.setdefault("slug", "alg101")

        course, _ = Course.objects.get_or_create(
            code="ALG101",
            defaults=course_defaults
        )

        # ---------- Section (robusta) ----------
        section_obj = None
        if Section:
            section_obj = create_section_safe(Section, course, docente)

        # ---------- CourseGroup (usa section si existe) ----------
        course_group_obj = None
        if CourseGroup:
            cg_fields = {f.name for f in CourseGroup._meta.get_fields() if hasattr(f, "name")}
            defaults = {}
            if "is_lab" in cg_fields:
                defaults["is_lab"] = False
            if "capacity" in cg_fields:
                defaults["capacity"] = 30

            if "section" in cg_fields:
                if not section_obj:
                    # como última defensa, crea una sección mínima
                    section_obj = create_section_safe(Section, course, docente)
                course_group_obj, _ = CourseGroup.objects.get_or_create(
                    course=course,
                    section=section_obj,
                    defaults=defaults,
                )
            else:
                course_group_obj, _ = CourseGroup.objects.get_or_create(
                    course=course,
                    defaults=defaults,
                )

        # ---------- Enrollment ----------
        enroll_fields = {f.name for f in Enrollment._meta.get_fields() if hasattr(f, "name")}
        if "course_group" in enroll_fields and course_group_obj:
            Enrollment.objects.get_or_create(student=alumno, course_group=course_group_obj)
        elif "section" in enroll_fields and section_obj:
            Enrollment.objects.get_or_create(student=alumno, section=section_obj)
        elif "course" in enroll_fields:
            Enrollment.objects.get_or_create(student=alumno, course=course)
        else:
            Enrollment.objects.get_or_create(student=alumno)

        # ---------- Grades ----------
        grade_num = pick_field(Grade, ["score", "grade", "value", "final", "points"])
        grade_fk = pick_field(Grade, ["section", "course_group", "course", "enrollment"])
        student_fk = pick_field(Grade, ["student", "user"])

        if grade_num and grade_fk and student_fk:
            common_kwargs = {student_fk: alumno}
            if grade_fk == "section" and section_obj:
                common_kwargs["section"] = section_obj
            elif grade_fk == "course_group" and course_group_obj:
                common_kwargs["course_group"] = course_group_obj
            elif grade_fk == "course":
                common_kwargs["course"] = course
            else:
                if grade_fk == "enrollment":
                    enr = Enrollment.objects.filter(student=alumno).first()
                    if enr:
                        common_kwargs["enrollment"] = enr

            g1 = Grade(**common_kwargs)
            setattr(g1, grade_num, 12)
            g1.save()

            g2 = Grade(**common_kwargs)
            setattr(g2, grade_num, 15)
            g2.save()

        # ---------- Schedule ----------
        sch_fk = pick_field(Schedule, ["section", "course_group", "course"])
        sch_day = pick_field(Schedule, ["day_of_week", "day", "weekday", "date"])
        sch_start = pick_field(Schedule, ["start_time", "start"])
        sch_end = pick_field(Schedule, ["end_time", "end"])
        sch_room = pick_field(Schedule, ["room", "classroom"])

        sch_kwargs = {}
        if sch_fk == "section" and section_obj:
            sch_kwargs["section"] = section_obj
        elif sch_fk == "course_group" and course_group_obj:
            sch_kwargs["course_group"] = course_group_obj
        elif sch_fk == "course":
            sch_kwargs["course"] = course

        if sch_day:
            if sch_day == "date":
                sch_kwargs[sch_day] = timezone.localdate()
            else:
                sch_kwargs[sch_day] = 1  # Lunes
        if sch_start:
            sch_kwargs[sch_start] = timezone.datetime.strptime("08:00", "%H:%M").time()
        if sch_end:
            sch_kwargs[sch_end] = timezone.datetime.strptime("10:00", "%H:%M").time()
        if sch_room:
            sch_kwargs[sch_room] = "A-101"

        if sch_fk:
            Schedule.objects.get_or_create(**sch_kwargs)

        # ---------- Material ----------
        mat = Materials.objects.create(course=course, title="Sílabo")
        mat.file.save("silabo.txt", ContentFile(b"Contenido demo"), save=True)

        self.stdout.write(self.style.SUCCESS(
            "Seed listo.\n"
            "- Usuario: alumno1 / alumno1 (rol Alumno)\n"
            "- Curso: ALG101 (Algoritmos)\n"
            "- Horario: Lunes 08:00–10:00 A-101\n"
            "- Notas: 12 y 15 (promedio visible)\n"
            "- Material: Sílabo (descargable)\n"
            "\nAbre:\n"
            "  /attendance/me/schedule/\n"
            "  /academics/student/performance/\n"
            "  /academics/student/materials/\n"
        ))
