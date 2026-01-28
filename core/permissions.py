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
    

class IsTenantAdmin(BasePermission):
    """
    Allows access only to admin users of an ACTIVE organization.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role == UserRoleChoices.TENANT_ADMIN):
            return False
        
        # Block if Org is inactive
        if user.organization and not user.organization.is_active:
            return False
            
        return True

class IsTenantAdminOrSuperAdmin(BasePermission):
    """
    Allows access to both SUPER_ADMIN and TENANT_ADMIN users.
    TENANT_ADMIN blocked if organization is inactive.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.role == UserRoleChoices.SUPER_ADMIN:
             return True

        if user.role == UserRoleChoices.TENANT_ADMIN:
            # Block if Org is inactive
            if user.organization and not user.organization.is_active:
                return False
            return True
            
        return False

class CanViewTask(BasePermission):
    """
    SUPER_ADMIN:
        - no access
    TENANT_ADMIN:
        - can view all tasks (if Org is active)
    USER:
        - can view tasks they own or are assigned to (if Org is active)
    """

    def has_permission(self, request, view):
        user = request.user
        if user.role == UserRoleChoices.SUPER_ADMIN:
            return False
        
        # Block if Org is inactive
        if user.organization and not user.organization.is_active:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role == UserRoleChoices.TENANT_ADMIN:
            return True

        if user.role == UserRoleChoices.USER:
            return obj.owner == user or obj.assignee == user

        return False

class CanCreateTask(BasePermission):
    """
    SUPER_ADMIN:
        - no access
    TENANT_ADMIN:
        - can create tasks (if Org is active)
    USER:
        - can create tasks (if Org is active)
    """

    def has_permission(self, request, view):
        user = request.user
        if user.role == UserRoleChoices.SUPER_ADMIN:
            return False

        # Block if Org is inactive
        if user.organization and not user.organization.is_active:
            return False

        return True


class CanUpdateTask(BasePermission):
    """
    SUPER_ADMIN:
        - no access
    TENANT_ADMIN:
        - can update any task
    USER:
        - can update tasks they own or are assigned to
    """

    def has_permission(self, request, view):
        if request.method not in ['PUT', 'PATCH']:
            # Let CanViewTask handle GET, etc., or CanDeleteTask handle DELETE
            return True
        return request.user.role != UserRoleChoices.SUPER_ADMIN

    def has_object_permission(self, request, view, obj):
        if request.method not in ['PUT', 'PATCH']:
             return True
             
        user = request.user

        if user.role == UserRoleChoices.TENANT_ADMIN:
            return True

        if user.role == UserRoleChoices.USER:
            return obj.owner == user or obj.assignee == user

        return False




class CanDeleteTask(BasePermission):
    """
    SUPER_ADMIN:
        - no access
    TENANT_ADMIN:
        - can delete any task
    USER:
        - can delete ONLY tasks they own
        - cannot delete assigned tasks
    """

    def has_permission(self, request, view):
        if request.method != 'DELETE':
             return True
        return request.user.role != UserRoleChoices.SUPER_ADMIN

    def has_object_permission(self, request, view, obj):
        # Ignore checks if not DELETE
        if request.method != 'DELETE':
             return True

        user = request.user

        if user.role == UserRoleChoices.TENANT_ADMIN:
            return True

        if user.role == UserRoleChoices.USER:
            return obj.owner == user  # only owner

        return False






class CanViewOrCreateComment(BasePermission):
    """
    Controls viewing & creating comments.
    Supports checking permissions against a Task object OR a Comment object.
    
    If obj is Comment, it checks permission on obj.task.
    """

    def has_permission(self, request, view):
        # SUPER_ADMIN blocked globally
        return request.user.role != UserRoleChoices.SUPER_ADMIN

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role == UserRoleChoices.TENANT_ADMIN:
            return True

        if user.role == UserRoleChoices.USER:
            # Handle if obj is Comment, get the task
            task = obj
            if hasattr(obj, 'task'):
                task = obj.task
            
            # Access logic: Must be Owner or Assignee of the TASK
            return task.owner == user or task.assignee == user

        return False


class CanUpdateComment(BasePermission):
    """
    Controls updating comments (object = Comment)
    """

    def has_permission(self, request, view):
        return request.user.role != UserRoleChoices.SUPER_ADMIN

    def has_object_permission(self, request, view, obj):
        """
        obj - Comment
        """
        user = request.user

        if user.role == UserRoleChoices.TENANT_ADMIN:
            return True

        if user.role == UserRoleChoices.USER:
            return obj.user == user

        return False


class CanDeleteComment(BasePermission):
    """
    Controls deleting comments (object = Comment)
    """

    def has_permission(self, request, view):
        return request.user.role != UserRoleChoices.SUPER_ADMIN

    def has_object_permission(self, request, view, obj):
        """
        obj - Comment
        """
        user = request.user

        if user.role == UserRoleChoices.TENANT_ADMIN:
            return True

        if user.role == UserRoleChoices.USER:
            return obj.user == user

        return False

    


class CanViewTaskHistory(BasePermission):
    """
    Admin:
        - can view history of all tasks
    User:
        - can view history of tasks they own or are assigned to
    """

    def has_permission(self, request, view):
        return request.user.role != UserRoleChoices.SUPER_ADMIN

    def has_object_permission(self, request, view, obj):
        """
        obj - Task
        """
        user = request.user

        if user.role == UserRoleChoices.SUPER_ADMIN:
            return False

        if user.role == UserRoleChoices.TENANT_ADMIN:
            return True


        return obj.owner == user or obj.assignee == user
    
    
class CanAccessUser(BasePermission):
    """
    Custom permission to handle User detail access.
    
    Rules:
    1. User can access themselves.
    2. SUPER_ADMIN can access TENANT_ADMIN.
    3. TENANT_ADMIN can access Users in their own organization.
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # 1. Allow Self Access
        if obj == user:
            return True
            
        # 2. Super Admin -> Tenant Admin
        if user.role == UserRoleChoices.SUPER_ADMIN:
            return obj.role == UserRoleChoices.TENANT_ADMIN
            
        # 3. Tenant Admin -> Org User
        if user.role == UserRoleChoices.TENANT_ADMIN:
            # Must be in same organization
            if obj.organization != user.organization:
                return False

            return True 
            
        return False


class CanRestoreUser(BasePermission):
    """
    Controls user restoration logic.
    SUPER_ADMIN:
        - can only restore TENANT_ADMIN
    TENANT_ADMIN:
        - can only restore USER within their own organization
    """
    
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
             return False
        
        # Block if Org is inactive (Standard Tenant check)
        if user.role == UserRoleChoices.TENANT_ADMIN:
             if user.organization and not user.organization.is_active:
                 return False

        return True

    def has_object_permission(self, request, view, obj):
        actor = request.user
        target_user = obj
        
        # 1. Tenant Admin -> Can only restore Users in same Org
        if actor.role == UserRoleChoices.TENANT_ADMIN:
            if target_user.role != UserRoleChoices.USER:
                return False
            if target_user.organization != actor.organization:
                return False
            return True
            
        # 2. Super Admin -> Can only restore Tenant Admins
        if actor.role == UserRoleChoices.SUPER_ADMIN:
            return target_user.role == UserRoleChoices.TENANT_ADMIN
            
        return False

        
class CanDeleteUser(BasePermission):
    """
    Controls user deletion logic.
    RULES:
    1. Users can delete themselves.
    2. SUPER_ADMIN can only delete TENANT_ADMIN (if Org is Active).
    3. TENANT_ADMIN can only delete USER (Same Org).
    """

    def has_object_permission(self, request, view, obj):
        # Allow non-DELETE methods to pass through (handled by other classes)
        if request.method != 'DELETE':
            return True

        actor = request.user
        target_user = obj

        # 1. Self Deletion
        if actor == target_user:
            return True

        # 2. Super Admin Logic
        if actor.role == UserRoleChoices.SUPER_ADMIN:
            # Can only delete Tenant Admin
            if target_user.role != UserRoleChoices.TENANT_ADMIN:
                return False
            
            # Block if Target Org is Deactivated
            if target_user.organization and not target_user.organization.is_active:
                return False
                
            return True

        # 3. Tenant Admin Logic
        if actor.role == UserRoleChoices.TENANT_ADMIN:
            # Can only delete User
            if target_user.role != UserRoleChoices.USER:
                return False
            
            # Must be same Org
            if target_user.organization != actor.organization:
                return False
                
            return True

        return False