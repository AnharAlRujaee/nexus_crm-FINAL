"""Login backend: verifies credentials against Users.xlsx using pandas.

Users.xlsx layout (sheet "Users"): Username | Password | Role   (Role = admin / user)
Put this file next to main.py (or inside crm/) and import it from the login window.
"""

import os
import sys
from dataclasses import dataclass

import pandas as pd


def users_file_path() -> str:
    """Users.xlsx next to main.py in dev, next to the .exe when frozen by PyInstaller."""
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
        else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "Users.xlsx")


class AuthError(Exception):
    """Users.xlsx missing, locked/open in Excel, or has the wrong columns."""


@dataclass(frozen=True)
class AuthResult:
    username: str
    role: str                      # "admin" or "user"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def load_users(path: str | None = None) -> pd.DataFrame:
    path = path or users_file_path()
    if not os.path.exists(path):
        raise AuthError(f"Users.xlsx not found at: {path}")
    try:
        df = pd.read_excel(path, sheet_name=0, dtype=str)   # dtype=str keeps "0123" intact
    except PermissionError as exc:
        raise AuthError("Users.xlsx is open in another program. Close it and retry.") from exc
    except Exception as exc:
        raise AuthError(f"Could not read Users.xlsx: {exc}") from exc

    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = {"username", "password", "role"} - set(df.columns)
    if missing:
        raise AuthError("Users.xlsx is missing column(s): " + ", ".join(sorted(missing)))

    df = df[["username", "password", "role"]].dropna()
    for col in df.columns:
        df[col] = df[col].str.strip()
    df["role"] = df["role"].str.lower()
    return df


def authenticate(username: str, password: str, path: str | None = None) -> AuthResult | None:
    """Return AuthResult on success, None on wrong credentials. Raises AuthError on file problems.

    Username is case-insensitive; password is exact.
    """
    username, password = username.strip(), password.strip()
    if not username or not password:
        return None
    df = load_users(path)
    hit = df[(df["username"].str.lower() == username.lower()) & (df["password"] == password)]
    if hit.empty:
        return None
    row = hit.iloc[0]
    return AuthResult(username=row["username"], role=row["role"])
