import unittest
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import cache, db
from app.models import Recipe, User


class DesignFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            "testing",
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "RATELIMIT_ENABLED": True,
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
        self.headers = {"Authorization": f"Bearer {response.json['token']}"}

    def test_recipe_list_cache_is_reused_and_invalidated_by_writes(self):
        with patch(
            "app.routes.recipes.db.session.get",
            wraps=db.session.get,
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
