from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.cache import cache
import uuid
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.password_validation import validate_password


from users.serializers import (
    UserListDetailSerializer,
    UserUpdateSerializer,
    UserCreateSerializer,
    InviteUserSerializer,
    ForgotPasswordSerializer

)
from core.permissions import IsAdminOrSelf , IsTenantAdminOrSuperAdmin , IsTenantAdmin
from core.pagination import DefaultPagination
from users.services import soft_delete_user
from core.utils import generate_otp
from users.tasks import send_user_verification_otp , send_user_invite_email , send_password_reset_email, send_verification_link_email
from core.choices import UserRoleChoices
from core.constants import CACHE_TIMEOUT , INVITE_LINK_EXPIRY , PASSWORD_RESET_TTL


User = get_user_model()  #getting user model inherited from abstractuser

class UserListCreateAPIView(APIView):
    """
    GET  /users  -> List users
    POST /users  -> Create user (SUPER_ADMIN / TENANT_ADMIN only)
    """

    permission_classes = [IsAuthenticated , IsTenantAdminOrSuperAdmin]

    def get_queryset(self, request):
        """
        Tenant-aware queryset
        """
        user = request.user

        qs = User.objects.filter(
            deleted_at__isnull=True,
            is_email_verified=True,
        )

        # SUPER_ADMIN can see all users
        if user.role == UserRoleChoices.SUPER_ADMIN:
            return qs

        # TENANT_ADMIN can see only users of their organization
        return qs.filter(organization=user.organization)

    # ---------- GET /users ----------
    def get(self, request):
        queryset = self.get_queryset(request).order_by("first_name", "last_name")

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = UserListDetailSerializer(page, many=True)

        response_data = {
            "status": "success",
            "message": "Users retrieved successfully",
            "data": serializer.data,
        }

        response_data.update(paginator.get_root_pagination_data())

        return Response(response_data, status=status.HTTP_200_OK)

    # ---------- POST /users ----------
    def post(self, request):
        serializer = UserCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        # Generate Verification Token
        token = uuid.uuid4().hex
        
        # Store token -> user_id in cache with 24h expiry
        cache_key = f"user_verification_token:{token}"
        # Store user_id -> token for invalidation on resend
        user_token_key = f"user_verification_active_token:{user.id}"

        cache.set(cache_key, user.id, timeout=86400) # 24 hours
        cache.set(user_token_key, token, timeout=86400) 

        verification_link = f"http://localhost:3000/verify-email?token={token}"

        send_verification_link_email.delay(user.email, verification_link)

        return Response(
            {
                "status": "success",
                "message": "User created successfully. Verification link sent to email.",
                "data": UserListDetailSerializer(user).data
            },
            status=status.HTTP_201_CREATED,
        )
    
class UserDetailUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSelf]    # IsAdminOrSelf - admin or self user(logged in user) 

    def get_object(self, request, id):
        user = get_object_or_404(
            User,
            id=id,
            deleted_at__isnull=True
        )
        self.check_object_permissions(request, user)
        return user

    def get(self, request, id):
        user = self.get_object(request, id)

        serializer = UserListDetailSerializer(user)
        return Response(
            {
                "status": "success",
                "message": "User retrieved successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, id):
        user = self.get_object(request, id)

        serializer = UserUpdateSerializer(
            instance=user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)

        updated_user = serializer.save()

        return Response(
            {
                "status": "success",
                "message": "User updated successfully",
                "data": UserListDetailSerializer(updated_user).data,
            },
            status=status.HTTP_200_OK,
        )

    #To do - in future - admin can restore the user and all its attributes including the tasks and all
            # or admin can allow to remove the user (hard delete) and recreate the new user 
            # or can just use patch and remove all the associated item and pretend to be use the same existing user

    def delete(self, request, id):
        user = self.get_object(request, id)

        soft_delete_user(user)

        return Response(
            {
                "status": "success",
                "message": "User deleted successfully",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )
    


# tenant admin create user invite link and send it through the email
class InviteUserAPIView(APIView):
    """
    POST /users/invite
    Tenant Admin ONLY
    """

    permission_classes = [IsAuthenticated, IsTenantAdmin]

    INVITE_TTL = INVITE_LINK_EXPIRY  # 24 hours

    def post(self, request):
        serializer = InviteUserSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        inviter = request.user
        email = serializer.validated_data["email"]
        organization = inviter.organization

        #  Per-tenant per-email key
        email_key = f"user_invite_email:{organization.id}:{email}"

        # Invalidate old invite (if exists)
        old_token = cache.get(email_key)
        if old_token:
            cache.delete(f"user_invite:{old_token}")
            cache.delete(email_key)

        #  Generate new token
        token = uuid.uuid4().hex

        # Store token → invite data
        cache.set(
            f"user_invite:{token}",
            {
                "email": email,
                "organization_id": str(organization.id),
                "role": UserRoleChoices.USER,
                "invited_by": str(inviter.id),
            },
            timeout=self.INVITE_TTL,
        )

        # Store email → token mapping
        cache.set(
            email_key,
            token,
            timeout=self.INVITE_TTL,
        )

        invite_link = f"http://localhost:3000/invite/{token}"

        send_user_invite_email.delay(email, invite_link)

        return Response(
            {
                "status": "success",
                "message": "Invite link sent successfully.",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordAPIView(APIView):
    """
    POST /auth/forgot-password
    """

    permission_classes = []

    RESET_TTL = PASSWORD_RESET_TTL  # 15 minutes

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(
                email=email,
                is_email_verified=True,
                deleted_at__isnull=True
            )
        except User.DoesNotExist:
            return Response(
                {
                    "status": "success",
                    "message": "If the email exists, a reset link has been sent.",
                    "data": None,
                },
                status=status.HTTP_200_OK,
            )

        user_token_key = f"password_reset_user:{user.id}"

        #  FIXED rate-limit logic
        existing_token = cache.get(user_token_key)

        if existing_token:
            token_key = f"password_reset:{existing_token}"

            if cache.get(token_key):
                # Valid reset already exists → do NOT resend
                return Response(
                    {
                        "status": "success",
                        "message": "If the email exists, a reset link has been sent.",
                        "data": None,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                # Stale mapping → cleanup
                cache.delete(user_token_key)

        # Generate new token
        token = uuid.uuid4().hex

        cache.set(
            f"password_reset:{token}",
            {"user_id": str(user.id)},
            timeout=self.RESET_TTL,
        )

        cache.set(
            user_token_key,
            token,
            timeout=self.RESET_TTL,
        )

        reset_link = f"http://localhost:8000/api/v1/auth/reset-password/{token}"

        send_password_reset_email.delay(user.email, reset_link)

        return Response(
            {
                "status": "success",
                "message": "If the email exists, a reset link has been sent.",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )
    


def reset_password_view(request, token):
    token_key = f"password_reset:{token}"
    data = cache.get(token_key)

    if not data:
        return HttpResponse("Reset link is invalid or expired.", status=400)

    user_id = data["user_id"]
    user = User.objects.get(id=user_id)

    user_token_key = f"password_reset_user:{user.id}"

    if request.method == "GET":
        return render(request, "users/reset_password.html")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(
                request,
                "users/reset_password.html",
                {"error": "Passwords do not match."},
            )

        try:
            validate_password(password, user)
        except ValidationError as e:
            return render(
                request,
                "users/reset_password.html",
                {"error": e.messages[0]},
            )

        user.set_password(password)
        user.save(update_fields=["password"])

        #  Invalidate token + user mapping
        cache.delete(token_key)
        cache.delete(user_token_key)

        return HttpResponse("Password reset successful. You can now log in.")
    

