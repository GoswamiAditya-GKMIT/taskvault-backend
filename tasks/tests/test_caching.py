from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from tasks.models import Task
from users.models import Organization
from django.core.cache import cache
import time

User = get_user_model()

class TaskCachingTests(APITestCase):
    def setUp(self):
        # Clear cache before tests
        cache.clear()

        # Create Organization
        self.organization = Organization.objects.create(name="Test Org")
        self.other_organization = Organization.objects.create(name="Other Org")

        # Create Users
        self.admin = User.objects.create_user(
            username="admin", 
            email="admin@example.com", 
            password="password",
            role="TENANT_ADMIN",
            organization=self.organization
        )
        self.user = User.objects.create_user(
            username="user", 
            email="user@example.com", 
            password="password",
            role="USER",
            organization=self.organization
        )
        self.other_tenant_admin = User.objects.create_user(
            username="other_admin", 
            email="other@example.com", 
            password="password",
            role="TENANT_ADMIN",
            organization=self.other_organization
        )

        # Create Task
        self.task = Task.objects.create(
            title="Test Task",
            description="Description",
            organization=self.organization,
            owner=self.admin,
            assignee=self.user,
            status="TODO",
            priority="MEDIUM"
        )

        self.url = "/api/v1/tasks/"

    def test_caching_behavior(self):
        self.client.force_authenticate(user=self.admin)

        # 1. First Request (Cache Miss)
        start_time = time.time()
        response1 = self.client.get(self.url)
        end_time = time.time()
        duration1 = end_time - start_time
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # 2. Second Request (Cache Hit)
        # We can't easily rely on timing in tests, but we can check if the code path works
        # Ideally we'd mock the cache, but integration testing with real redis/locmem is fine.
        start_time = time.time()
        response2 = self.client.get(self.url)
        end_time = time.time()
        duration2 = end_time - start_time
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data, response2.data)

        # 3. Invalidation (Update Task)
        # Updating the task should trigger the signal and invalidate the cache
        self.task.title = "Updated Task"
        self.task.save()

        # 4. Third Request (Cache Miss / New Data)
        response3 = self.client.get(self.url)
        self.assertEqual(response3.status_code, status.HTTP_200_OK)
        # Verify that we got the updated data
        self.assertEqual(response3.data['data'][0]['title'], "Updated Task")

    def test_tenant_isolation(self):
        # Authenticate as Org 1 Admin and populate cache
        self.client.force_authenticate(user=self.admin)
        self.client.get(self.url)

        # Authenticate as Org 2 Admin and populate cache
        self.client.force_authenticate(user=self.other_tenant_admin)
        response_other = self.client.get(self.url)
        self.assertEqual(len(response_other.data['data']), 0) # Should verify empty list for new org

        # Update Org 1 Task -> Should NOT invalidate Org 2 Cache
        # (Though actually, we want to know if Org 2 cache is independent. 
        # Modifying Org 1 data shouldn't affect Org 2 keys)
        
        # Checking if keys are different
        key1 = f"previous_cache_version:{self.organization.id}"
        key2 = f"previous_cache_version:{self.other_organization.id}"
        
        # They should be managed independently.
        # But implicitly, the cache key generation includes the org ID, so they are isolated.
        
        # Let's verify that updating Org 1 task doesn't change Org 2's data view
        # (which is obvious by DB isolation, but also cache shouldn't bleed)
        self.task.save() # Updates Org 1
        
        self.client.force_authenticate(user=self.other_tenant_admin)
        response_other_again = self.client.get(self.url)
        self.assertEqual(len(response_other_again.data['data']), 0)

