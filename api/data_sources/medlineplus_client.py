"""
MedlinePlus Client — Consumer Health Information
Uses MedlinePlus Connect Web Service (no API key required)
https://connect.medlineplus.gov/service
"""

import httpx
import logging
import xml.etree.ElementTree as ET
from api.cache.simple_cache import SimpleCache

logger = logging.getLogger(__name__)

_cache = SimpleCache(default_ttl_seconds=24 * 3600)  # 24-hour TTL

MEDLINEPLUS_URL = "https://connect.medlineplus.gov/service"


class MedlinePlusClient:

    async def get_drug_info(self, drug_name: str) -> dict | None:
        """
        Get consumer-friendly drug information from MedlinePlus.
        Returns dict with title, url, summary or None.
        """
        return await self._fetch(f"drug: {drug_name}", drug_name)

    async def get_condition_info(self, condition: str) -> dict | None:
        """
        Get consumer-friendly condition/diagnosis information from MedlinePlus.
        Returns dict with title, url, summary or None.
        """
        return await self._fetch(condition, condition)

    async def _fetch(self, query: str, cache_suffix: str) -> dict | None:
        cache_key = f"medlineplus:{cache_suffix.lower().strip()}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached if cached != "__none__" else None

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(MEDLINEPLUS_URL, params={
                    "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.90",  # ICD-10
                    "mainSearchCriteria.v.dn": query,
                    "knowledgeResponseType": "application/json",
                    "informationRecipient": "PROV",
                })
                response.raise_for_status()
                data = response.json()

            # Parse Atom-style feed wrapped in JSON
            entries = data.get("feed", {}).get("entry", [])
            if not entries:
                _cache.set(cache_key, "__none__")
                return None

            entry = entries[0]
            result = {
                "title":   entry.get("title", {}).get("_value", query),
                "url":     entry.get("link", [{}])[0].get("href", ""),
                "summary": entry.get("summary", {}).get("_value", ""),
            }
            # Trim summary to avoid reproducing full article text (NLM compliance)
            if result["summary"]:
                result["summary"] = result["summary"][:400]

            _cache.set(cache_key, result)
            return result

        except Exception as e:
            logger.warning("MedlinePlus fetch failed (query len=%d): %s", len(query or ""), type(e).__name__)
            _cache.set(cache_key, "__none__")
            return None


medlineplus_client = MedlinePlusClient()