import unittest
from app.core.security import (
    generate_csrf_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    needs_rehash,
    normalize_email,
    validate_csrf_token,
    verify_password,
)


class TestSecurityPrimitives(unittest.TestCase):
    """Test suite covering Argon2id password hashing, session tokens, and CSRF validation."""

    def test_argon2id_password_hashing_and_verification(self):
        """Verify that password hashes verify correctly and reject invalid credentials."""
        password = "SecureTradingPassword!2026"
        hashed = hash_password(password)

        self.assertTrue(hashed.startswith("$argon2id$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword123", hashed))
        self.assertFalse(verify_password("", hashed))
        self.assertFalse(verify_password(password, ""))
        self.assertFalse(verify_password(password, "invalid_hash_string"))
        self.assertFalse(needs_rehash(hashed))

    def test_opaque_token_generation_and_hashing(self):
        """Verify generation of high-entropy opaque tokens and SHA-256 digests."""
        token1 = generate_opaque_token(32)
        token2 = generate_opaque_token(32)

        self.assertNotEqual(token1, token2)
        self.assertTrue(len(token1) >= 40)

        digest1 = hash_token(token1)
        digest2 = hash_token(token1)
        self.assertEqual(len(digest1), 64)
        self.assertEqual(digest1, digest2)
        self.assertNotEqual(digest1, hash_token(token2))

    def test_csrf_token_validation(self):
        """Verify double-submit CSRF token validation with constant-time equality."""
        csrf_token = generate_csrf_token()
        self.assertEqual(len(csrf_token), 64)

        self.assertTrue(validate_csrf_token(csrf_token, csrf_token))
        self.assertFalse(validate_csrf_token(csrf_token, generate_csrf_token()))
        self.assertFalse(validate_csrf_token(csrf_token, None))
        self.assertFalse(validate_csrf_token(None, csrf_token))
        self.assertFalse(validate_csrf_token("", ""))

    def test_normalize_email(self):
        """Verify email validation and normalization."""
        self.assertEqual(
            normalize_email("  Investor.Alpha@Example.COM  "),
            "investor.alpha@example.com",
        )
        with self.assertRaises(ValueError):
            normalize_email("not-an-email")
        with self.assertRaises(ValueError):
            normalize_email("")


if __name__ == "__main__":
    unittest.main()

