"""Beta monetization boundary.

Payments, Premium and advertising are intentionally disabled for the closed
consumer beta.  Keeping this explicit prevents old payment code from looking
like a supported production feature.
"""


class PaymentService:
    async def create_payment(self, *args, **kwargs):
        return {"ok": False, "error": "payments_disabled_in_beta"}


class PremiumManager:
    async def is_premium(self, user_id: int) -> bool:
        return False


payment_service = PaymentService()
premium_manager = PremiumManager()
