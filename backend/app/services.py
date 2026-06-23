from typing import Optional, Dict

class PricingService:
    # In-memory storage acting as standard pricing rules database.
    # Future enhancement: Replace this with async queries to PostgreSQL, Redis, NetSuite, SAP, or AI engines.
    _PRICING_RULES: Dict[str, float] = {
        "75028": 1499.00,
        "10001": 1699.00,
        "90210": 1799.00
    }

    @classmethod
    async def get_price(cls, product_id: int, zip_code: str) -> Optional[float]:
        """
        Determines the custom price for a product based on the user's regional ZIP code.
        
        Args:
            product_id: The Shopify product ID (used for future granular item-level overrides).
            zip_code: The 5-digit zip code parameter.

        Returns:
            The custom float price if a rule exists, otherwise None.
        """
        # Rules logic is centralized here. product_id is accepted to enable
        # future product-specific matrix lookups or database mappings.
        return cls._PRICING_RULES.get(zip_code)

    @classmethod
    def format_currency(cls, amount: float) -> str:
        """
        Formats float numbers into standard USD currency layout.
        """
        return f"${amount:,.2f}"
