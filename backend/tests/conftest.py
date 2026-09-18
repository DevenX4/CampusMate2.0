import os

# Real environment variables take precedence over .env, so tests use these values
# regardless of what a developer has in their local .env. Set before importing the app.
os.environ.update(
    APP_ENV="test",
    DB_HOST="localhost",
    DB_PORT="5432",
    DB_NAME="campusmate_test",
    DB_USER="campusmate_app",
    DB_PASSWORD="test-password",
)
