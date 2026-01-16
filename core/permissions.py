from rest_framework.permissions import BasePermission
from core.choices import UserRoleChoices



class IsSuperAdmin(BasePermission):
    """
    Allows access only to SUPER_ADMIN users.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRoleChoices.SUPER_ADMIN
        )
    

class IsAdmin(BasePermission):
    """
    Allows access only to admin users.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRoleChoices.ADMIN
        )


class IsAdminOrSelf(BasePermission):
    """
    Allows access if user is admin OR accessing their own object.
    Assumes the object has `id` attribute.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRoleChoices.ADMIN:
            return True

        return obj == request.user




def CommentOnTask(user, task):
    if user.role == UserRoleChoices.ADMIN:
        return task.owner == user

    return task.owner == user or task.assignee == user


def DeleteTaskcomment(user, task, comment):
    if user.role == UserRoleChoices.ADMIN:
        return task.owner == user

    return comment.user == user
