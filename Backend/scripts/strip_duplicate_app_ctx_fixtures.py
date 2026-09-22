#!/usr/bin/env python
"""Elimina fixtures app_ctx locales simples que sombrean conftest.app_ctx (JWT)."""
from __future__ import annotations

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TESTS = BACKEND / "tests"

PATTERNS = [
    re.compile(
        r"@pytest\.fixture\s*\n"
        r"def app_ctx\(\):\s*\n"
        r"    from app import create_app\s*\n"
        r"\s*\n?"
        r"    app = create_app\(\)\s*\n"
        r"    with app\.app_context\(\):\s*\n"
        r"        yield app\s*\n"
        r"        db\.session\.rollback\(\)\s*\n",
        re.MULTILINE,
    ),
    re.compile(
        r"@pytest\.fixture\s*\n"
        r"def app_ctx\(app\):\s*\n"
        r"    with app\.app_context\(\):\s*\n"
        r"        yield app\s*\n"
        r"        db\.session\.rollback\(\)\s*\n",
        re.MULTILINE,
    ),
    re.compile(
        r"@pytest\.fixture\s*\n"
        r"def app_ctx\(app, actor_user_id\):\s*\n"
        r"    from flask_jwt_extended import create_access_token, verify_jwt_in_request\s*\n"
        r"\s*\n?"
        r"    with app\.app_context\(\):\s*\n"
        r"        token = create_access_token\(identity=str\(actor_user_id\)\)\s*\n"
        r"        with app\.test_request_context\(\s*\n"
        r'            "/", headers=\{"Authorization": f"Bearer \{token\}"\}\s*\n'
        r"        \):\s*\n"
        r"            verify_jwt_in_request\(\)\s*\n"
        r"            yield app\s*\n"
        r"            db\.session\.rollback\(\)\s*\n",
        re.MULTILINE,
    ),
]

SKIP = {
    "test_relevadores_relevamiento.py",  # custom, already jwt
}


def main() -> None:
    changed = 0
    for path in sorted(TESTS.rglob("test_*.py")):
        if path.name in SKIP:
            continue
        text = path.read_text(encoding="utf-8")
        new = text
        for pat in PATTERNS:
            new = pat.sub("", new)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print(path.relative_to(BACKEND))
    print(f"stripped={changed}")


if __name__ == "__main__":
    main()
