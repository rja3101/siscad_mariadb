from django.shortcuts import render
from django.apps import apps
from django.http import HttpResponse
from django.template import loader, TemplateDoesNotExist
from apps.users.decorators import role_required

from .models import CourseMaterial

@role_required(["Alumno"])
def my_materials(request):
    Enrollment = apps.get_model("academics", "Enrollment")

    enrollments = (
        Enrollment.objects
        .filter(student=request.user)
        .select_related("course_group__course")  
    )

    course_ids = set()
    for e in enrollments:
        cg = getattr(e, "course_group", None)
        course = getattr(cg, "course", None)
        if course is None:
            course = getattr(e, "course", None)
        if course:
            course_ids.add(course.id)

    materials = (
        CourseMaterial.objects
        .filter(course_id__in=course_ids)
        .select_related("course")
        .order_by("-uploaded_at")
    )

    return render(request, "materials/my_materials.html", {"materials": materials})
