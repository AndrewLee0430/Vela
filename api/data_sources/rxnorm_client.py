"""
RxNorm Client — Drug Name Standardization
Uses NLM RxNav REST API (no API key required)
https://rxnav.nlm.nih.gov/REST/
"""

import httpx
import logging
from api.cache.simple_cache import SimpleCache

logger = logging.getLogger(__name__)

_cache = SimpleCache(default_ttl_seconds=7 * 24 * 3600)  # 7-day TTL

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"


class RxNormClient:

    async def get_rxcui(self, drug_name: str) -> str | None:
        """
        Find the RXCUI (standard drug ID) for a drug name.
        Tries exact match first, then approximate match.
        Returns RXCUI string or None.
        """
        cache_key = f"rxcui:{drug_name.lower().strip()}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached if cached != "__none__" else None

        rxcui = await self._exact_match(drug_name) or await self._approx_match(drug_name)
        _cache.set(cache_key, rxcui if rxcui else "__none__")
        return rxcui

    async def _exact_match(self, drug_name: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{RXNAV_BASE}/rxcui.json",
                    params={"name": drug_name, "search": 1}
                )
                response.raise_for_status()
                data = response.json()
            rxcui = data.get("idGroup", {}).get("rxnormId", [None])[0]
            return rxcui
        except Exception as e:
            logger.warning("RxNorm exact match failed (term len=%d): %s", len(drug_name or ""), type(e).__name__)
            return None

    async def _approx_match(self, drug_name: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{RXNAV_BASE}/approximateTerm.json",
                    params={"term": drug_name, "maxEntries": 1}
                )
                response.raise_for_status()
                data = response.json()
            candidates = data.get("approximateGroup", {}).get("candidate", [])
            if candidates:
                return candidates[0].get("rxcui")
            return None
        except Exception as e:
            logger.warning("RxNorm approx match failed (term len=%d): %s", len(drug_name or ""), type(e).__name__)
            return None


rxnorm_client = RxNormClient()