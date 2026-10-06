"""
FDA OpenFDA API Client
用於查詢藥品標籤、不良反應、召回等資訊

API 文件：https://open.fda.gov/apis/
"""

import os
import logging
import httpx
from typing import Optional
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class FDADrugLabel:
    """FDA 藥品標籤資料結構"""
    brand_name: str
    generic_name: str
    manufacturer: str
    indications: Optional[str] = None
    warnings: Optional[str] = None
    adverse_reactions: Optional[str] = None
    drug_interactions: Optional[str] = None
    dosage: Optional[str] = None
    contraindications: Optional[str] = None
    
    @property
    def url(self) -> str:
        return "https://labels.fda.gov/"
    
    @property
    def source_id(self) -> str:
        return f"FDA:{self.brand_name}"
    
    def to_text(self) -> str:
        """轉換為可用於 RAG 的文字格式"""
        sections = [f"# {self.brand_name} ({self.generic_name})"]
        sections.append(f"\n**Manufacturer:** {self.manufacturer}")
        sections.append(f"**Source:** FDA Official Drug Label")
        
        # Baton A parity with DailyMed option (b): openFDA sections are single prose blobs
        # (no separable table), so the interaction/contraindication DRUG ENUMERATIONS live
        # INLINE in these safety fields. To match "the enumeration always reaches the LLM",
        # the SAFETY/interaction-bearing sections (Drug Interactions, Warnings,
        # Contraindications) are passed FULL — never truncated. Non-grounding NARRATIVE
        # (Indications, Adverse Reactions, Dosage) stays bounded via _truncate.
        if self.indications:
            sections.append(f"\n## Indications and Usage\n{self._truncate(self.indications)}")

        if self.warnings:
            sections.append(f"\n## Warnings\n{self.warnings}")

        if self.adverse_reactions:
            sections.append(f"\n## Adverse Reactions\n{self._truncate(self.adverse_reactions)}")

        if self.drug_interactions:
            sections.append(f"\n## Drug Interactions\n{self.drug_interactions}")

        if self.dosage:
            sections.append(f"\n## Dosage and Administration\n{self._truncate(self.dosage)}")

        if self.contraindications:
            sections.append(f"\n## Contraindications\n{self.contraindications}")

        return "\n".join(sections)
    
    def _truncate(self, text: str, max_length: int = 2000) -> str:
        """截斷過長的文字"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    def to_dict(self) -> dict:
        """轉換為字典格式（用於 JSON 序列化）"""
        return {
            "brand_name": self.brand_name,
            "generic_name": self.generic_name,
            "manufacturer": self.manufacturer,
            "indications": self.indications,
            "warnings": self.warnings,
            "adverse_reactions": self.adverse_reactions,
            "drug_interactions": self.drug_interactions,
            "dosage": self.dosage,
            "contraindications": self.contraindications,
            "url": self.url,
            "source_id": self.source_id
        }


class FDAClient:
    """OpenFDA API 客戶端"""
    
    BASE_URL = "https://api.fda.gov/drug"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 FDA 客戶端
        
        Args:
            api_key: FDA API key（可選，有的話 rate limit 提升）
        """
        self.api_key = api_key or os.getenv("FDA_API_KEY")
        
        # Rate limit: 40/分鐘（無 API key）或 240/分鐘（有 API key）
        self.rate_limit_delay = 1.5 if not self.api_key else 0.25
    
    async def search_drug_labels(
        self,
        query: str,
        limit: int = 5
    ) -> list[FDADrugLabel]:
        """
        搜尋藥品標籤（異步）
        
        Args:
            query: 藥品名稱或關鍵字
            limit: 最多返回筆數
            
        Returns:
            FDADrugLabel 列表
        """
        # 建立搜尋查詢 - 同時搜尋 brand_name 和 generic_name
        search_query = f'openfda.brand_name:"{query}" OR openfda.generic_name:"{query}"'
        
        params = {
            "search": search_query,
            "limit": limit
        }
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/label.json",
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 404:
                    # 沒有找到結果
                    return []
                
                response.raise_for_status()
                data = response.json()
            
            await asyncio.sleep(self.rate_limit_delay)
            return self._parse_labels(data.get("results", []))
            
        except httpx.HTTPStatusError as e:
            logger.warning("FDA API HTTP error (query len=%d): %d", len(query), e.response.status_code)
            return []
        except Exception as e:
            logger.warning("FDA API error (query len=%d): %s", len(query), type(e).__name__)
            return []
    
    # ✅ 新增：同步版本的 get_drug_label
    def get_drug_label(self, drug_name: str) -> Optional[dict]:
        """
        獲取藥品標籤（同步版本）
        
        Args:
            drug_name: 藥品名稱
            
        Returns:
            藥品標籤字典，如果未找到則返回 None
        """
        try:
            # 使用同步的 search_drug_labels_sync
            labels = self.search_drug_labels_sync(drug_name, limit=1)
            
            if labels:
                # 返回字典格式
                return labels[0].to_dict()
            else:
                return None
                
        except Exception as e:
            logger.warning("Error in get_drug_label: %s", type(e).__name__)
            return None
    
    # ✅ 新增：同步包裝方法
    def search_drug_labels_sync(self, query: str, limit: int = 5) -> list[FDADrugLabel]:
        """
        搜尋藥品標籤（同步版本）
        
        Args:
            query: 藥品名稱或關鍵字
            limit: 最多返回筆數
            
        Returns:
            FDADrugLabel 列表
        """
        return asyncio.run(self.search_drug_labels(query, limit))
    
    async def search_by_interaction(
        self,
        drug_name: str,
        limit: int = 3
    ) -> list[FDADrugLabel]:
        """
        專門搜尋藥物交互作用相關資訊
        
        Args:
            drug_name: 藥品名稱
            limit: 最多返回筆數
            
        Returns:
            FDADrugLabel 列表（只包含有 drug_interactions 的）
        """
        labels = await self.search_drug_labels(drug_name, limit=limit * 2)
        
        # 過濾出有藥物交互作用資訊的
        return [
            label for label in labels
            if label.drug_interactions
        ][:limit]
    
    async def search_adverse_events(
        self,
        drug_name: str,
        limit: int = 10
    ) -> list[dict]:
        """
        搜尋藥品不良反應通報（FAERS）
        
        Args:
            drug_name: 藥品名稱
            limit: 最多返回筆數
            
        Returns:
            不良反應報告列表
        """
        params = {
            "search": f'patient.drug.medicinalproduct:"{drug_name}"',
            "limit": limit
        }
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/event.json",
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 404:
                    return []
                
                response.raise_for_status()
                data = response.json()
            
            await asyncio.sleep(self.rate_limit_delay)
            return data.get("results", [])
            
        except Exception as e:
            logger.error("[FDA] API error for search_drug_labels: %s", type(e).__name__)
            return []

    def _parse_labels(self, results: list[dict]) -> list[FDADrugLabel]:
        """解析 FDA Label API 回應"""
        labels = []
        
        for result in results:
            try:
                openfda = result.get("openfda", {})
                
                # 品牌名和通用名
                brand_name = self._get_first(openfda.get("brand_name", []))
                generic_name = self._get_first(openfda.get("generic_name", []))
                
                if not brand_name and not generic_name:
                    continue
                
                # 製造商
                manufacturer = self._get_first(openfda.get("manufacturer_name", ["Unknown"]))
                
                # 各個區塊
                indications = self._get_first(result.get("indications_and_usage", []))
                warnings = self._get_first(result.get("warnings", []))
                adverse_reactions = self._get_first(result.get("adverse_reactions", []))
                drug_interactions = self._get_first(result.get("drug_interactions", []))
                dosage = self._get_first(result.get("dosage_and_administration", []))
                contraindications = self._get_first(result.get("contraindications", []))
                
                labels.append(FDADrugLabel(
                    brand_name=brand_name or generic_name,
                    generic_name=generic_name or brand_name,
                    manufacturer=manufacturer,
                    indications=indications,
                    warnings=warnings,
                    adverse_reactions=adverse_reactions,
                    drug_interactions=drug_interactions,
                    dosage=dosage,
                    contraindications=contraindications
                ))
                
            except Exception:
                continue
        
        return labels
    
    def _get_first(self, lst: list) -> Optional[str]:
        """取得列表的第一個元素，如果是列表的話"""
        if not lst:
            return None
        item = lst[0] if isinstance(lst, list) else lst
        return str(item) if item else None


# 同步版本的包裝函數（方便測試）
def search_fda_sync(query: str, limit: int = 5) -> list[FDADrugLabel]:
    """同步版本的 FDA 搜尋"""
    client = FDAClient()
    return client.search_drug_labels_sync(query, limit)


# 測試用
if __name__ == "__main__":
    # 測試同步方法
    print("=== Testing Synchronous Methods ===")
    client = FDAClient()
    
    print("\n1. Testing get_drug_label (sync)...")
    label = client.get_drug_label("Metformin")
    if label:
        print(f"✅ Found: {label['brand_name']}")
    else:
        print("❌ Not found")
    
    print("\n2. Testing search_drug_labels_sync...")
    labels = client.search_drug_labels_sync("Aspirin", limit=2)
    print(f"✅ Found {len(labels)} labels")
    
    # 測試異步方法
    async def test_async():
        client = FDAClient()
        
        print("\n=== Testing Async Methods ===")
        print("\n=== 搜尋 Metformin ===")
        labels = await client.search_drug_labels("metformin", limit=2)
        for label in labels:
            print(f"Brand: {label.brand_name}")
            print(f"Generic: {label.generic_name}")
            print(f"Has interactions: {bool(label.drug_interactions)}")
            print("-" * 50)
        
        print("\n=== 搜尋 Warfarin 交互作用 ===")
        labels = await client.search_by_interaction("warfarin", limit=1)
        for label in labels:
            print(f"Drug: {label.brand_name}")
            if label.drug_interactions:
                print(f"Interactions (first 500 chars): {label.drug_interactions[:500]}...")
    
    print("\n=== Running async tests ===")
    asyncio.run(test_async())