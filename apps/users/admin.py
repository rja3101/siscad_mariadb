from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.hashers import make_password
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from .models import User, Role


class UserResource(resources.ModelResource):
    role = fields.Field(
        column_name="role",
        attribute="role",
        widget=ForeignKeyWidget(Role, "name"),
    )
    password = fields.Field(column_name="password")

    class Meta:
        model = User
        import_id_fields = ("username",)  
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "password",
        )
        skip_unchanged = True

    def before_import_row(self, row, **kwargs):
        row.setdefault("password", "123")
        for col in ("is_active", "is_staff", "is_superuser"):
            if col in row:
                val = str(row[col]).strip().lower()
                row[col] = 1 if val in ("1", "true", "t", "yes", "y") else 0

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        raw = getattr(instance, "password", "")
        if raw and not raw.startswith("pbkdf2_"):
            instance.password = make_password(raw)


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, DjangoUserAdmin):
    resource_classes = [UserResource]
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "role")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name", "email", "role")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "role", "is_active"),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
