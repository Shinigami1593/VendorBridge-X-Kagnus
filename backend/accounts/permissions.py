from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):
    roles = ()

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in self.roles


class IsAdmin(RolePermission):
    roles = ('admin',)


class IsAdminOrOfficer(RolePermission):
    roles = ('admin', 'officer')


class IsAdminOrOfficerOrManager(RolePermission):
    roles = ('admin', 'officer', 'manager')
