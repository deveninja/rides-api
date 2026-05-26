from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from rides.models import Ride, RideEvent, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "role", "is_staff", "is_active"]
    list_filter = ["role", "is_staff", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "phone_number", "role")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = ["date_joined"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]
    list_per_page = 20
    fieldsets = tuple(fieldsets)


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ["id_ride", "status", "rider", "driver", "pickup_time"]
    list_filter = ["status", "pickup_time"]
    search_fields = ["rider__email", "driver__email", "status"]
    autocomplete_fields = ["rider", "driver"]


@admin.register(RideEvent)
class RideEventAdmin(admin.ModelAdmin):
    list_display = ["id_ride_event", "ride", "description", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["description", "ride__id_ride"]
    autocomplete_fields = ["ride"]
