from rest_framework import permissions


class IsRoommatePostOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.posted_by_id == request.user.id
