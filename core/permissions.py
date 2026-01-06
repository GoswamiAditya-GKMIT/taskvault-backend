from rest_framework.permissions import BasePermission
from core.choices import UserRoleChoices


class IsAdmin(BasePermission):
    """
    Allows access only to admin users.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRoleChoices.ADMIN
        )


class IsSelf(BasePermission):
    """
    Allows access only to the authenticated user's own object.
    """

    def has_object_permission(self, request, view, obj):
        return obj.id == request.user.id




def CommentOnTask(user, task):
    if user.role == UserRoleChoices.ADMIN:
        return task.owner == user

    return task.owner == user or task.assignee == user


def DeleteTaskcomment(user, task, comment):
    if user.role == UserRoleChoices.ADMIN:
        return task.owner == user

    return comment.user == user
