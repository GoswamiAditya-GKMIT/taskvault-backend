from locust import HttpUser, task, between, events
import random
import os

class LoadTestUser(HttpUser):
    wait_time = between(1, 3)
    tokens = []

    def on_start(self):
        """
        Load tokens from the generated file on start.
        """
        token_file = "locust_tokens.txt"
        if os.path.exists(token_file):
            with open(token_file, "r") as f:
                self.tokens = [line.strip() for line in f.readlines()]
        else:
            print(f"WARNING: {token_file} not found. Authenticated tasks will fail.")

    @task(1)
    def health_check(self):
        """
        Unauthenticated task: Hit the health check API.
        """
        self.client.get("/api/v1/health/")

    @task(3)
    def get_user_me(self):
        """
        Authenticated task: Get current user profile.
        """
        if not self.tokens:
            return
        
        token = random.choice(self.tokens)
        headers = {"Authorization": f"Bearer {token}"}
        self.client.get("/api/v1/users/me/", headers=headers)

    @task(2)
    def list_tasks(self):
        """
        Authenticated task: List tasks.
        """
        if not self.tokens:
            return
        
        token = random.choice(self.tokens)
        headers = {"Authorization": f"Bearer {token}"}
        self.client.get("/api/v1/tasks/", headers=headers)
