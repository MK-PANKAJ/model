try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    print("Warning: Stripe SDK not found. Payment features will be disabled.")
import os

# Configure Stripe
if STRIPE_AVAILABLE:
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_payment_link(case_id: str, amount: float, partial_amount: float = None, currency: str = "inr"):
    """
    Generates a Stripe Checkout Session URL for a specific debt case.
    """
    try:
        if not STRIPE_AVAILABLE:
            return {"error": "Stripe SDK not found. Install it to enable payments."}
            
        if not stripe.api_key:
            return {"error": "Stripe API Key is missing. Set STRIPE_SECRET_KEY in Cloud Run environment variables."}

        domain_url = os.getenv("DOMAIN_URL", "https://MK-PANKAJ.github.io/model")
        
        # Determine the amount to charge
        charge_amount = partial_amount if partial_amount is not None else amount

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': f'Debt Settlement - Case {case_id}',
                    },
                    'unit_amount': int(charge_amount * 100), # Stripe expects cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{domain_url}/api/v1/payment/success?case_id={case_id}&amount_paid={charge_amount}",
            cancel_url=domain_url + '?payment=cancelled',
            metadata={
                "case_id": case_id,
                "amount_paid": str(charge_amount)
            }
        )
        return {"payment_url": session.url}
    except Exception as e:
        print(f"Stripe Error: {e}")
        return {"error": str(e)}
