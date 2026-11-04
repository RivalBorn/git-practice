-- Store registered accounts and their authentication details.
CREATE TABLE IF NOT EXISTS users (
    -- Assign each user a unique integer identifier.
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Require usernames to be unique and present.
    username TEXT NOT NULL UNIQUE,
    -- Require email addresses to be unique and present.
    email TEXT NOT NULL UNIQUE,
    -- Store the password hash, never the plaintext password.
    password_hash TEXT NOT NULL,
    -- Default new accounts to the regular-user role.
    role TEXT NOT NULL DEFAULT 'user'
);

-- Store recipes and associate each one with its owner.
CREATE TABLE IF NOT EXISTS recipes (
    -- Assign each recipe a unique integer identifier.
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Store the recipe's required display title.
    title TEXT NOT NULL,
    -- Store the required ingredient description.
    ingredients TEXT NOT NULL,
    -- Store the required cooking duration in minutes.
    cook_time_minutes INTEGER NOT NULL,
    -- Reference the account that owns this recipe.
    user_id INTEGER NOT NULL,
    -- Store optional preparation or serving notes.
    notes TEXT,
    -- Enforce that each recipe owner exists in the users table.
    FOREIGN KEY (user_id) REFERENCES users (id)
);