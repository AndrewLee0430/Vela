# api/services/lemonsqueezy_service.py

import os
import httpx

LEMON_API_KEY = os.getenv("LEMON_SQUEEZY_API_KEY", "")
LEMON_STORE_ID = os.getenv("LEMON_SQUEEZY_STORE_ID", "")
LEMON_BASE_URL = "https://api.lemonsqueezy.com/v1"

HEADERS = {
    "Authorization": f"Bearer {LEMON_API_KEY}",
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
}


async def create_checkout(variant_id: str, clerk_user_id: str, email: str = "") -> str:
    """
    建立 Lemon Squeezy Checkout Session
    回傳 checkout URL
    """
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "custom": {
                        "clerk_user_id": clerk_user_id
                    }
                },
                "checkout_options": {
                    "embed": False
                }
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": str(LEMON_STORE_ID)
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": str(variant_id)
                    }
                }
            }
        }
    }

    if email:
        payload["data"]["attributes"]["checkout_data"]["email"] = email

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LEMON_BASE_URL}/checkouts",
            json=payload,
            headers=HEADERS,
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["attributes"]["url"]


async def get_customer_portal_url(subscription_id: str) -> str:
    """
    取得 Customer Portal URL（讓用戶自行管理訂閱）
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{LEMON_BASE_URL}/subscriptions/{subscription_id}",
            headers=HEADERS,
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["attributes"]["urls"]["customer_portal"]
