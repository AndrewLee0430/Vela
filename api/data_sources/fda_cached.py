"""
FDA Client with Caching
带缓存的 FDA API 客户端

使用方法:
    from api.data_sources.fda_cached import fda_client_cached
    
    # 获取单个药物标签
    label = fda_client_cached.get_drug_label("Metformin")
    
    # 搜索药物（返回 FDADrugLabel 对象列表）
    labels = fda_client_cached.search_drug_labels_sync("Aspirin", limit=5)
"""

import json
import logging
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from api.cache.simple_cache import fda_cache

logger = logging.getLogger(__name__)


@dataclass
class FDADrugLabel:
    """FDA 药物标签数据类"""
    drug_name: str
    active_ingredient: Optional[str] = None
    indications: Optional[str] = None
    dosage: Optional[str] = None
    warnings: Optional[str] = None
    adverse_reactions: Optional[str] = None
    drug_interactions: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    def to_text(self) -> str:
        """转换为文本格式（用于 RAG）"""
        parts = [f"Drug: {self.drug_name}\n"]
        
        if self.active_ingredient:
            parts.append(f"Active Ingredient:\n{self.active_ingredient}\n")
        
        if self.indications:
            parts.append(f"Indications:\n{self.indications}\n")
        
        if self.dosage:
            parts.append(f"Dosage:\n{self.dosage}\n")
        
        if self.warnings:
            parts.append(f"Warnings:\n{self.warnings}\n")
        
        if self.adverse_reactions:
            parts.append(f"Adverse Reactions:\n{self.adverse_reactions}\n")
        
        if self.drug_interactions:
            parts.append(f"Drug Interactions:\n{self.drug_interactions}\n")
        
        return "\n".join(parts)


class FDAClientCached:
    """带缓存的 FDA API 客户端"""
    
    def __init__(self, base_url: str = "https://api.fda.gov/drug/label.json"):
        self.base_url = base_url
        self.cache = fda_cache
    
    def _get_first(self, data: dict, key: str) -> Optional[str]:
        """
        从 FDA API 结果中获取字段的第一个值
        FDA API 的字段都是数组格式
        
        Args:
            data: FDA API 返回的数据
            key: 字段名
            
        Returns:
            字段的第一个值，如果不存在则返回 None
        """
        value = data.get(key, [])
        if isinstance(value, list) and len(value) > 0:
            return value[0]
        return None
    
    def _parse_fda_result(self, result: dict, drug_name: str) -> FDADrugLabel:
        """
        解析 FDA API 返回结果为 FDADrugLabel 对象
        
        Args:
            result: FDA API 返回的单个结果
            drug_name: 药物名称
            
        Returns:
            FDADrugLabel 对象
        """
        return FDADrugLabel(
            drug_name=drug_name,
            active_ingredient=self._get_first(result, "active_ingredient"),
            indications=self._get_first(result, "indications_and_usage"),
            dosage=self._get_first(result, "dosage_and_administration"),
            warnings=self._get_first(result, "warnings"),
            adverse_reactions=self._get_first(result, "adverse_reactions"),
            drug_interactions=self._get_first(result, "drug_interactions")
        )
    
    def get_drug_label(self, drug_name: str) -> Optional[Dict[str, Any]]:
        """
        获取药品标签原始数据（带缓存）
        
        Args:
            drug_name: 药物名称
            
        Returns:
            药品标签数据字典，如果未找到则返回 None
        """
        # 生成缓存键
        cache_key = f"fda_label:{drug_name.lower()}"
        
        # 1. 尝试从缓存获取
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            logger.debug("Cache hit for FDA label: %s", drug_name)
            try:
                # 尝试解析 JSON（如果是字符串）
                if isinstance(cached_data, str):
                    return json.loads(cached_data)
                return cached_data
            except json.JSONDecodeError:
                logger.warning("Cache data corrupted for %s, fetching fresh", drug_name)
        
        # 2. 缓存未命中，调用 API
        logger.debug("Cache miss for FDA label: %s, calling FDA API", drug_name)
        
        try:
            # 构建搜索查询（尝试多种搜索方式）
            search_terms = [
                f'openfda.brand_name:"{drug_name}"',
                f'openfda.generic_name:"{drug_name}"',
                f'openfda.substance_name:"{drug_name}"'
            ]
            
            for search_term in search_terms:
                params = {
                    "search": search_term,
                    "limit": 1
                }
                
                response = requests.get(self.base_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("results"):
                        result = data["results"][0]
                        
                        # 3. 存入缓存（24 小时）
                        self.cache.set(cache_key, json.dumps(result), ttl=86400)
                        logger.debug("Cached FDA label for %s", drug_name)
                        
                        return result
                
                elif response.status_code == 404:
                    # 404 表示未找到，尝试下一个搜索词
                    continue
                
                else:
                    logger.warning("FDA API returned status %d", response.status_code)
                    break

            # 所有搜索词都未找到
            logger.warning("No FDA label found for %s", drug_name)
            return None
            
        except requests.exceptions.Timeout:
            logger.warning("FDA API timeout for %s", drug_name)
            return None

        except requests.exceptions.RequestException as e:
            logger.warning("FDA API request error for %s: %s", drug_name, e)
            return None

        except Exception as e:
            logger.error("Unexpected error fetching FDA label for %s: %s", drug_name, e)
            return None
    
    def search_drug_labels_sync(self, query: str, limit: int = 5) -> List[FDADrugLabel]:
        """
        搜索药物标签（同步方法，带缓存）
        返回 FDADrugLabel 对象列表
        
        Args:
            query: 搜索查询（药物名称）
            limit: 返回结果数量
            
        Returns:
            FDADrugLabel 对象列表
        """
        cache_key = f"fda_search:{query.lower()}:{limit}"
        
        # 1. 尝试从缓存获取
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            logger.debug("Cache hit for FDA search: %s", query)
            try:
                # 从缓存恢复 FDADrugLabel 对象
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                return [FDADrugLabel(**item) for item in data]
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning("Cache data error for %s: %s, fetching fresh data", query, e)
                # 缓存数据损坏，继续调用 API
        
        # 2. 缓存未命中，调用 API
        logger.debug("Cache miss for FDA search: %s, calling FDA API", query)
        
        try:
            # 构建搜索查询
            search_terms = [
                f'openfda.brand_name:"{query}"',
                f'openfda.generic_name:"{query}"',
                f'openfda.substance_name:"{query}"'
            ]
            
            all_results = []
            
            for search_term in search_terms:
                params = {
                    "search": search_term,
                    "limit": limit
                }
                
                response = requests.get(self.base_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    # 解析为 FDADrugLabel 对象
                    for result in results:
                        label = self._parse_fda_result(result, query)
                        all_results.append(label)
                    
                    if all_results:
                        break  # 找到结果就停止
                
                elif response.status_code == 404:
                    continue  # 尝试下一个搜索词
                
                else:
                    logger.warning("FDA API returned status %d", response.status_code)
                    break

            # 3. 存入缓存（1 小时）
            if all_results:
                cache_data = [label.to_dict() for label in all_results]
                self.cache.set(cache_key, json.dumps(cache_data), ttl=3600)
                logger.debug("Cached %d FDA search results for %s", len(all_results), query)
            else:
                logger.warning("No FDA labels found for %s", query)
                # 缓存空结果（10分钟），避免重复查询
                self.cache.set(cache_key, json.dumps([]), ttl=600)
            
            return all_results
        
        except requests.exceptions.Timeout:
            logger.warning("FDA API timeout for %s", query)
            return []

        except requests.exceptions.RequestException as e:
            logger.warning("FDA API request error for %s: %s", query, e)
            return []

        except Exception as e:
            logger.error("Unexpected error searching FDA for %s: %s", query, e)
            return []
    
    def search_drugs(self, query: str, limit: int = 5) -> list:
        """
        搜索药物（返回原始数据，带缓存）
        
        Args:
            query: 搜索查询
            limit: 返回结果数量
            
        Returns:
            搜索结果列表（原始 FDA API 数据）
        """
        cache_key = f"fda_raw_search:{query.lower()}:{limit}"
        
        # 尝试从缓存获取
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            logger.debug("Cache hit for FDA raw search: %s", query)
            try:
                return json.loads(cached_data) if isinstance(cached_data, str) else cached_data
            except json.JSONDecodeError:
                logger.warning("Cache data corrupted, fetching fresh")
        
        # 调用 API
        logger.debug("Cache miss for FDA raw search: %s, calling FDA API", query)
        
        try:
            params = {
                "search": query,
                "limit": limit
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # 存入缓存（1 小时）
                self.cache.set(cache_key, json.dumps(results), ttl=3600)
                
                return results
            
            else:
                logger.warning("FDA API returned status %d", response.status_code)
                return []

        except Exception as e:
            logger.error("Error searching FDA: %s", e)
            return []
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return self.cache.get_stats()
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()


# 全局实例（推荐使用）
fda_client_cached = FDAClientCached()


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("Testing FDAClientCached")
    print("=" * 60)
    
    client = FDAClientCached()
    
    # 测试 1: get_drug_label
    print("\n=== Test 1: get_drug_label (first call - API) ===")
    label1 = client.get_drug_label("Metformin")
    print(f"Found: {bool(label1)}")
    
    print("\n=== Test 1: get_drug_label (second call - cache) ===")
    label2 = client.get_drug_label("Metformin")
    print(f"Found: {bool(label2)}")
    print(f"Same result: {label1 == label2}")
    
    # 测试 2: search_drug_labels_sync
    print("\n=== Test 2: search_drug_labels_sync (first call - API) ===")
    labels1 = client.search_drug_labels_sync("Aspirin", limit=2)
    print(f"Found {len(labels1)} labels")
    if labels1:
        print(f"First label drug name: {labels1[0].drug_name}")
        print(f"Has warnings: {bool(labels1[0].warnings)}")
    
    print("\n=== Test 2: search_drug_labels_sync (second call - cache) ===")
    labels2 = client.search_drug_labels_sync("Aspirin", limit=2)
    print(f"Found {len(labels2)} labels (from cache)")
    
    # 测试 3: to_dict 和 to_text
    if labels1:
        print("\n=== Test 3: FDADrugLabel methods ===")
        label = labels1[0]
        print(f"to_dict keys: {list(label.to_dict().keys())}")
        print(f"to_text preview: {label.to_text()[:100]}...")
    
    # 测试 4: 缓存统计
    print("\n=== Test 4: Cache statistics ===")
    stats = client.get_cache_stats()
    print(f"Cache stats: {stats}")