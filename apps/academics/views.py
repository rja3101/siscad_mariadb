from django.apps import apps
from django.db.models import Avg
from django.http import HttpResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from apps.users.decorators import role_required 
def _field_names(model):
    return {f.name for f in model._meta.get_fields() if hasattr(f, "name")}

def _pick_grade_numeric_field(grade_fields: set[str]) -> str | None:
    for name in ["score", "grade", "value", "final", "points"]:
        if name in grade_fields:
            return name
    return None

@role_required(["Alumno"])
def my_performance(request):
    Enrollment = apps.get_model("academics", "Enrollment")
    Grade      = apps.get_model("academics", "Grade")

    grade_fields = _field_names(Grade)
    enrollment_fields = _field_names(Enrollment)
    num_field = _pick_grade_numeric_field(grade_fields)
    student_field = "student" if "student" in grade_fields else ("user" if "user" in grade_fields else None)

    enroll_qs = Enrollment.objects.filter(student=request.user)
    sel = []
    if "section" in enrollment_fields: sel.append("section__course")
    if "course_group" in enrollment_fields: sel.append("course_group__course")
    if "course" in enrollment_fields: sel.append("course")
    if sel: enroll_qs = enroll_qs.select_related(*sel)

    groups = []
    for e in enroll_qs:
        section = getattr(e, "section", None)
        course_group = getattr(e, "course_group", None)
        course = getattr(section, "course", None) or getattr(course_group, "course", None) or getattr(e, "course", None)
        groups.append({
            "course": course,
            "course_code": getattr(course, "code", "—"),
            "course_name": getattr(course, "name", "—"),
            "section": section,
            "section_code": getattr(section, "code", None) or getattr(course_group, "code", None) or getattr(course_group, "group_code", None) or "—",
            "course_group": course_group,
            "course_id": getattr(course, "id", None),
            "section_id": getattr(section, "id", None),
            "course_group_id": getattr(course_group, "id", None),
        })

    def avg_for_group(g):
        if not num_field or not student_field: return None
        base = Grade.objects.filter(**{student_field: request.user})
        if "section" in grade_fields and g["section_id"]:
            qs = base.filter(section_id=g["section_id"])
        elif "course_group" in grade_fields and g["course_group_id"]:
            qs = base.filter(course_group_id=g["course_group_id"])
        elif "course" in grade_fields and g["course_id"]:
            qs = base.filter(course_id=g["course_id"])
        else:
            qs = base.none()
        return qs.aggregate(avg=Avg(num_field))["avg"]

    rows, avgs = [], []
    for g in groups:
        avg = avg_for_group(g)
        if avg is None:
            status = "Sin notas registradas"
        else:
            status = "Al día" if avg >= 11 else "En riesgo"
            avgs.append(avg)
        rows.append({
            "course_code": g["course_code"],
            "course_name": g["course_name"],
            "section_code": g["section_code"],
            "avg": avg,
            "status": status,
        })

    global_avg = (sum(avgs) / len(avgs)) if avgs else None
    global_status = "Sin notas registradas" if global_avg is None else ("Al día" if global_avg >= 11 else "En riesgo")

    try:
        return render(request, "academics/my_performance.html", {
            "rows": rows, "global_avg": global_avg, "global_status": global_status
        })
    except TemplateDoesNotExist:
        if not rows:
            return HttpResponse("<!doctype html><body><h1>Mi desempeño</h1><p>Sin notas registradas.</p></body>")
        body = "".join(
            f"<tr><td>{r['course_code']} - {r['course_name']}</td>"
            f"<td>{r['section_code']}</td>"
            f"<td>{'—' if r['avg'] is None else f'{r['avg']:.2f}'}</td>"
            f"<td>{r['status']}</td></tr>"
            for r in rows
        )
        gline = ("—" if global_avg is None else f"{global_avg:.2f}") + f" — {global_status}"
        html = f"<!doctype html><body><h1>Mi desempeño</h1><table><thead><tr><th>Curso</th><th>Sección</th><th>Promedio</th><th>Semáforo</th></tr></thead><tbody>{body}</tbody></table><div><strong>Promedio global:</strong> {gline}</div></body>"
        return HttpResponse(html)
