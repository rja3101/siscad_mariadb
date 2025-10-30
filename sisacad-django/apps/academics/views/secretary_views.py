from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse
from ..models import Term
from ..services.import_service import ImportService
from ..services.report_service import ReportService
from ..forms import ImportStudentsForm, ImportEnrollmentsForm


@staff_member_required
def import_students_view(request):
    """
    Importar estudiantes desde XLSX
    GET/POST /secretary/import/students/
    """
    if request.method == 'POST':
        form = ImportStudentsForm(request.POST, request.FILES)
        
        if form.is_valid():
            file = request.FILES['file']
            results = ImportService.import_students(file)
            
            # Mostrar resultados
            if results['created'] > 0:
                messages.success(
                    request,
                    f"✓ {results['created']} estudiantes creados"
                )
            
            if results['updated'] > 0:
                messages.info(
                    request,
                    f"↻ {results['updated']} estudiantes actualizados"
                )
            
            if results['errors']:
                for error in results['errors']:
                    messages.error(request, error)
            
            if not results['errors']:
                messages.success(request, "Importación completada exitosamente")
                return redirect('import_students')
    else:
        form = ImportStudentsForm()
    
    context = {
        'form': form,
        'title': 'Importar Estudiantes',
        'instructions': """
            <p>El archivo XLSX debe contener las siguientes columnas:</p>
            <ul>
                <li><strong>username:</strong> Nombre de usuario único</li>
                <li><strong>first_name:</strong> Nombres</li>
                <li><strong>last_name:</strong> Apellidos</li>
                <li><strong>email:</strong> Correo electrónico</li>
            </ul>
            <p>La primera fila debe contener los encabezados.</p>
        """
    }
    
    return render(request, 'academics/secretary/import_students.html', context)


@staff_member_required
def import_enrollments_view(request):
    """
    Importar matrículas desde XLSX
    GET/POST /secretary/import/enrollments/
    """
    term = Term.objects.filter(is_active=True).first()
    
    if not term:
        messages.error(request, "No hay periodo académico activo")
        return redirect('admin:index')
    
    if request.method == 'POST':
        form = ImportEnrollmentsForm(request.POST, request.FILES)
        
        if form.is_valid():
            file = request.FILES['file']
            results = ImportService.import_enrollments(file, term)
            
            # Mostrar resultados
            if results['enrolled'] > 0:
                messages.success(
                    request,
                    f"✓ {results['enrolled']} estudiantes matriculados"
                )
            
            if results['waitlisted'] > 0:
                messages.info(
                    request,
                    f"⏳ {results['waitlisted']} agregados a lista de espera"
                )
            
            if results['errors']:
                for error in results['errors']:
                    messages.error(request, error)
            
            if not results['errors']:
                messages.success(request, "Importación completada exitosamente")
                return redirect('import_enrollments')
    else:
        form = ImportEnrollmentsForm()
    
    context = {
        'form': form,
        'term': term,
        'title': 'Importar Matrículas',
        'instructions': """
            <p>El archivo XLSX debe contener las siguientes columnas:</p>
            <ul>
                <li><strong>username:</strong> Nombre de usuario del estudiante</li>
                <li><strong>course_code:</strong> Código del curso (ej: CS101)</li>
                <li><strong>section:</strong> Código de sección (ej: A, B, C1)</li>
            </ul>
            <p>La primera fila debe contener los encabezados.</p>
            <p><strong>Periodo actual:</strong> {}</p>
        """.format(term.name)
    }
    
    return render(request, 'academics/secretary/import_enrollments.html', context)


@staff_member_required
def occupancy_report_view(request):
    """
    Reporte de ocupación
    GET /secretary/reports/occupancy/
    """
    term_id = request.GET.get('term')
    
    if term_id:
        term = Term.objects.filter(pk=term_id).first()
    else:
        term = Term.objects.filter(is_active=True).first()
    
    if not term:
        messages.error(request, "No hay periodo académico seleccionado")
        return redirect('admin:index')
    
    report_data = ReportService.get_occupancy_report(term)
    
    # Calcular totales
    total_capacity = sum(r['capacity'] for r in report_data)
    total_enrolled = sum(r['enrolled'] for r in report_data)
    avg_usage = (total_enrolled / total_capacity * 100) if total_capacity > 0 else 0
    
    context = {
        'term': term,
        'terms': Term.objects.all().order_by('-start_date'),
        'report_data': report_data,
        'total_capacity': total_capacity,
        'total_enrolled': total_enrolled,
        'avg_usage': round(avg_usage, 2)
    }
    
    return render(request, 'academics/secretary/occupancy_report.html', context)


@staff_member_required
def occupancy_report_csv(request):
    """
    Exportar reporte a CSV
    GET /secretary/reports/occupancy.csv
    """
    term_id = request.GET.get('term')
    
    if term_id:
        term = Term.objects.filter(pk=term_id).first()
    else:
        term = Term.objects.filter(is_active=True).first()
    
    if not term:
        return HttpResponse("Periodo no encontrado", status=404)
    
    csv_content = ReportService.export_occupancy_csv(term)
    
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ocupacion_{term.code}.csv"'
    
    return response