from locust import HttpUser, between, task


class AgentGuardReadOnlyUser(HttpUser):
    wait_time = between(0.05, 0.15)

    @task(3)
    def readonly_agent(self):
        self.client.post("/api/agent/run", json={"user_input": "查询虚构账户 ACC-001", "user_role": "customer", "actor_id": "CUST-001", "target_object": "ACC-001"}, name="POST /api/agent/run read-only")

    @task(2)
    def trace_history(self):
        self.client.get("/api/traces?limit=10", name="GET /api/traces")

    @task(2)
    def evaluation_history(self):
        self.client.get("/api/evaluations/runs", name="GET /api/evaluations/runs")

