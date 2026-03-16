import factory
from django.contrib.auth import get_user_model
from users.models import Organization
from tasks.models import Task, Comment, TaskHistory
from core.choices import UserRoleChoices, TaskStatusChoices, TaskPriorityChoices

User = get_user_model()

# --- Model Factories ---

class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization
        
    name = factory.Sequence(lambda n: f"Test Organization {n}")
    is_active = True
    is_premium = False

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True
        
    username = factory.Sequence(lambda n: f"testuser_{n}")
    email = factory.Sequence(lambda n: f"testuser_{n}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_email_verified = True
    is_active = True
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted if extracted else "StrongPassword@2026!"
        self.set_password(password)
        if create:
            self.save()

class SuperAdminFactory(UserFactory):
    role = UserRoleChoices.SUPER_ADMIN
    organization = None

class TenantAdminFactory(UserFactory):
    role = UserRoleChoices.TENANT_ADMIN
    organization = factory.SubFactory(OrganizationFactory)

class NormalUserFactory(UserFactory):
    role = UserRoleChoices.USER
    organization = factory.SubFactory(OrganizationFactory)

class TaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Task
        
    organization = factory.SubFactory(OrganizationFactory)
    owner = factory.SubFactory(
        NormalUserFactory, 
        organization=factory.SelfAttribute('..organization')
    )
    assignee = factory.SubFactory(
        NormalUserFactory, 
        organization=factory.SelfAttribute('..organization')
    )
    
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('paragraph')
    status = TaskStatusChoices.PENDING
    priority = TaskPriorityChoices.MEDIUM

class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    organization = factory.SubFactory(OrganizationFactory)
    task = factory.SubFactory(
        TaskFactory, 
        organization=factory.SelfAttribute('..organization')
    )
    user = factory.SubFactory(
        NormalUserFactory, 
        organization=factory.SelfAttribute('..organization')
    )
    message = factory.Faker('sentence')

class TaskHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaskHistory
        
    organization = factory.SubFactory(OrganizationFactory)
    task = factory.SubFactory(
        TaskFactory, 
        organization=factory.SelfAttribute('..organization')
    )
    actor = factory.SubFactory(
        NormalUserFactory, 
        organization=factory.SelfAttribute('..organization')
    )
    old_status = TaskStatusChoices.PENDING
    new_status = TaskStatusChoices.IN_PROGRESS

# --- Payload Factories ---

class TaskPayloadFactory(factory.Factory):
    class Meta:
        model = dict

    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('paragraph')
    status = TaskStatusChoices.PENDING
    priority = TaskPriorityChoices.MEDIUM

class UserPayloadFactory(factory.Factory):
    class Meta:
        model = dict

    username = factory.Sequence(lambda n: f"username_{n:03d}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")
    password = "StrongPassword@2026!"
    confirm_password = "StrongPassword@2026!"
    first_name = "John"
    last_name = "Doe"
    role = "USER"

class LoginPayloadFactory(factory.Factory):
    class Meta:
        model = dict
    
    username = ""
    password = ""

class OrganizationPayloadFactory(factory.Factory):
    class Meta:
        model = dict
    
    name = factory.Sequence(lambda n: f"New Org {n}")
