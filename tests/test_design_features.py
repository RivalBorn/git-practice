import unittest
from uuid import uuid4
from unittest.mock import patch

import httpx
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import cache, db
from app.models import Recipe, User
from app.routes.recipes import list_recipes_for_user


class DesignFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            "testing",
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "RATELIMIT_ENABLED": True,
                "INTERNAL_SERVICE_TOKEN": "test-internal-service-token",
            },
        )
        cls.app.config["JWT_SECRET"] = "test-signing-key-with-at-least-32-bytes"
        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self):
        cache.clear()
        self.client = self.app.test_client()
        self.username = f"user-{uuid4().hex}"
        response = self.client.post(
            "/register",
            json={
                "username": self.username,
                "email": f"{self.username}@example.test",
                "password": "test-password",
            },
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.post(
            "/login",
            json={"username": self.username, "password": "test-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.headers = {
            "Authorization": f"Bearer {response.json['token']}",
            "X-Internal-Service-Token": self.app.config["INTERNAL_SERVICE_TOKEN"],
        }

    def test_recipe_list_requires_valid_jwt_and_internal_service_token(self):
        valid_token = self.headers["Authorization"]
        internal_token = self.app.config["INTERNAL_SERVICE_TOKEN"]

        response = self.client.get(
            "/recipes",
            headers={"X-Internal-Service-Token": internal_token},
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.get(
            "/recipes",
            headers={
                "Authorization": "Bearer invalid",
                "X-Internal-Service-Token": internal_token,
            },
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.get("/recipes", headers={"Authorization": valid_token})
        self.assertEqual(response.status_code, 401)

        response = self.client.get(
            "/recipes",
            headers={
                "Authorization": valid_token,
                "X-Internal-Service-Token": "wrong-token",
            },
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.get("/recipes", headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_recipe_list_cache_is_reused_and_invalidated_by_writes(self):
        with patch(
            "app.routes.recipes.list_recipes_for_user",
            wraps=list_recipes_for_user,
        ) as query:
            response = self.client.get("/recipes", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, [])

            response = self.client.get("/recipes", headers=self.headers)
            self.assertEqual(response.json, [])
            query.assert_called_once()

        response = self.client.post(
            "/recipes",
            headers=self.headers,
            json={
                "title": "Soup",
                "ingredients": "Beans",
                "cook_time_minutes": 30,
                "notes": "Serve warm",
            },
        )
        self.assertEqual(response.status_code, 201)
        recipe_id = response.json["id"]

        response = self.client.get("/recipes", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json[0]["notes"], "Serve warm")

        response = self.client.put(
            f"/recipes/{recipe_id}",
            headers=self.headers,
            json={
                "title": "Bean Soup",
                "ingredients": "Beans, water",
                "cook_time_minutes": 35,
                "notes": "Updated",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["notes"], "Updated")

        response = self.client.get("/recipes", headers=self.headers)
        self.assertEqual(response.json[0]["title"], "Bean Soup")

        response = self.client.delete(
            f"/recipes/{recipe_id}",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/recipes", headers=self.headers).json, [])

    def test_registration_is_rate_limited(self):
        for attempt in range(5):
            response = self.client.post(
                "/register",
                json={},
                environ_base={"REMOTE_ADDR": "192.0.2.55"},
            )
            self.assertEqual(response.status_code, 400, attempt)

        response = self.client.post(
            "/register",
            json={},
            environ_base={"REMOTE_ADDR": "192.0.2.55"},
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json, {"error": "rate limit exceeded"})

    def test_recipe_reads_are_not_rate_limited(self):
        for _ in range(6):
            response = self.client.get("/recipes", headers=self.headers)
            self.assertEqual(response.status_code, 200)

    def test_recipe_foreign_key_without_orm_relationships(self):
        with self.app.app_context():
            user = User.query.filter_by(username=self.username).one()
            recipe = Recipe(
                title="Pasta",
                ingredients="Pasta",
                cook_time_minutes=15,
                user_id=user.id,
            )
            db.session.add(recipe)
            db.session.commit()
            self.assertEqual(recipe.user_id, user.id)

            db.session.add(
                Recipe(
                    title="Invalid",
                    ingredients="None",
                    cook_time_minutes=1,
                    user_id=-1,
                )
            )
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_gateway_checks_jwt_before_forwarding_to_recipe_service(self):
        gateway = create_app(
            "testing",
            {
                "TESTING": True,
                "JWT_SECRET": self.app.config["JWT_SECRET"],
                "INTERNAL_SERVICE_TOKEN": self.app.config["INTERNAL_SERVICE_TOKEN"],
                "USERS_SERVICE_URL": "http://users.test",
                "RECIPES_SERVICE_URL": "http://recipes.test",
            },
            service="gateway",
        )
        gateway.config["JWT_SECRET"] = self.app.config["JWT_SECRET"]
        gateway_client = gateway.test_client()

        with patch("app.routes.gateway.httpx.request") as downstream:
            response = gateway_client.get("/recipes")
            self.assertEqual(response.status_code, 401)
            downstream.assert_not_called()

            downstream.return_value = httpx.Response(200, json=[])
            response = gateway_client.get("/recipes", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            downstream.assert_called_once()
            self.assertEqual(
                downstream.call_args.kwargs["headers"]["X-Internal-Service-Token"],
                self.app.config["INTERNAL_SERVICE_TOKEN"],
            )

        recipe_service = create_app(
            "testing",
            {
                "TESTING": True,
                "JWT_SECRET": "different-service-signing-key-at-least-32-bytes",
                "INTERNAL_SERVICE_TOKEN": self.app.config["INTERNAL_SERVICE_TOKEN"],
            },
            service="recipes",
        )
        recipe_service.config["JWT_SECRET"] = (
            "different-service-signing-key-at-least-32-bytes"
        )
        response = recipe_service.test_client().get(
            "/recipes",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 401)

    def test_gateway_timeout_returns_gateway_timeout(self):
        gateway = create_app(
            "testing",
            {
                "TESTING": True,
                "JWT_SECRET": self.app.config["JWT_SECRET"],
                "INTERNAL_SERVICE_TOKEN": self.app.config["INTERNAL_SERVICE_TOKEN"],
                "DOWNSTREAM_TIMEOUT_SECONDS": 0.25,
            },
            service="gateway",
        )
        gateway.config["JWT_SECRET"] = self.app.config["JWT_SECRET"]
        with patch(
            "app.routes.gateway.httpx.request",
            side_effect=httpx.TimeoutException("timed out"),
        ) as downstream:
            response = gateway.test_client().get(
                "/recipes",
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 504)
        self.assertEqual(downstream.call_args.kwargs["timeout"], 0.25)
        self.assertEqual(
            response.json,
            {"error": "downstream timeout", "service": "recipes"},
        )

    def test_gateway_health_reports_gateway_status(self):
        gateway = create_app(
            "testing",
            {"TESTING": True},
            service="gateway",
        )
        response = gateway.test_client().get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {"status": "ok", "service": "gateway"},
        )

    def test_gateway_me_forwards_jwt_to_users_service(self):
        gateway = create_app(
            "testing",
            {
                "TESTING": True,
                "JWT_SECRET": self.app.config["JWT_SECRET"],
                "INTERNAL_SERVICE_TOKEN": self.app.config["INTERNAL_SERVICE_TOKEN"],
                "USERS_SERVICE_URL": "http://users.test",
                "RECIPES_SERVICE_URL": "http://recipes.test",
                "DOWNSTREAM_TIMEOUT_SECONDS": 0.6,
            },
            service="gateway",
        )
        gateway.config["JWT_SECRET"] = self.app.config["JWT_SECRET"]
        with patch(
            "app.routes.gateway.httpx.get",
            side_effect=[
                httpx.Response(
                    200,
                    json={"id": 7, "username": "alice", "role": "user"},
                ),
                httpx.Response(200, json=[{"id": 12, "title": "Soup"}]),
            ],
        ) as downstream:
            response = gateway.test_client().get("/me", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {
                "user": {"id": 7, "username": "alice", "role": "user"},
                "user_status": "ok",
                "recipes": [{"id": 12, "title": "Soup"}],
                "recipes_status": "ok",
            },
        )
        user_call = downstream.call_args_list[0]
        self.assertEqual(user_call.args[0], "http://users.test/me")
        self.assertEqual(
            user_call.kwargs["headers"]["Authorization"],
            self.headers["Authorization"],
        )
        self.assertEqual(user_call.kwargs["timeout"], 0.6)
        recipe_call = downstream.call_args_list[1]
        self.assertEqual(recipe_call.args[0], "http://recipes.test/recipes")
        self.assertEqual(
            recipe_call.kwargs["headers"]["Authorization"],
            self.headers["Authorization"],
        )
        self.assertEqual(
            recipe_call.kwargs["headers"]["X-Internal-Service-Token"],
            self.app.config["INTERNAL_SERVICE_TOKEN"],
        )
        self.assertEqual(recipe_call.kwargs["timeout"], 0.6)

    def test_gateway_me_requires_jwt_before_calling_users_service(self):
        gateway = create_app(
            "testing",
            {"TESTING": True, "JWT_SECRET": self.app.config["JWT_SECRET"]},
            service="gateway",
        )
        with patch("app.routes.gateway.httpx.get") as downstream:
            response = gateway.test_client().get("/me")
        self.assertEqual(response.status_code, 401)
        downstream.assert_not_called()

    def test_gateway_me_marks_users_timeout_and_connection_failure(self):
        gateway = create_app(
            "testing",
            {
                "TESTING": True,
                "JWT_SECRET": self.app.config["JWT_SECRET"],
                "INTERNAL_SERVICE_TOKEN": self.app.config["INTERNAL_SERVICE_TOKEN"],
                "USERS_SERVICE_URL": "http://users.test",
                "RECIPES_SERVICE_URL": "http://recipes.test",
            },
            service="gateway",
        )
        gateway.config["JWT_SECRET"] = self.app.config["JWT_SECRET"]
        client = gateway.test_client()
        cases = (
            (httpx.TimeoutException("timed out"), "timeout"),
            (httpx.ConnectError("connection failed"), "unavailable"),
        )
        for error, expected_status in cases:
            with self.subTest(user_status=expected_status):
                with patch(
                    "app.routes.gateway.httpx.get",
                    side_effect=[
                        error,
                        httpx.Response(200, json=[]),
                    ],
                ):
                    response = client.get("/me", headers=self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.json["user"])
                self.assertEqual(response.json["user_status"], expected_status)
                self.assertEqual(response.json["recipes"], [])
                self.assertEqual(response.json["recipes_status"], "ok")

    def test_gateway_me_reports_recipes_timeout_unavailable_and_auth_failure(self):
        gateway = create_app(
            "testing",
            {
                "TESTING": True,
                "JWT_SECRET": self.app.config["JWT_SECRET"],
                "INTERNAL_SERVICE_TOKEN": self.app.config["INTERNAL_SERVICE_TOKEN"],
                "USERS_SERVICE_URL": "http://users.test",
                "RECIPES_SERVICE_URL": "http://recipes.test",
            },
            service="gateway",
        )
        gateway.config["JWT_SECRET"] = self.app.config["JWT_SECRET"]
        cases = (
            (httpx.TimeoutException("timed out"), "timeout"),
            (httpx.ConnectError("connection failed"), "unavailable"),
            (httpx.Response(401, json={"error": "unauthorized"}), "auth_failed"),
        )
        for recipe_result, expected_status in cases:
            with self.subTest(recipes_status=expected_status):
                with patch(
                    "app.routes.gateway.httpx.get",
                    side_effect=[
                        httpx.Response(200, json={"id": 7}),
                        recipe_result,
                    ],
                ) as downstream:
                    response = gateway.test_client().get(
                        "/me",
                        headers=self.headers,
                    )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["user_status"], "ok")
                self.assertIsNone(response.json["recipes"])
                self.assertEqual(response.json["recipes_status"], expected_status)
                recipe_call = downstream.call_args_list[1]
                self.assertEqual(
                    recipe_call.kwargs["headers"]["X-Internal-Service-Token"],
                    self.app.config["INTERNAL_SERVICE_TOKEN"],
                )

    def test_gateway_dependency_health_marks_unavailable_service_as_partial(self):
        gateway = create_app(
            "testing",
            {
                "TESTING": True,
                "INTERNAL_SERVICE_TOKEN": self.app.config["INTERNAL_SERVICE_TOKEN"],
                "USERS_SERVICE_URL": "http://users.test",
                "RECIPES_SERVICE_URL": "http://recipes.test",
            },
            service="gateway",
        )
        with patch(
            "app.routes.gateway.httpx.get",
            side_effect=[
                httpx.Response(200),
                httpx.TimeoutException("timed out"),
            ],
        ):
            response = gateway.test_client().get("/health/dependencies")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["status"], "partial")
        self.assertTrue(response.json["partial"])
        self.assertEqual(response.json["services"]["users"]["status"], "ok")
        self.assertEqual(
            response.json["services"]["recipes"],
            {"status": "unavailable", "error": "timeout"},
        )

    def test_dashboard_returns_recipes_when_user_service_times_out(self):
        gateway = create_app(
            "testing",
            {
                "TESTING": True,
                "INTERNAL_SERVICE_TOKEN": self.app.config["INTERNAL_SERVICE_TOKEN"],
                "USERS_SERVICE_URL": "http://users.test",
                "RECIPES_SERVICE_URL": "http://recipes.test",
            },
            service="gateway",
        )
        gateway.config["JWT_SECRET"] = self.app.config["JWT_SECRET"]
        with patch(
            "app.routes.gateway.httpx.get",
            side_effect=[
                httpx.Response(200, json=[{"id": 7, "title": "Soup"}]),
                httpx.TimeoutException("timed out"),
            ],
        ):
            response = gateway.test_client().get(
                "/dashboard",
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["partial"])
        self.assertEqual(response.json["recipes"], [{"id": 7, "title": "Soup"}])
        self.assertIsNone(response.json["user"])
        self.assertEqual(response.json["errors"], {"user": "timeout"})
