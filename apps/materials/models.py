from django.db import models

class CourseMaterial(models.Model):
    course = models.ForeignKey(
        "academics.Course",     
        on_delete=models.CASCADE,
        related_name="materials",
        db_index=True,
    )
    title = models.CharField(max_length=200)

    def cm_upload_to(instance, filename):
        code = getattr(instance.course, "code", "COURSE")
        return f"materials/{code}/{filename}"

    file = models.FileField(upload_to=cm_upload_to)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.course} · {self.title}"
