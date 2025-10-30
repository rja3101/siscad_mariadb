from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from ..models import Term, CourseGroup, Enrollment
from ..services.cart_service import CartService
from ..services.enrollment_service import EnrollmentService


@login_required
def offerings_view(request):
    """Vista de oferta de secciones - GET /academics/offerings/"""
    # Obtener término activo
    term = Term.objects.filter(is_active=True).first()
    
    if not term:
        messages.error(request, "No hay periodo académico activo")
        return redirect('home')
    
    # Filtros
    course_code = request.GET.get('course_code', '')
    section = request.GET.get('section', '')
    
    groups = CourseGroup.objects.filter(term=term).select_related('course')
    
    if course_code:
        groups = groups.filter(course__code__icontains=course_code)
    if section:
        groups = groups.filter(section_code__icontains=section)
    
    # Agregar info de disponibilidad
    for group in groups:
        group.available_slots_count = group.get_available_slots()
        group.enrolled_count = Enrollment.objects.filter(
            course_group=group,
            term=term,
            status='ENROLLED'
        ).count()
    
    context = {
        'term': term,
        'groups': groups,
        'course_code': course_code,
        'section': section
    }
    
    return render(request, 'academics/student/offerings.html', context)


@login_required
def cart_view(request):
    """Vista del carrito - GET /academics/cart/"""
    term = Term.objects.filter(is_active=True).first()
    
    if not term:
        messages.error(request, "No hay periodo académico activo")
        return redirect('home')
    
    cart_summary = CartService.get_cart_summary(request.user, term)
    
    context = {
        'term': term,
        **cart_summary
    }
    
    return render(request, 'academics/student/cart.html', context)


@login_required
@require_POST
def add_to_cart(request, group_id):
    """Agregar curso al carrito - POST /academics/cart/add/<group_id>/"""
    term = Term.objects.filter(is_active=True).first()
    
    if not term:
        return JsonResponse({'success': False, 'errors': ['No hay periodo activo']})
    
    group = get_object_or_404(CourseGroup, pk=group_id)
    
    success, messages_list = CartService.add_to_cart(request.user, group, term)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'messages': messages_list
        })
    
    for msg in messages_list:
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    
    return redirect('cart_view')


@login_required
@require_POST
def remove_from_cart(request, group_id):
    """Eliminar curso del carrito - POST /academics/cart/remove/<group_id>/"""
    term = Term.objects.filter(is_active=True).first()
    group = get_object_or_404(CourseGroup, pk=group_id)
    
    success, messages_list = CartService.remove_from_cart(request.user, group, term)
    
    for msg in messages_list:
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    
    return redirect('cart_view')


@login_required
@require_POST
def confirm_cart(request):
    """Confirmar matrícula - POST /academics/cart/confirm/"""
    term = Term.objects.filter(is_active=True).first()
    
    if not term:
        messages.error(request, "No hay periodo académico activo")
        return redirect('cart_view')
    
    success, error_msgs, enrollments = EnrollmentService.confirm_enrollment(
        request.user, term, enrolled_by=request.user
    )
    
    if success:
        messages.success(request, "¡Matrícula confirmada exitosamente!")
        messages.info(request, f"Cursos matriculados: {len(enrollments)}")
        return redirect('my_enrollments')
    else:
        for error in error_msgs:
            messages.error(request, error)
        return redirect('cart_view')


@login_required
def my_enrollments_view(request):
    """Mis matrículas - GET /academics/me/enrollments/"""
    term = Term.objects.filter(is_active=True).first()
    
    if not term:
        messages.error(request, "No hay periodo académico activo")
        return redirect('home')
    
    enrollments = Enrollment.objects.filter(
        student=request.user,
        term=term,
        status='ENROLLED'
    ).select_related('course_group', 'course_group__course')
    
    # Calcular total de créditos
    total_credits = sum(
        e.course_group.course.credits 
        for e in enrollments
    )
    
    context = {
        'term': term,
        'enrollments': enrollments,
        'total_credits': total_credits
    }
    
    return render(request, 'academics/student/my_enrollments.html', context)


@login_required
@require_POST
def drop_enrollment_view(request, enrollment_id):
    """Dar de baja - POST /academics/enrollment/drop/<id>/"""
    enrollment = get_object_or_404(
        Enrollment,
        pk=enrollment_id,
        student=request.user,
        status='ENROLLED'
    )
    
    success, msgs = EnrollmentService.drop_enrollment(enrollment, request.user)
    
    for msg in msgs:
        messages.success(request, msg) if success else messages.error(request, msg)
    
    return redirect('my_enrollments')


@login_required
@require_POST
def swap_section_view(request, enrollment_id):
    """Cambiar sección - POST /academics/enrollment/swap/<id>/"""
    enrollment = get_object_or_404(
        Enrollment,
        pk=enrollment_id,
        student=request.user,
        status='ENROLLED'
    )
    
    new_group_id = request.POST.get('new_group_id')
    new_group = get_object_or_404(CourseGroup, pk=new_group_id)
    
    success, msgs = EnrollmentService.swap_section(
        request.user,
        enrollment.course_group,
        new_group,
        enrollment.term
    )
    
    for msg in msgs:
        messages.success(request, msg) if success else messages.error(request, msg)
    
    return redirect('my_enrollments')