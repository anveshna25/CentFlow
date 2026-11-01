from datetime import datetime, timedelta, timezone
import unittest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import (
    Base,
    EmailTokenModel,
    PortfolioModel,
    UserIdentityModel,
    UserModel,
    UserSessionModel,
    WatchlistModel,
)


class TestIdentityDatabaseModels(unittest.TestCase):
    """Test suite validating UserModel, UserIdentityModel, UserSessionModel, and EmailTokenModel."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def test_create_user_with_identities_and_sessions(self):
        """Test creating a user with linked identity and active session."""
        user = UserModel(
            email="trader@centflow.com",
            email_normalized="trader@centflow.com",
            display_name="Quantitative Trader",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummyhash",
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()

        # Link local identity
        identity = UserIdentityModel(
            user_id=user.id,
            provider="local",
            provider_subject=user.id,
            provider_email=user.email,
        )
        # Create session
        now = datetime.now(timezone.utc)
        session = UserSessionModel(
            user_id=user.id,
            token_hash="a"*64,
            expires_at=now + timedelta(days=7),
            ip_address="127.0.0.1",
        )
        # Create email token
        email_token = EmailTokenModel(
            user_id=user.id,
            token_hash="b"*64,
            token_type="VERIFY_EMAIL",
            expires_at=now + timedelta(hours=1),
        )
        self.db.add_all([identity, session, email_token])
        self.db.commit()

        # Query back and verify relationships
        queried_user = self.db.query(UserModel).filter_by(id=user.id).first()
        self.assertIsNotNone(queried_user)
        self.assertEqual(len(queried_user.identities), 1)
        self.assertEqual(queried_user.identities[0].provider, "local")
        self.assertEqual(len(queried_user.sessions), 1)
        self.assertEqual(queried_user.sessions[0].token_hash, "a"*64)
        self.assertEqual(len(queried_user.email_tokens), 1)

    def test_user_email_uniqueness(self):
        """Ensure duplicate normalized emails are rejected by unique constraints."""
        user1 = UserModel(
            email="investor@centflow.com",
            email_normalized="investor@centflow.com",
            display_name="Investor 1",
        )
        self.db.add(user1)
        self.db.commit()

        user2 = UserModel(
            email="Investor@Centflow.com",
            email_normalized="investor@centflow.com",
            display_name="Investor 2",
        )
        self.db.add(user2)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_cascade_delete_user_cleans_sessions_and_portfolios(self):
        """Ensure deleting a user cascades to identities, sessions, portfolios, and watchlists."""
        user = UserModel(
            email="owner@centflow.com",
            email_normalized="owner@centflow.com",
            display_name="Portfolio Owner",
        )
        self.db.add(user)
        self.db.commit()

        now = datetime.now(timezone.utc)
        session = UserSessionModel(
            user_id=user.id,
            token_hash="c"*64,
            expires_at=now + timedelta(days=1),
        )
        portfolio = PortfolioModel(
            name="Alpha Fund",
            user_id=user.id,
        )
        watchlist = WatchlistModel(
            name="Tech Radar",
            user_id=user.id,
        )
        self.db.add_all([session, portfolio, watchlist])
        self.db.commit()

        # Delete user
        self.db.delete(user)
        self.db.commit()

        # Assert cascaded deletion
        self.assertEqual(self.db.query(UserSessionModel).filter_by(user_id=user.id).count(), 0)
        self.assertEqual(self.db.query(PortfolioModel).filter_by(user_id=user.id).count(), 0)
        self.assertEqual(self.db.query(WatchlistModel).filter_by(user_id=user.id).count(), 0)


if __name__ == "__main__":
    unittest.main()

