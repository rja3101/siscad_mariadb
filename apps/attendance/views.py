from django.apps import apps
from django.http import HttpResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from apps.users.decorators import role_required 

def _field_names(model):
    return {f.name for f in model._meta.get_fields() if hasattr(f, "name")}

@role_required(["Alumno"])
def my_schedule(request):
    Enrollment = apps.get_model("academics", "Enrollment")
    Schedule   = apps.get_model("attendance", "Schedule")

    sch_fields = _field_names(Schedule)

    section_ids, course_ids, course_group_ids = set(), set(), set()
    for e in Enrollment.objects.filter(student=request.user):
        sec = getattr(e, "section", None)
        if sec is not None:
            section_ids.add(getattr(sec, "id", None))
            crs = getattr(sec, "course", None)
            if crs is not None:
                course_ids.add(getattr(crs, "id", None))

        cg = getattr(e, "course_group", None)
        if cg is not None:
            course_group_ids.add(getattr(cg, "id", None))
            crs = getattr(cg, "course", None)
            if crs is not None:
                course_ids.add(getattr(crs, "id", None))

        crs = getattr(e, "course", None)
        if crs is not None:
            course_ids.add(getattr(crs, "id", None))

    qs = Schedule.objects.all()

    if "section" in sch_fields and section_ids:
        qs = qs.filter(section_id__in=[sid for sid in section_ids if sid])
    elif "course_group" in sch_fields and course_group_ids:
        qs = qs.filter(course_group_id__in=[gid for gid in course_group_ids if gid])
    elif "course" in sch_fields and course_ids:
        qs = qs.filter(course_id__in=[cid for cid in course_ids if cid])

    order_by_fields = [f for f in ["day_of_week", "day", "weekday", "date", "start_time"] if f in sch_fields]
    if order_by_fields:
        qs = qs.order_by(*order_by_fields)
    else:
        qs = qs.order_by("id")

    rows = []
    for s in qs:
        day = (
            getattr(s, "get_day_of_week_display", None)() if hasattr(s, "get_day_of_week_display") else
            getattr(s, "day_of_week", None) or getattr(s, "day", None) or getattr(s, "weekday", None) or getattr(s, "date", "—")
        )

        course_name, section_code = "—", "—"
        if hasattr(s, "section") and getattr(s, "section") is not None:
            sec = s.section
            section_code = getattr(sec, "code", "—")
            crs = getattr(sec, "course", None)
            course_name = getattr(crs, "name", "—") if crs else course_name
        elif hasattr(s, "course_group") and getattr(s, "course_group") is not None:
            cg = s.course_group
            section_code = getattr(cg, "code", getattr(cg, "group_code", "—"))
            crs = getattr(cg, "course", None)
            course_name = getattr(crs, "name", "—") if crs else course_name
        elif hasattr(s, "course") and getattr(s, "course") is not None:
            course_name = getattr(s.course, "name", "—")

        room = getattr(s, "room", None) or getattr(s, "classroom", None) or "—"
        start = getattr(s, "start_time", None) or getattr(s, "start", None) or "—"
        end   = getattr(s, "end_time", None)   or getattr(s, "end", None)   or "—"

        rows.append({
            "day": day, "course": course_name, "section": section_code,
            "room": room, "start": start, "end": end,
        })

    try:
        return render(request, "attendance/my_schedule.html", {"schedules": rows})
    except TemplateDoesNotExist:
        if not rows:
            html = "<!doctype html><body><h1>Mi horario</h1><p>No tienes horarios asignados.</p></body>"
            return HttpResponse(html)
        body = "".join(
            f"<tr><td>{r['day']}</td><td>{r['course']}</td><td>{r['section']}</td>"
            f"<td>{r['room']}</td><td>{r['start']}</td><td>{r['end']}</td></tr>"
            for r in rows
        )
        html = f"""
        <!doctype html><html><body>
        <h1>Mi horario</h1>
        <table>
          <thead><tr><th>Día</th><th>Curso</th><th>Sección</th><th>Aula</th><th>Inicio</th><th>Fin</th></tr></thead>
          <tbody>{body}</tbody>
        </table>
        <p style="margin-top:12px;color:#666">* Vista temporal sin plantilla. Crea <code>templates/attendance/my_schedule.html</code> cuando quieras estilizar.</p>
        </body></html>
        """
        return HttpResponse(html)
