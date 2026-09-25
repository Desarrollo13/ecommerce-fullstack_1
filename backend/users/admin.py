from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("E-commerce", {"fields": ("phone", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("E-commerce", {"fields": ("email", "phone", "role")}),
    )
    list_display = ("email", "username", "first_name", "last_name", "role", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)
