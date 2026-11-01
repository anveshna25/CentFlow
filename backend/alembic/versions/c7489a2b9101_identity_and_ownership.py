"""identity_and_ownership

Revision ID: c7489a2b9101
Revises: b6601f2a7d57
Create Date: 2026-11-01 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7489a2b9101'
down_revision: Union[str, None] = 'b6601f2a7d57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_USER_ID = "legacy-dev-user-0000-000000000001"
LEGACY_EMAIL = "legacy-dev@centflow.local"


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('email_normalized', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_email_normalized'), 'users', ['email_normalized'], unique=True)

    # 2. Create user_identities table
    op.create_table(
        'user_identities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_subject', sa.String(length=255), nullable=False),
        sa.Column('provider_email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_subject', name='uq_identity_provider_subject'),
    )
    op.create_index(op.f('ix_user_identities_user_id'), 'user_identities', ['user_id'], unique=False)

    # 3. Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_sessions_token_hash'), 'user_sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_expires_at'), 'user_sessions', ['expires_at'], unique=False)
    op.create_index(op.f('ix_user_sessions_revoked_at'), 'user_sessions', ['revoked_at'], unique=False)

    # 4. Create email_tokens table
    op.create_table(
        'email_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('token_type', sa.String(length=30), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_tokens_token_hash'), 'email_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_email_tokens_user_id'), 'email_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_email_tokens_expires_at'), 'email_tokens', ['expires_at'], unique=False)

    # 5. Legacy data migration: Ensure legacy development data is attributed without data loss
    bind = op.get_bind()
    has_unowned_portfolios = bind.execute(
        sa.text("SELECT COUNT(1) FROM portfolios WHERE user_id IS NULL")
    ).scalar() or 0
    has_unowned_watchlists = bind.execute(
        sa.text("SELECT COUNT(1) FROM watchlists WHERE user_id IS NULL")
    ).scalar() or 0

    if has_unowned_portfolios > 0 or has_unowned_watchlists > 0:
        # Seed legacy user
        bind.execute(
            sa.text(
                "INSERT OR IGNORE INTO users (id, email, email_normalized, display_name, password_hash, email_verified_at, is_active) "
                "VALUES (:id, :email, :email_normalized, :display_name, NULL, CURRENT_TIMESTAMP, 1)"
            ),
            {
                "id": LEGACY_USER_ID,
                "email": LEGACY_EMAIL,
                "email_normalized": LEGACY_EMAIL,
                "display_name": "Legacy Development User",
            },
        )
        # Re-assign unowned portfolios and watchlists
        bind.execute(
            sa.text("UPDATE portfolios SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": LEGACY_USER_ID},
        )
        bind.execute(
            sa.text("UPDATE watchlists SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": LEGACY_USER_ID},
        )

    # 6. Apply non-nullable constraint and foreign key via batch_alter_table for SQLite compatibility
    with op.batch_alter_table('portfolios', schema=None) as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.String(length=36), nullable=False)
        batch_op.create_foreign_key('fk_portfolios_user_id', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('watchlists', schema=None) as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.String(length=36), nullable=False)
        batch_op.create_foreign_key('fk_watchlists_user_id', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    with op.batch_alter_table('watchlists', schema=None) as batch_op:
        batch_op.drop_constraint('fk_watchlists_user_id', type_='foreignkey')
        batch_op.alter_column('user_id', existing_type=sa.String(length=36), nullable=True)

    with op.batch_alter_table('portfolios', schema=None) as batch_op:
        batch_op.drop_constraint('fk_portfolios_user_id', type_='foreignkey')
        batch_op.alter_column('user_id', existing_type=sa.String(length=36), nullable=True)

    op.drop_index(op.f('ix_email_tokens_expires_at'), table_name='email_tokens')
    op.drop_index(op.f('ix_email_tokens_user_id'), table_name='email_tokens')
    op.drop_index(op.f('ix_email_tokens_token_hash'), table_name='email_tokens')
    op.drop_table('email_tokens')

    op.drop_index(op.f('ix_user_sessions_revoked_at'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_expires_at'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_token_hash'), table_name='user_sessions')
    op.drop_table('user_sessions')

    op.drop_index(op.f('ix_user_identities_user_id'), table_name='user_identities')
    op.drop_table('user_identities')

    op.drop_index(op.f('ix_users_email_normalized'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

