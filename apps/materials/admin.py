from django.contrib import admin
from .models import CourseMaterial

@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "uploaded_at")
    search_fields = ("title",)
    list_filter = ("course",)
