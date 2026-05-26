from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    message = "Only users with the admin role can access this endpoint."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "admin")
