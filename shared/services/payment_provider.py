"""
PCI-Compliant Payment Provider Integration
Handles secure payment method tokenization and processing
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class PaymentProvider(Enum):
    """Supported payment providers"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    SQUARE = "square"
    MANUAL_IMPORT = "manual_import"  # For legacy data migration


class PaymentProviderError(Exception):
    """Base exception for payment provider errors"""
    pass


class PaymentMethodTokenizer(ABC):
    """Abstract base class for payment method tokenization"""

    @abstractmethod
    async def create_payment_method(self, card_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Create a tokenized payment method from card data

        Args:
            card_data: Dict containing card information (number, exp_month, exp_year, cvc)

        Returns:
            Dict with keys: token, last4, brand, fingerprint

        Note: This method should NEVER store raw card data
        """
        pass

    @abstractmethod
    async def get_payment_method(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve payment method details by token

        Args:
            token: Payment method token

        Returns:
            Dict with payment method details (no sensitive data)
        """
        pass

    @abstractmethod
    async def delete_payment_method(self, token: str) -> bool:
        """
        Delete a payment method

        Args:
            token: Payment method token

        Returns:
            True if successful
        """
        pass


class StripePaymentTokenizer(PaymentMethodTokenizer):
    """Stripe payment method tokenizer"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Import stripe only when needed to avoid dependency issues
        try:
            import stripe
            self.stripe = stripe
            stripe.api_key = api_key
        except ImportError:
            raise PaymentProviderError("Stripe library not installed. Run: pip install stripe")

    async def create_payment_method(self, card_data: Dict[str, Any]) -> Dict[str, str]:
        """Create Stripe payment method token"""
        try:
            payment_method = self.stripe.PaymentMethod.create(
                type="card",
                card={
                    "number": card_data["number"],
                    "exp_month": card_data["exp_month"],
                    "exp_year": card_data["exp_year"],
                    "cvc": card_data["cvc"],
                }
            )

            return {
                "token": payment_method.id,
                "last4": payment_method.card.last4,
                "brand": payment_method.card.brand,
                "fingerprint": payment_method.card.fingerprint,
                "exp_month": payment_method.card.exp_month,
                "exp_year": payment_method.card.exp_year,
            }

        except Exception as e:
            logger.error(f"Failed to create Stripe payment method: {e}")
            raise PaymentProviderError(f"Stripe tokenization failed: {e}")

    async def get_payment_method(self, token: str) -> Optional[Dict[str, Any]]:
        """Get Stripe payment method details"""
        try:
            payment_method = self.stripe.PaymentMethod.retrieve(token)
            return {
                "id": payment_method.id,
                "last4": payment_method.card.last4,
                "brand": payment_method.card.brand,
                "exp_month": payment_method.card.exp_month,
                "exp_year": payment_method.card.exp_year,
            }
        except Exception as e:
            logger.error(f"Failed to retrieve Stripe payment method: {e}")
            return None

    async def delete_payment_method(self, token: str) -> bool:
        """Delete Stripe payment method"""
        try:
            self.stripe.PaymentMethod.detach(token)
            return True
        except Exception as e:
            logger.error(f"Failed to delete Stripe payment method: {e}")
            return False


class PaymentProviderFactory:
    """Factory for creating payment provider instances"""

    _providers = {
        PaymentProvider.STRIPE: StripePaymentTokenizer,
        # PaymentProvider.PAYPAL: PayPalPaymentTokenizer,  # TODO: Implement
        # PaymentProvider.SQUARE: SquarePaymentTokenizer,  # TODO: Implement
    }

    @classmethod
    def create_tokenizer(self, provider: PaymentProvider, **kwargs) -> PaymentMethodTokenizer:
        """
        Create a payment method tokenizer for the specified provider

        Args:
            provider: Payment provider enum
            **kwargs: Provider-specific configuration (e.g., api_key)

        Returns:
            PaymentMethodTokenizer instance
        """
        if provider not in self._providers:
            raise PaymentProviderError(f"Unsupported payment provider: {provider}")

        tokenizer_class = self._providers[provider]
        return tokenizer_class(**kwargs)


class SecurePaymentService:
    """
    Service for managing PCI-compliant payment methods
    Replaces direct credit card storage
    """

    def __init__(self, tokenizer: PaymentMethodTokenizer):
        self.tokenizer = tokenizer

    async def tokenize_payment_method(self, card_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Securely tokenize payment method data

        IMPORTANT: This method should be called from a PCI-compliant environment only
        Card data should never be stored in your application

        Args:
            card_data: Card information dict

        Returns:
            Tokenized payment method data safe for storage
        """
        if not self._validate_card_data(card_data):
            raise PaymentProviderError("Invalid card data provided")

        # Tokenize with payment provider
        token_data = await self.tokenizer.create_payment_method(card_data)

        # Return only safe data for storage
        return {
            "provider": self.tokenizer.__class__.__name__.lower().replace("paymenttokenizer", ""),
            "token": token_data["token"],
            "last4": token_data["last4"],
            "brand": token_data["brand"],
            "exp_month": token_data.get("exp_month"),
            "exp_year": token_data.get("exp_year"),
        }

    def _validate_card_data(self, card_data: Dict[str, Any]) -> bool:
        """Validate card data structure"""
        required_fields = ["number", "exp_month", "exp_year", "cvc"]
        return all(field in card_data for field in required_fields)

    async def get_payment_method_details(self, token: str) -> Optional[Dict[str, Any]]:
        """Get safe payment method details for display"""
        return await self.tokenizer.get_payment_method(token)

    async def delete_payment_method(self, token: str) -> bool:
        """Securely delete payment method"""
        return await self.tokenizer.delete_payment_method(token)


# Example usage and migration helper
class LegacyDataMigrator:
    """
    Helper for migrating existing encrypted credit card data to tokenized format

    WARNING: This should only be run in a secure, PCI-compliant environment
    with proper access controls and audit logging
    """

    def __init__(self, payment_service: SecurePaymentService):
        self.payment_service = payment_service

    async def migrate_legacy_account(self, encrypted_cc: str, encrypted_cvv: str,
                                   exp_month: int, exp_year: int) -> Optional[Dict[str, str]]:
        """
        Migrate legacy encrypted credit card data to tokenized format

        This is a one-time migration that should be run during the PCI compliance update
        """
        try:
            # Decrypt legacy data (implementation depends on existing encryption)
            # NOTE: This step requires the existing encryption key
            decrypted_card_data = self._decrypt_legacy_data(encrypted_cc, encrypted_cvv)

            # Add expiry information
            card_data = {
                **decrypted_card_data,
                "exp_month": exp_month,
                "exp_year": exp_year,
            }

            # Tokenize with payment provider
            token_data = await self.payment_service.tokenize_payment_method(card_data)

            # CRITICAL: Immediately clear decrypted data from memory
            del card_data
            del decrypted_card_data

            return token_data

        except Exception as e:
            logger.error(f"Failed to migrate legacy payment data: {e}")
            return None

    def _decrypt_legacy_data(self, encrypted_cc: str, encrypted_cvv: str) -> Dict[str, str]:
        """
        Decrypt legacy encrypted credit card data

        WARNING: This method should only be implemented during migration
        and removed immediately after migration is complete
        """
        # TODO: Implement using existing encryption key
        # This is intentionally not implemented to prevent accidental exposure
        raise NotImplementedError("Legacy decryption must be implemented securely during migration")


# Environment configuration
def get_payment_service(provider_name: str = "stripe") -> SecurePaymentService:
    """
    Get configured payment service instance

    Args:
        provider_name: Name of payment provider

    Returns:
        Configured SecurePaymentService instance
    """
    import os

    provider = PaymentProvider(provider_name.lower())

    if provider == PaymentProvider.STRIPE:
        api_key = os.getenv("STRIPE_SECRET_KEY")
        if not api_key:
            raise PaymentProviderError("STRIPE_SECRET_KEY environment variable not set")
        tokenizer = PaymentProviderFactory.create_tokenizer(provider, api_key=api_key)
    else:
        raise PaymentProviderError(f"Payment provider {provider_name} not configured")

    return SecurePaymentService(tokenizer)