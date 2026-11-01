import hashlib
import hmac
import secrets
from typing import Optional
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from email_validator import EmailNotValidError, validate_email

# Initialize Argon2id password hasher according to current OWASP guidance
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash in constant time."""
    if not plain_password or not hashed_password:
        return False
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Determine if a stored password hash requires parameter upgrading."""
    try:
        return _hasher.check_needs_rehash(hashed_password)
    except (InvalidHashError, VerificationError):
        return True


def generate_opaque_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random opaque token (e.g. for sessions)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    """Compute the SHA-256 hexadecimal digest of an opaque token for secure database lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generate a cryptographically secure random token for CSRF protection."""
    return secrets.token_hex(32)


def validate_csrf_token(cookie_csrf: Optional[str], header_csrf: Optional[str]) -> bool:
    """Validate double-submit CSRF tokens using constant-time string comparison."""
    if not cookie_csrf or not header_csrf:
        return False
    return hmac.compare_digest(cookie_csrf.strip(), header_csrf.strip())


def normalize_email(email: str) -> str:
    """Validate and normalize an email address to a consistent lowercase representation."""
    if not email:
        raise ValueError("Email address cannot be empty.")
    try:
        validated = validate_email(email.strip(), check_deliverability=False)
        return validated.normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError(f"Invalid email address: {exc}") from exc

