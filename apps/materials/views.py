from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.apps import apps
from .models import CourseMaterial

@login_required
def my_materials(request):
    # Cargamos Enrollment perezosamente para evitar circulares
    Enrollment = apps.get_model("academics", "Enrollment")

    # cursos donde el alumno está matriculado (vía section.course si tu Enrollment tiene section)
    qs = (Enrollment.objects
          .filter(student=request.user)
          .select_related("section__course"))

    # si tu Enrollment no tiene section, y apunta directo a course, adapta a select_related("course")
    course_ids = set()
    for e in qs:
        # intenta ambas rutas; la que exista aportará el id
        course = getattr(getattr(e, "section", None), "course", None) or getattr(e, "course", None)
        if course:
            course_ids.add(course.id)

    materials = (CourseMaterial.objects
                 .filter(course_id__in=course_ids)
                 .select_related("course")
                 .order_by("-uploaded_at"))

    return render(request, "materials/my_materials.html", {"materials": materials})
