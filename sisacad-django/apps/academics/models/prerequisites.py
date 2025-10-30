from django.db import models


class CoursePrerequisite(models.Model):
    """Prerrequisito de un curso"""
    course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE,
        related_name='prerequisites_as_course'
    )
    prerequisite_course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE,
        related_name='prerequisites_as_prerequisite'
    )
    
    # Configuración adicional
    is_strict = models.BooleanField(
        default=True,
        help_text="Si es estricto, debe estar aprobado. Si no, puede estar cursando."
    )
    min_grade = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Nota mínima requerida (opcional)"
    )
    
    class Meta:
        db_table = 'course_prerequisites'
        unique_together = [['course', 'prerequisite_course']]
        indexes = [
            models.Index(fields=['course']),
        ]
    
    def __str__(self):
        return f"{self.course.code} requiere {self.prerequisite_course.code}"


class CourseCorequisite(models.Model):
    """Corequisito de un curso (debe llevarse en el mismo término)"""
    course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE,
        related_name='corequisites_as_course'
    )
    corequisite_course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE,
        related_name='corequisites_as_corequisite'
    )
    
    class Meta:
        db_table = 'course_corequisites'
        unique_together = [['course', 'corequisite_course']]
        indexes = [
            models.Index(fields=['course']),
        ]
    
    def __str__(self):
        return f"{self.course.code} con {self.corequisite_course.code}"


class GroupPairing(models.Model):
    """Emparejamiento de grupos teoría-laboratorio"""
    theory_group = models.ForeignKey(
        'CourseGroup',
        on_delete=models.CASCADE,
        related_name='paired_as_theory',
        help_text="Grupo de teoría"
    )
    lab_group = models.ForeignKey(
        'CourseGroup',
        on_delete=models.CASCADE,
        related_name='paired_as_lab',
        help_text="Grupo de laboratorio"
    )
    term = models.ForeignKey('Term', on_delete=models.CASCADE, related_name='group_pairings')
    
    # Configuración
    is_mandatory = models.BooleanField(
        default=True,
        help_text="Si es obligatorio, deben matricularse juntos"
    )
    
    class Meta:
        db_table = 'group_pairings'
        unique_together = [['theory_group', 'lab_group', 'term']]
        indexes = [
            models.Index(fields=['theory_group', 'term']),
            models.Index(fields=['lab_group', 'term']),
        ]
    
    def __str__(self):
        return f"{self.theory_group} ↔ {self.lab_group}"
    
    def get_paired_groups(self):
        """Retorna lista de ambos grupos"""
        return [self.theory_group, self.lab_group]