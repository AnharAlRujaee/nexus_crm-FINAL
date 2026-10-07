"""Login backend: verifies credentials against data/Users.xlsx using pandas.

Users.xlsx layout (sheet "Users"): Username | Password | Role   (Role = admin / user)
"""

import os
from dataclasses import dataclass

import pandas as pd

from data_service import data_file


def users_file_path() -> str:
    return data_file("Users.xlsx")


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


def username_exists(username: str, path: str | None = None) -> bool:
    df = load_users(path)
    return not df[df["username"].str.lower() == username.strip().lower()].empty


def register_user(username: str, password: str, role: str = "user", path: str | None = None) -> None:
    path = path or users_file_path()
    username, password = username.strip(), password.strip()
    if username_exists(username, path):
        raise AuthError(f"Username '{username}' is already taken.")
    df = load_users(path)
    new = pd.DataFrame([{"username": username, "password": password, "role": role.lower()}])
    out = pd.concat([df, new], ignore_index=True)
    out.columns = ["Username", "Password", "Role"]
    try:
        out.to_excel(path, sheet_name="Users", index=False)
    except PermissionError as exc:
        raise AuthError("Users.xlsx is open in another program. Close it and retry.") from exc
