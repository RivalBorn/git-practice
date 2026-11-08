"""Create or upgrade the recipe database. Run with: python init_db.py"""

import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
"""

RECIPE_SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL UNIQUE,
    ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    is_public INTEGER NOT NULL DEFAULT 1,
    owner_id INTEGER REFERENCES users(id)
);
"""

SEED = [
    (
        "Shakshuka",
        "eggs, tomatoes, peppers, onion, cumin, paprika",
        "Simmer the sauce, crack in the eggs, cover until just set.",
        1,
    ),
    (
        "Overnight oats",
        "rolled oats, milk, yogurt, chia seeds, honey",
        "Stir everything together and refrigerate overnight.",
        1,
    ),
    (
        "Secret family hot sauce",
        "habaneros, garlic, vinegar, a secret ingredient",
        "If we wrote it down here, it wouldn't be a secret.",
        0,
    ),
]

def initialize_database(database):
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        connection.executescript(RECIPE_SCHEMA)

        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(recipes)")
        }
        if "owner_id" not in columns:
            connection.execute(
                "ALTER TABLE recipes ADD COLUMN owner_id "
                "INTEGER REFERENCES users(id)"
            )

        connection.execute(
            "CREATE INDEX IF NOT EXISTS recipes_owner_id_idx "
            "ON recipes(owner_id)"
        )
        existing = connection.execute(
            "SELECT COUNT(*) FROM recipes"
        ).fetchone()[0]
        if existing == 0:
            connection.executemany(
                "INSERT INTO recipes (title, ingredients, instructions, is_public)"
                " VALUES (?, ?, ?, ?)",
                SEED,
            )
            print(f"Created {database} and seeded {len(SEED)} recipes.")
        else:
            print(f"{database} already has {existing} recipes.")
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database(os.environ.get("DATABASE_PATH", "recipes.db"))
