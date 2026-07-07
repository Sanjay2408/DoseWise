"""
Authentication for DoseWise: registration, login, and JWT verification.

- Passwords are hashed with bcrypt (never stored in plain text).
- Sessions use signed JWTs (HS256). Set JWT_SECRET in the environment for
  production; otherwise a secret is generated once and kept in
  app/storage/.jwt_secret so tokens survive restarts.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from app.storage import db

TOKEN_TTL_HOURS = int(os.environ.get("JWT_TTL_HOURS", "72"))
_SECRET_FILE = Path(__file__).resolve().parent / "storage" / ".jwt_secret"


def _get_secret() -> str:
    env_secret = os.environ.get("JWT_SECRET", "").strip()
    if env_secret:
        return env_secret
    if _SECRET_FILE.exists():
        stored = _SECRET_FILE.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    generated = secrets.token_hex(32)
    _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_FILE.write_text(generated, encoding="utf-8")
    return generated


_JWT_SECRET = _get_secret()
_ALGORITHM = "HS256"

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _issue_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI dependency: resolve the Bearer token to a user record (401 otherwise)."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    try:
        payload = jwt.decode(credentials.credentials, _JWT_SECRET, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    user = db.get_user_by_id(str(payload.get("sub") or ""))
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found. Please sign in again.")
    return user


def _public_user(user: dict) -> dict:
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


@router.post("/register")
async def register(body: RegisterRequest) -> dict:
    try:
        user = db.create_user(body.email, body.name, _hash_password(body.password))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return {"token": _issue_token(user["id"]), "user": _public_user(user)}


@router.post("/login")
async def login(body: LoginRequest) -> dict:
    user = db.get_user_by_email(body.email)
    if user is None or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return {"token": _issue_token(user["id"]), "user": _public_user(user)}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict:
    return {"user": _public_user(user)}
