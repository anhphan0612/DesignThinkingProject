from rest_framework import permissions


class IsRoomOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return (
            request.user.is_authenticated
            and hasattr(request.user, "landlord_profile")
            and obj.landlord_id == request.user.landlord_profile.id
        )

