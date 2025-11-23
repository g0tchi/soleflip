"""
Base classes and mixins for SQLAlchemy models
Provides common functionality for all domain models
"""

import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Load environment variables from .env file
load_dotenv()

# Create declarative base
Base = declarative_base()

# --- Encryption Setup ---
ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Fail loudly and clearly if the key is not set. Do not generate an ephemeral key.
    raise ValueError(
        "FATAL: The 'FIELD_ENCRYPTION_KEY' environment variable is not set or not passed to the container."
    )

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    raise ValueError(
        f"FATAL: Invalid FIELD_ENCRYPTION_KEY. The key must be a valid Fernet key. Error: {e}"
    )
# -------------------------


# --- Dialect-specific Type Compilation ---
@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(element, compiler, **kw):  # type: ignore[no-untyped-def]
    return compiler.visit_JSON(element, **kw)


# --- Mixins ---
class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EncryptedFieldMixin:
    """Mixin for models that need encrypted field support"""

    def get_encrypted_field(self, field_name: str) -> str:
        """Get decrypted field value"""
        encrypted_value = getattr(self, field_name, None)
        if not encrypted_value:
            return ""

        try:
            fernet = Fernet(ENCRYPTION_KEY.encode())
            return fernet.decrypt(encrypted_value.encode()).decode()
        except Exception:
            # Return empty string if decryption fails
            return ""

    def set_encrypted_field(self, field_name: str, value: str) -> None:
        """Set encrypted field value"""
        if not value:
            setattr(self, field_name, None)
            return

        try:
            fernet = Fernet(ENCRYPTION_KEY.encode())
            encrypted_value = fernet.encrypt(value.encode()).decode()
            setattr(self, field_name, encrypted_value)
        except Exception:
            # Set to None if encryption fails
            setattr(self, field_name, None)
