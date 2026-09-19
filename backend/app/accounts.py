"""Create a user account from the command line, e.g. the very first admin:

    python -m app.accounts create --email admin@campusmate-demo.example --role admin --name "Admin"

The password is typed at a hidden prompt (twice), or read from an environment variable named
with --password-env (for scripts). It is never accepted as a plain command-line argument,
because those end up in shell history and process lists.
"""

import argparse
import getpass
import os
import sys

from pydantic import ValidationError

from app.core.db import SessionLocal
from app.schemas.users import UserCreate
from app.services import users
from app.services.audit import RequestContext
from app.services.errors import ConflictError


def _password(env_var: str | None) -> str:
    if env_var:
        return os.environ[env_var]
    first = getpass.getpass("Password (min. 10 characters): ")
    if first != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.accounts")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create a user")
    create.add_argument("--email", required=True)
    create.add_argument("--role", required=True, choices=["admin", "faculty", "student"])
    create.add_argument("--name", default=None)
    create.add_argument("--password-env", default=None, help="read the password from this environment variable")
    args = parser.parse_args(argv)

    try:
        data = UserCreate(email=args.email, full_name=args.name, role=args.role,
                          password=_password(args.password_env))
    except ValidationError as exc:
        print("Invalid input:", "; ".join(e["msg"] for e in exc.errors()))
        return 1
    with SessionLocal() as db:
        try:
            user = users.create_user(db, data, actor_id=None, context=RequestContext(user_agent="cli"))
        except ConflictError as exc:
            print(exc)
            return 1
    print(f"Created {user.role} account {user.email} (id {user.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
