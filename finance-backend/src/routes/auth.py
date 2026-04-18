import random
import string
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from src.db.database import get_db
from src.middleware.auth import create_token
from src.utils.email import send_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── Schemas ────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

# ── Routes ─────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if len(body.name.strip()) < 2:
        raise HTTPException(400, "Name must be at least 2 characters")

    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (body.email.lower(),))
            if cur.fetchone():
                raise HTTPException(409, "An account with this email already exists")

            cur.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, name, email, currency, created_at
                """,
                (body.name.strip(), body.email.lower(), hashed)
            )
            user = dict(cur.fetchone())

    token = create_token(str(user["id"]), user["email"])
    return {
        "token": token,
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "currency": user["currency"]
        }
    }


@router.post("/login")
def login(body: LoginRequest):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, password_hash, currency FROM users WHERE email = %s",
                (body.email.lower(),)
            )
            user = cur.fetchone()

    if not user:
        raise HTTPException(401, "Invalid email or password")

    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Invalid email or password")

    token = create_token(str(user["id"]), user["email"])
    return {
        "token": token,
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "currency": user["currency"]
        }
    }


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    email = body.email.lower()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            if not user:
                # Don't reveal whether the email exists
                return {"message": "If that email exists, a reset code has been sent"}

            name = user["name"]
            code = ''.join(random.choices(string.digits, k=6))
            expires_at = datetime.utcnow() + timedelta(minutes=10)

            # Invalidate any existing unused codes for this email
            cur.execute(
                "UPDATE password_reset_tokens SET used = TRUE WHERE email = %s",
                (email,)
            )
            cur.execute(
                "INSERT INTO password_reset_tokens (email, code, expires_at) VALUES (%s, %s, %s)",
                (email, code, expires_at)
            )

    try:
        send_reset_email(email, code, name)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to send email. Check EMAIL_USER and EMAIL_PASSWORD in .env"
        )

    return {"message": "Reset code sent to your email"}


@router.post("/verify-reset-code")
def verify_reset_code(body: VerifyCodeRequest):
    email = body.email.lower()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM password_reset_tokens
                WHERE email = %s AND code = %s AND used = FALSE AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
                """,
                (email, body.code)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="Invalid or expired code")

    return {"message": "Code verified", "valid": True}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest):
    email = body.email.lower()

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM password_reset_tokens
                WHERE email = %s AND code = %s AND used = FALSE AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
                """,
                (email, body.code)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="Invalid or expired code")

            hashed = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()

            # Column is password_hash (matches schema.sql) — not password
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (hashed, email)
            )
            cur.execute(
                "UPDATE password_reset_tokens SET used = TRUE WHERE id = %s",
                (row["id"],)
            )

    return {"message": "Password updated successfully"}

