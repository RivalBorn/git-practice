import os
import sqlite3
import tempfile
import unittest

import recipe_api as recipe_app
from init_db import initialize_database


class RecipeOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = os.path.join(self.temp_dir.name, "test.db")
        self.original_database = recipe_app.DATABASE
        recipe_app.DATABASE = self.database
        recipe_app.app.config["JWT_SECRET_KEY"] = (
            "test-secret-that-is-at-least-thirty-two-bytes"
        )
        recipe_app.app.config["JWT_LIFETIME_SECONDS"] = 3600
        initialize_database(self.database)
        self.client = recipe_app.app.test_client()
        self.user_a_token = self.register_and_login("user-a")
        self.user_b_token = self.register_and_login("user-b")

    def tearDown(self):
        recipe_app.DATABASE = self.original_database
        self.temp_dir.cleanup()

    def register_and_login(self, username):
        registration = self.client.post(
            "/register",
            json={"username": username, "password": "test-password-123"},
        )
        self.assertEqual(registration.status_code, 201)
        response = self.client.post(
            "/login",
            json={"username": username, "password": "test-password-123"},
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()["token"]

    @staticmethod
    def auth(token):
        return {"Authorization": f"Bearer {token}"}

    def create_recipe(self, token):
        response = self.client.post(
            "/recipes",
            headers=self.auth(token),
            json={
                "title": "User A recipe",
                "ingredients": "test ingredient",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()["id"]

    def test_only_owner_can_read_update_or_delete_recipe(self):
        recipe_id = self.create_recipe(self.user_a_token)

        owner_list = self.client.get(
            "/recipes", headers=self.auth(self.user_a_token)
        )
        other_user_list = self.client.get(
            "/recipes", headers=self.auth(self.user_b_token)
        )
        self.assertEqual(len(owner_list.get_json()), 1)
        self.assertEqual(other_user_list.get_json(), [])

        forbidden_read = self.client.get(
            f"/recipes/{recipe_id}",
            headers=self.auth(self.user_b_token),
        )
        self.assertEqual(forbidden_read.status_code, 403)
        self.assertEqual(forbidden_read.get_json(), {"error": "forbidden"})
        self.assertEqual(
            self.client.patch(
                f"/recipes/{recipe_id}",
                headers=self.auth(self.user_b_token),
                json={"title": "Changed by User B"},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(
                f"/recipes/{recipe_id}",
                headers=self.auth(self.user_b_token),
            ).status_code,
            404,
        )

        owner_read = self.client.get(
            f"/recipes/{recipe_id}",
            headers=self.auth(self.user_a_token),
        )
        self.assertEqual(owner_read.status_code, 200)
        self.assertEqual(owner_read.get_json()["title"], "User A recipe")

        owner_update = self.client.patch(
            f"/recipes/{recipe_id}",
            headers=self.auth(self.user_a_token),
            json={"title": "Updated by User A"},
        )
        self.assertEqual(owner_update.status_code, 200)
        self.assertEqual(owner_update.get_json()["title"], "Updated by User A")

        owner_delete = self.client.delete(
            f"/recipes/{recipe_id}",
            headers=self.auth(self.user_a_token),
        )
        self.assertEqual(owner_delete.status_code, 204)
        missing_after_delete = self.client.get(
            f"/recipes/{recipe_id}",
            headers=self.auth(self.user_a_token),
        )
        self.assertEqual(missing_after_delete.status_code, 404)
        self.assertEqual(
            missing_after_delete.get_json(), {"error": "recipe not found"}
        )

    def test_get_recipe_returns_json_400_403_and_404(self):
        recipe_id = self.create_recipe(self.user_a_token)

        invalid_id = self.client.get(
            "/recipes/not-an-id", headers=self.auth(self.user_a_token)
        )
        self.assertEqual(invalid_id.status_code, 400)
        self.assertEqual(
            invalid_id.get_json(),
            {"error": "recipe id must be a positive integer"},
        )

        forbidden = self.client.get(
            f"/recipes/{recipe_id}",
            headers=self.auth(self.user_b_token),
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.get_json(), {"error": "forbidden"})

        missing = self.client.get(
            "/recipes/999999", headers=self.auth(self.user_a_token)
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.get_json(), {"error": "recipe not found"})

    def test_recipe_routes_require_a_valid_token(self):
        recipe_id = self.create_recipe(self.user_a_token)
        for response in (
            self.client.get("/recipes"),
            self.client.get(f"/recipes/{recipe_id}"),
            self.client.post(
                "/recipes",
                json={"title": "No token", "ingredients": "none"},
            ),
            self.client.patch(
                f"/recipes/{recipe_id}", json={"title": "No token"}
            ),
            self.client.delete(f"/recipes/{recipe_id}"),
        ):
            self.assertEqual(response.status_code, 401)

    def test_database_initializer_upgrades_existing_recipe_table(self):
        legacy_database = os.path.join(self.temp_dir.name, "legacy.db")
        connection = sqlite3.connect(legacy_database)
        connection.execute(
            "CREATE TABLE recipes ("
            "id INTEGER PRIMARY KEY, title TEXT NOT NULL UNIQUE, "
            "ingredients TEXT NOT NULL, "
            "instructions TEXT NOT NULL DEFAULT '', "
            "is_public INTEGER NOT NULL DEFAULT 1)"
        )
        connection.execute(
            "INSERT INTO recipes (title, ingredients) VALUES (?, ?)",
            ("Legacy recipe", "legacy ingredient"),
        )
        connection.commit()
        connection.close()

        initialize_database(legacy_database)

        connection = sqlite3.connect(legacy_database)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(recipes)")
        }
        owner_id = connection.execute(
            "SELECT owner_id FROM recipes WHERE title = ?",
            ("Legacy recipe",),
        ).fetchone()[0]
        connection.close()
        self.assertIn("owner_id", columns)
        self.assertIsNone(owner_id)


if __name__ == "__main__":
    unittest.main()
