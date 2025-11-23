"""
Password hashing utilities using bcrypt.
"""

from typing import cast

import bcrypt

# from typing import str as StrType


class PasswordHasher:
    """Secure password hashing using bcrypt"""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return cast(str, hashed.decode("utf-8"))

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password is correct, False otherwise
        """
        try:
            return cast(bool, bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8")))
        except (ValueError, TypeError):
            return False
