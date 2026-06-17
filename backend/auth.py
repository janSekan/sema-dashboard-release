import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from dotenv import load_dotenv
from db import get_account
from core.proxy_auth import get_proxy_user

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/device-api/login")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str


class User(BaseModel):
    username: str
    role: str
    disabled: bool = False


class LoginRequest(BaseModel):
    username: str
    password: str


VALID_ROLES = ["user", "admin", "superadmin"]


def get_user_by_username(username: str):
    for role in VALID_ROLES:
        account = get_account(role)

        if account and account["username"] == username:
            return {
                "username": account["username"],
                "password_hash": account["password_hash"],
                "role": account["role"],
                "disabled": False,
            }

    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str) -> Optional[User]:
    db_user = get_user_by_username(username)
    if not db_user:
        return None

    if not verify_password(password, db_user["password_hash"]):
        return None

    return User(
        username=db_user["username"],
        role=db_user["role"],
        disabled=db_user["disabled"],
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> User:
    proxy_user = get_proxy_user(request)

    if proxy_user:
        return User(
            username=proxy_user["username"],
            role=proxy_user["role"],
            disabled=False,
        )

    payload = decode_token(token)

    username = payload.get("sub")
    role = payload.get("role")

    if not username or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db_user = get_user_by_username(username)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return User(
        username=db_user["username"],
        role=db_user["role"],
        disabled=db_user["disabled"],
    )

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user

def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return current_user

def get_account_by_role(role: str):
    account = get_account(role)

    if not account:
        return None

    return {
        "username": account["username"],
        "role": account["role"],
    }