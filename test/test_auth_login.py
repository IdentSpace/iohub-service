import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.auth_routes import router
from app.db.models import ApiKey, User


class LoginTests(unittest.TestCase):
    def test_login_persists_token_and_rejects_wrong_password(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        try:
            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                user = User(
                    username="admin", password="admin",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                user_id = user.id

            app = FastAPI()
            app.include_router(router, prefix="/auth")
            with patch("app.db.session.get_session", side_effect=lambda: Session(engine)):
                with TestClient(app) as client:
                    response = client.post("/auth/login", json={"username": "admin", "password": "admin"})
                    self.assertEqual(response.status_code, 200)
                    token = response.json()["data"]["access_token"]
                    self.assertTrue(token)
                    rejected = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
                    self.assertEqual(rejected.status_code, 400)
            with Session(engine) as session:
                keys = session.exec(select(ApiKey)).all()
                self.assertEqual(len(keys), 1)
                self.assertEqual(keys[0].key, token)
                self.assertEqual(keys[0].user_id, user_id)
                self.assertIsNotNone(keys[0].created_at)
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
