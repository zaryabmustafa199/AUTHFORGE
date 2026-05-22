from passlib.context import CryptContext
import secrets
import string

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def generate_otp() -> str:
    """Generates a 6-digit numeric OTP"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def generate_reset_token() -> str:
    """Generates a secure random string for password resets"""
    return secrets.token_urlsafe(32)
