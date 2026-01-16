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

class CanViewTask(BasePermission):
    """
    Admin: can view all tasks
    User: can view only tasks assigned to them
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role == UserRoleChoices.ADMIN:
            return True

        return obj.assignee == user


class CanUpdateTask(BasePermission):
    """
    Admin: can update own tasks and tasks assigned to users
    User: can update self tasks and tasks assigned to them
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role == UserRoleChoices.ADMIN:
            return obj.owner == user

        return obj.assignee == user or obj.owner == user


class CanDeleteTask(BasePermission):
    """
    User:
        - can delete only self tasks (owner == assignee == user)

    Admin:
        - can delete only tasks owned by admin
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role == UserRoleChoices.ADMIN:
            return obj.owner == user

        return (
            user.role == UserRoleChoices.USER
            and obj.owner == user
            and obj.assignee == user
        )


class CanViewOrCreateComment(BasePermission):
    """
    Admin:
        - can comment/view only on tasks owned by admin
    User:
        - can comment/view on tasks they own OR are assigned to
    """

    def has_object_permission(self, request, view, obj):
        """
        obj → Task
        """
        user = request.user

        if user.role == UserRoleChoices.ADMIN:
            return obj.owner == user

        return obj.owner == user or obj.assignee == user


class CanUpdateComment(BasePermission):
    """
    User:
        - can update their own comments
    Admin:
        - can update comments only on tasks owned by admin
    """

    def has_object_permission(self, request, view, obj):
        """
        obj → Comment
        """
        user = request.user
        task = obj.task

        if user.role == UserRoleChoices.ADMIN:
            return task.owner == user

        return obj.user == user


class CanDeleteComment(BasePermission):
    """
    User:
        - can delete their own comments
    Admin:
        - can delete comments only on tasks owned by admin
    """

    def has_object_permission(self, request, view, obj):
        """
        obj → Comment
        """
        user = request.user
        task = obj.task

        if user.role == UserRoleChoices.ADMIN:
            return task.owner == user

        return obj.user == user
    


class CanViewTaskHistory(BasePermission):
    """
    Admin:
        - can view history of all tasks
    User:
        - can view history only for tasks assigned to them
    """

    def has_object_permission(self, request, view, obj):
        """
        obj → Task
        """
        user = request.user

        if user.role == UserRoleChoices.ADMIN:
            return True

        return obj.assignee == user
    
    