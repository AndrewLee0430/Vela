"""
PubMed API Client
使用 NCBI E-utilities API 搜尋和取得醫學文獻

API 文件：https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

import os
import logging
import httpx
from typing import Optional, List
from dataclasses import dataclass
from xml.etree import ElementTree as ET
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class PubMedArticle:
    """PubMed 文章資料結構"""
    pmid: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    pub_date: str
    doi: Optional[str] = None
    publication_types: List[str] = None  # PubMed PublicationType list (evidence-tier signal)

    @property
    def url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
    
    @property
    def source_id(self) -> str:
        return f"PMID:{self.pmid}"
    
    def to_text(self) -> str:
        """轉換為可用於 RAG 的文字格式"""
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."
        
        return f"""# {self.title}

**Authors:** {authors_str}
**Journal:** {self.journal} ({self.pub_date})
**PMID:** {self.pmid}

## Abstract
{self.abstract}
"""


class PubMedClient:
    """PubMed E-utilities API 客戶端"""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None
    ):
        """
        初始化 PubMed 客戶端
        
        Args:
            api_key: NCBI API key（可選，有的話 rate limit 提升到 10/秒）
            email: 聯絡 email（NCBI 建議提供）
        """
        self.api_key = api_key or os.getenv("PUBMED_API_KEY")
        self.email = email or os.getenv("NCBI_EMAIL", "medinotes@example.com")
        
        # Rate limit: 3/秒（無 API key）或 10/秒（有 API key）
        self.rate_limit_delay = 0.1 if self.api_key else 0.34
    
    def _build_params(self, **kwargs) -> dict:
        """建立 API 請求參數"""
        params = {**kwargs}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        return params
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance"
    ) -> List[str]:
        """
        搜尋 PubMed，返回 PMID 列表
        
        Args:
            query: 搜尋關鍵字
            max_results: 最多返回筆數
            sort: 排序方式 ("relevance" 或 "date")
            
        Returns:
            PMID 列表
        """
        # 參數驗證
        if not query or not query.strip():
            logger.warning("PubMed: Empty query")
            return []

        if max_results < 1:
            logger.warning("PubMed: Invalid max_results")
            return []
        
        try:
            params = self._build_params(
                db="pubmed",
                term=query,
                retmax=max_results,
                retmode="json",
                sort=sort
            )
            
            logger.debug("Searching PubMed (query len=%d)", len(query))
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/esearch.fcgi",
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
            
            await asyncio.sleep(self.rate_limit_delay)
            
            pmids = data.get("esearchresult", {}).get("idlist", [])
            logger.info("PubMed: Found %d articles", len(pmids))
            
            return pmids
        
        except httpx.TimeoutException as e:
            logger.warning("PubMed timeout: %s", type(e).__name__)
            return []

        except httpx.HTTPStatusError as e:
            logger.warning("PubMed HTTP error: %d", e.response.status_code)
            return []

        except ValueError as e:
            logger.warning("PubMed JSON parse error: %s", e)
            return []

        except Exception as e:
            logger.error("PubMed unexpected error: %s", type(e).__name__)
            return []
    
    async def fetch_details(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        根據 PMID 取得文章詳細資訊
        
        Args:
            pmids: PMID 列表
            
        Returns:
            PubMedArticle 列表
        """
        if not pmids:
            logger.warning("PubMed: No PMIDs to fetch")
            return []
        
        try:
            params = self._build_params(
                db="pubmed",
                id=",".join(pmids),
                retmode="xml",
                rettype="abstract"
            )
            
            logger.debug("Fetching details for %d PubMed articles", len(pmids))
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/efetch.fcgi",
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                xml_text = response.text
            
            await asyncio.sleep(self.rate_limit_delay)
            
            articles = self._parse_xml(xml_text)
            logger.info("PubMed: Parsed %d articles", len(articles))
            
            return articles
        
        except httpx.TimeoutException as e:
            logger.warning("PubMed fetch timeout: %s", e)
            return []

        except httpx.HTTPStatusError as e:
            logger.warning("PubMed fetch HTTP error: %d", e.response.status_code)
            return []

        except ValueError as e:
            # Python 3.11+ httpx/asyncio 在處理某些 XML response 時可能拋出
            # "second argument (exceptions) must be a non-empty sequence"
            # 這是函式庫的已知邊緣情況，安全忽略並回傳空結果
            logger.warning("PubMed fetch ValueError (likely httpx/asyncio edge case): %s", e)
            return []

        except Exception as e:
            logger.error("PubMed fetch unexpected error: %s: %s", type(e).__name__, e)
            return []
    
    def _parse_xml(self, xml_text: str) -> List[PubMedArticle]:
        """解析 PubMed XML 回應"""
        articles = []
        
        if not xml_text or not xml_text.strip():
            logger.warning("PubMed: Empty XML response")
            return articles
        
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error("PubMed XML parse error: %s", e)
            return articles
        except Exception as e:
            logger.error("PubMed XML unexpected error: %s: %s", type(e).__name__, e)
            return articles
        
        for article_elem in root.findall(".//PubmedArticle"):
            try:
                # PMID
                pmid = article_elem.findtext(".//PMID", "")
                if not pmid:
                    continue
                
                # Title
                title = article_elem.findtext(".//ArticleTitle", "")
                if not title:
                    continue
                
                # Abstract - 可能有多個段落
                abstract_parts = []
                for abstract_text in article_elem.findall(".//AbstractText"):
                    try:
                        label = abstract_text.get("Label", "")
                        text = abstract_text.text or ""
                        if label:
                            abstract_parts.append(f"**{label}:** {text}")
                        else:
                            abstract_parts.append(text)
                    except Exception:
                        continue
                
                abstract = "\n\n".join(abstract_parts)
                
                # 如果沒有 abstract，跳過
                if not abstract:
                    continue
                
                # Authors
                authors = []
                for author in article_elem.findall(".//Author"):
                    try:
                        last_name = author.findtext("LastName", "")
                        fore_name = author.findtext("ForeName", "")
                        if last_name:
                            authors.append(f"{last_name} {fore_name}".strip())
                    except Exception:
                        continue
                
                # Journal
                journal = article_elem.findtext(".//Journal/Title", "Unknown Journal")
                
                # Publication Date
                pub_date = article_elem.findtext(".//PubDate/Year", "")
                if not pub_date:
                    medline_date = article_elem.findtext(".//PubDate/MedlineDate", "")
                    if medline_date and len(medline_date) >= 4:
                        pub_date = medline_date[:4]  # 取前4個字元（年份）
                
                if not pub_date:
                    pub_date = "Unknown"
                
                # DOI
                doi = None
                try:
                    for id_elem in article_elem.findall(".//ArticleId"):
                        if id_elem.get("IdType") == "doi":
                            doi = id_elem.text
                            break
                except Exception:
                    pass

                # PublicationType list (evidence-tier signal, §2.10.6) — additive metadata;
                # never affects retrieval order/scores. Best-effort: any parse issue → [].
                publication_types = []
                try:
                    for pt in article_elem.findall(".//PublicationTypeList/PublicationType"):
                        if pt.text and pt.text.strip():
                            publication_types.append(pt.text.strip())
                except Exception:
                    publication_types = []

                articles.append(PubMedArticle(
                    pmid=pmid,
                    title=title,
                    abstract=abstract,
                    authors=authors or ["Unknown"],
                    journal=journal,
                    pub_date=pub_date,
                    doi=doi,
                    publication_types=publication_types,
                ))
                
            except KeyError as e:
                logger.warning("PubMed: Missing required field in article: %s", e)
                continue
            except TypeError as e:
                logger.warning("PubMed: Type error in article parsing: %s", e)
                continue
            except Exception as e:
                logger.warning("PubMed: Unexpected error parsing article: %s: %s", type(e).__name__, e)
                continue
        
        return articles
    
    async def search_and_fetch(
        self,
        query: str,
        max_results: int = 10
    ) -> List[PubMedArticle]:
        """
        搜尋並取得文章詳細資訊（組合方法）
        
        Args:
            query: 搜尋關鍵字
            max_results: 最多返回筆數
            
        Returns:
            PubMedArticle 列表
        """
        try:
            pmids = await self.search(query, max_results)
            if not pmids:
                logger.warning("PubMed: No results found (query len=%d)", len(query))
                return []
            
            articles = await self.fetch_details(pmids)
            return articles
        
        except Exception as e:
            logger.error("PubMed search_and_fetch error: %s", type(e).__name__)
            return []


# 同步版本的包裝函數（方便測試）
def search_pubmed_sync(query: str, max_results: int = 10) -> List[PubMedArticle]:
    """
    同步版本的 PubMed 搜尋
    
    Args:
        query: 搜尋關鍵字
        max_results: 最多返回筆數
        
    Returns:
        PubMedArticle 列表
    """
    try:
        client = PubMedClient()
        return asyncio.run(client.search_and_fetch(query, max_results))
    except Exception as e:
        logger.error("PubMed sync search error: %s", type(e).__name__)
        return []


# 測試用
if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("Testing PubMed Client")
        print("=" * 60)
        
        client = PubMedClient()
        
        # 測試 1: 正常查詢
        print("\n=== Test 1: Normal query ===")
        articles = await client.search_and_fetch("metformin diabetes", max_results=3)
        for article in articles:
            print(f"PMID: {article.pmid}")
            print(f"Title: {article.title}")
            print(f"URL: {article.url}")
            print("-" * 50)
        
        # 測試 2: 空查詢
        print("\n=== Test 2: Empty query ===")
        articles = await client.search_and_fetch("", max_results=3)
        print(f"Results: {len(articles)}")
        
        # 測試 3: 無結果查詢
        print("\n=== Test 3: No results query ===")
        articles = await client.search_and_fetch("xyzabc123nonexistent", max_results=3)
        print(f"Results: {len(articles)}")
    
    asyncio.run(test())