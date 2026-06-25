# Vela Blog 實作 Spec(給 Claude Code 執行)

**目標**:在 vela.an-tho.com/blog 加 Blog 功能,完全複用 §4.6 Explore 的 DB-backed Jinja2 SSR 模式。
**前置**:勘查報告已確認 stack(Next.js static export + FastAPI Jinja2 SEO pages + Neon DB)。Blog mirror §4.6 Explore。
**HEAD 基準**:fae8626

---

## 核心架構決定(已拍板)

選項 A:FastAPI Jinja2 SSR + DB-backed markdown,mirror §4.6 Explore pattern。

理由:同 stack、同 deploy story、滿足「更新內容不 redeploy」、FAQPage schema 從現有 {% block jsonld %} 自然延伸、復用 design tokens + markdown/citation helpers + Pillow OG image pipeline。

**內容更新流程**:edit content/blog/{slug}.{locale}.md → python scripts/blog_cli.py sync → 寫入 Neon DB blog_post table → 即時生效,zero redeploy。

---

## MVP 範圍(嚴格遵守,不要 over-build)

做:
- /blog 列表頁(card grid 佈局)
- /blog/{slug} 單篇頁
- 每篇自動生成封面圖(Pillow,主題色 + 標題 + logo)
- 主題色系統(見下方配色規則)
- 每張 card:封面圖 + 標題 + 日期 + theme 標籤
- FAQPage JSON-LD schema(末尾 FAQ)
- sitemap-blog.xml
- en + zh-TW 兩語言(UI strings + 內容),NOT 16 語言

不要做(明確排除):
- 影片縮圖
- 手動設計每篇封面(但保留 cover_image frontmatter 可選覆蓋)
- 分類篩選 / 搜尋 / 分頁(文章 < 10 篇用不到)
- 留言 / 分享按鈕 / 相關文章
- 16 語言 UI(只 en + zh-TW)
- ISR(stack 是 static export,不支援,本來就走 FastAPI SSR)

---

## 配色規則(主題色系統)

每篇 .md frontmatter 標 `theme:` 字串,決定封面圖背景色 + card 標籤色。

| theme 值 | 主題色 | 色碼來源 |
| --- | --- | --- |
| research | 暖橘色 | **讀既有 codebase 的 Research UI 色碼**(找 research.tsx / Tailwind config 對應色) |
| verify | 淡藍色 | **讀既有 Verify UI 色碼**(verify.tsx) |
| explain | 亮綠色 | **讀既有 Explain UI 色碼**(explain.tsx) |
| privacy | lavender | 復用 explore_base.jinja2 design tokens(若無則新增) |
| allied-health | sage green | 同上 |
| asia | coral | explore_base.jinja2 已有 coral token,直接用 |
| strategy | 淺灰色(中性,default) | 新增中性淺灰 token,#F0F0F0 ~ #E8E8E8 區間,Claude Code 選對齊既有設計的灰階 |

規則:
- frontmatter 沒標 theme → fallback 到 `strategy`(淺灰)
- 封面圖背景 = theme 對應色
- 無效 theme 值 → fallback strategy + log warning

**重要**:research/verify/explain 三色必須讀既有 codebase 真實色碼,不要自己編。先 grep 找到實際 hex 再用。

---

## 封面圖生成(路線 3:自動 + 可手動覆蓋)

預設:Pillow 自動生成。復用 explore_renderer.py 既有 OG image pipeline。

封面圖佈局:
```
┌─────────────────────────────┐
│  [theme 主題色背景]           │
│                              │
│  {文章標題}                   │  ← frontmatter title,自動換行
│                              │
│  Vela for Work · {theme標籤}  │  ← 底部標籤
│         [Vela logo]          │
└─────────────────────────────┘
```
- 尺寸:對齊既有 OG image 尺寸(explore_renderer 用什麼就用什麼,通常 1200x630)
- 寫入:static/og/blog/{slug}-{locale}.png(idempotent,mirror explore 的 static/og/explore/ pattern)
- 字體:復用 explore_renderer 既有字體

可選覆蓋:frontmatter 有 `cover_image: /path/to/custom.png` → 用手動圖,跳過自動生成。

---

## 實作元件清單

### 1. Migration 008_add_blog_post.sql
Mirror ExplorePage schema(見既有 migration for explore_page table)。

欄位:
- slug (varchar) + locale (varchar) → 複合 PK
- title (varchar)
- summary (text) — card 顯示的一句摘要
- body_markdown (text) — 文章內容
- theme (varchar) — 配色用,default 'strategy'
- cover_image (varchar, nullable) — 手動覆蓋用
- faqs (jsonb, nullable) — FAQPage schema 用,結構 [{"q":"...","a":"..."}]
- tags (jsonb, nullable)
- status (varchar) — draft / published,mirror explore_page enum
- published_at (timestamptz)
- created_at / updated_at (timestamptz, default now())

注意:無 auto-migrate runner(TECH_DEBT schema_versions)。deploy 前手動 psql -f migrations/008_add_blog_post.sql 對 Neon prod 跑。

### 2. ORM model — BlogPost
Mirror ExplorePage model(找既有 explore_page model 檔案,複製結構)。

### 3. scripts/blog_cli.py
Clone scripts/explore_cli.py 結構。

指令:
- python scripts/blog_cli.py sync — 掃 content/blog/*.md → parse frontmatter + body → UPSERT 進 blog_post table
- python scripts/blog_cli.py list — 列出 DB 中所有 blog post(debug 用)
- 復用 explore_cli.py 的 _parse_markdown(--- 分隔 + yaml.safe_load)

frontmatter 格式:
```
---
title: "Why Asian Medical AI Needs a Different Playbook"
slug: "asian-medical-ai-playbook"
locale: "en"
theme: "asia"
summary: "Three structural factors that don't translate from US medical AI."
status: "published"
published_at: "2026-06-04"
tags: ["medical-ai", "asia", "allied-health"]
cover_image: null
faqs:
  - q: "Why can't US medical AI tools just be translated for Asian markets?"
    a: "..."
  - q: "How do drug regulations differ across Asian countries?"
    a: "..."
---

{markdown body here}
```

### 4. api/services/blog_renderer.py
Mirror explore_renderer.py。

- render_blog_list(locale) → 讀 DB 所有 published post → render blog_list.jinja2
- render_blog_post(slug, locale) → 讀單篇 → markdown to HTML → render blog_post.jinja2
- 復用 share_renderer.py 的 _markdown_to_html / _augment_citations
- 復用 Pillow OG image 生成(封面圖),加 theme 色邏輯
- theme → 色碼 mapping function（讀既有色碼）

### 5. Templates
- api/templates/blog_list.jinja2 — extends explore_base.jinja2。card grid 佈局(CSS grid,responsive,desktop 3 欄 / tablet 2 欄 / mobile 1 欄)。每張 card:封面圖 + 標題 + 日期 + theme 標籤。
- api/templates/blog_post.jinja2 — extends explore_base.jinja2。文章內容 + 末尾 FAQ section。override {% block jsonld %} emit FAQPage schema。

FAQPage schema(填進 blog_post.jinja2 的 jsonld block):
```
{% block jsonld %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {% for faq in faqs %}
    {
      "@type": "Question",
      "name": {{ faq.q | tojson }},
      "acceptedAnswer": { "@type": "Answer", "text": {{ faq.a | tojson }} }
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
}
</script>
{% endblock %}
```

### 6. Routes in api/server.py
註冊在 Next.js catch-all (serve_nextjs_pages) 之前,mirror §4.6 explore route 順序(server.py:1907 附近)。

- GET /blog → serve_blog_list(locale from Accept-Language or query param)
- GET /blog/{slug} → serve_blog_post
- 404 handling:slug 不存在 → 適當 404 頁

### 7. sitemap-blog.xml
Mirror sitemap_explore.py。掛在既有 sitemap.xml index 下。列所有 published blog post 的 URL（en + zh-TW）。

### 8. i18n UI strings
加到 utils/i18n-ui.ts（既有結構）。只做 en + zh-TW。
keys: blog_title, blog_read_more, blog_published, blog_back_to_list, 等（~10 keys × 2 locales）。

---

## hreflang（SEO）
每篇 blog post 的 <head> 標 hreflang,只標真實存在的語言版本（en + zh-TW，若該篇只有 en 就只標 en）。NOT 16 語言。Mirror explore page 既有 hreflang 邏輯。

---

## 驗證清單（實作後）
- [ ] /blog 列表頁 render（card grid，封面圖顯示）
- [ ] /blog/{slug} 單篇 render（內容 + FAQ）
- [ ] FAQPage JSON-LD 在 initial HTML response 裡（curl /blog/{slug} 看 <script type="application/ld+json">）
- [ ] 7 個 theme 色都正確（research/verify/explain 對齊既有 UI 色，strategy 淺灰 fallback）
- [ ] 封面圖自動生成（static/og/blog/{slug}-{locale}.png）
- [ ] cover_image frontmatter 覆蓋有效
- [ ] blog_cli.py sync 寫入 DB，不需 redeploy 即生效（本機 sync 對 Neon 測）
- [ ] sitemap-blog.xml 列出 posts
- [ ] hreflang 只標真實語言（en + zh-TW）
- [ ] migration 008 deploy 前手動跑（記進 deploy checklist）

---

## 一次性 vs 重複成本
- 一次性開發:1.5-2 天
- 每篇新 post ship:~5 分鐘（edit md → blog_cli.py sync → publish）
- 唯一新 ops:migration 008 下次 deploy 前手動 psql -f 跑一次

## 不要做的事（再次強調）
- 不要引入 headless CMS / 新 hosting / 新 secret
- 不要碰 Next.js static export 設定
- 不要做 16 語言 UI
- 不要做影片縮圖 / 分類篩選 / 搜尋 / 分頁
- research/verify/explain 色碼必須讀既有 codebase，不要自編
