import stripe
import os

# Configure Stripe (User must set STRIPE_SECRET_KEY in Cloud Run Env Vars)
# Defaulting to a dummy placeholder to prevent crash on startup if missing
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder_key_must_be_set_in_env_vars")

def create_payment_link(case_id: str, amount: float, currency: str = "inr"):
    """
    Generates a Stripe Checkout Session URL for a specific debt case.
    """
    try:
        domain_url = os.getenv("DOMAIN_URL", "https://MK-PANKAJ.github.io/model") # Default to GitHub Pages

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': f'Debt Settlement - Case {case_id}',
                    },
                    'unit_amount': int(amount * 100), # Stripe expects cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{domain_url}/api/v1/payment/success?case_id={case_id}",
            cancel_url=domain_url + '?payment=cancelled',
        )
        return {"payment_url": session.url}
    except Exception as e:
        print(f"Stripe Error: {e}")
        return {"error": str(e)}
