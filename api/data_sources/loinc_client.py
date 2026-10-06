"""
LOINC Client — Lab Test Terminology Lookups
Uses NLM Clinical Tables API (no API key required)
https://clinicaltables.nlm.nih.gov/api/loinc_items/v3/search
"""

import httpx
import logging
from api.cache.simple_cache import SimpleCache

logger = logging.getLogger(__name__)

_cache = SimpleCache(default_ttl_seconds=7 * 24 * 3600)  # 7-day TTL (LOINC codes are stable)

LOINC_API_URL = "https://clinicaltables.nlm.nih.gov/api/loinc_items/v3/search"


class LOINCClient:

    async def search(self, term: str) -> dict | None:
        """
        Search LOINC for a lab test name.
        Returns the best match as a dict with loinc_num, long_common_name, etc.
        """
        cache_key = f"loinc:{term.lower().strip()}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(LOINC_API_URL, params={
                    "terms": term,
                    "ef": "LOINC_NUM,LONG_COMMON_NAME,COMPONENT,SYSTEM,CLASS",
                    "maxList": 3,
                })
                response.raise_for_status()
                data = response.json()

            # Response format: [total, [codes], null, [extra_fields]]
            # extra_fields[i] = {"LOINC_NUM": ..., "LONG_COMMON_NAME": ...}
            if not data or not data[0]:
                _cache.set(cache_key, None)
                return None

            extra = data[3]
            if not extra:
                _cache.set(cache_key, None)
                return None

            # NLM API returns data[3] as dict of lists:
            # {"LOINC_NUM": ["12345-6", ...], "LONG_COMMON_NAME": ["GFR...", ...], ...}
            if isinstance(extra, dict):
                result = {
                    "loinc_num":        extra.get("LOINC_NUM", [""])[0] if extra.get("LOINC_NUM") else "",
                    "long_common_name": extra.get("LONG_COMMON_NAME", [term])[0] if extra.get("LONG_COMMON_NAME") else term,
                    "component":        extra.get("COMPONENT", [""])[0] if extra.get("COMPONENT") else "",
                    "system":           extra.get("SYSTEM", [""])[0] if extra.get("SYSTEM") else "",
                    "class":            extra.get("CLASS", [""])[0] if extra.get("CLASS") else "",
                }
            elif isinstance(extra, list) and extra:
                # Fallback: list of lists
                best = extra[0]
                if isinstance(best, list):
                    result = {
                        "loinc_num":        best[0] if len(best) > 0 else "",
                        "long_common_name": best[1] if len(best) > 1 else term,
                        "component":        best[2] if len(best) > 2 else "",
                        "system":           best[3] if len(best) > 3 else "",
                        "class":            best[4] if len(best) > 4 else "",
                    }
                else:
                    result = {
                        "loinc_num":        best.get("LOINC_NUM", ""),
                        "long_common_name": best.get("LONG_COMMON_NAME", term),
                        "component":        best.get("COMPONENT", ""),
                        "system":           best.get("SYSTEM", ""),
                        "class":            best.get("CLASS", ""),
                    }
            else:
                _cache.set(cache_key, None)
                return None
            _cache.set(cache_key, result)
            return result

        except Exception as e:
            logger.warning("LOINC search failed (term len=%d): %s", len(term or ""), type(e).__name__)
            return None


loinc_client = LOINCClient()