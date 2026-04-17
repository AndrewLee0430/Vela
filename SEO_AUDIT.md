# Vela 渲染方式與行銷可見度技術體檢

**日期：** 2026-04-17
**站點：** vela.an-tho.com
**範圍：** 只檢查、未修改任何程式碼

---

## 1. 渲染架構判斷

**框架：** Next.js 15.5.14（Pages Router）
**模式：** **SSG（Static Site Generation / Static Export）** — 建置時產生靜態 HTML，之後純前端 hydrate。

**證據：**
- `package.json:18` `"next": "^15.5.14"`，`"build": "next build"`
- `next.config.ts:5` `output: 'export'` — 這會輸出純靜態 HTML/JS，**不存在 SSR runtime**
- `pages/` 目錄存在（`_app.tsx, _document.tsx, index.tsx, pricing.tsx, ...`），確認是 Pages Router 而非 App Router
- 無 `getServerSideProps`、無 ISR（`output: 'export'` 根本不支援）

**各 route 的渲染方式（執行 `npm run build` 後 `out/` 的產物）：**

| URL | 輸出檔 | 實際渲染方式 |
|---|---|---|
| `/` | `out/index.html`（2.9 KB） | **🚨 pseudo-CSR**：SSG 但 top-level component 有 `if (!isLoaded) return <Spinner />` gate，HTML 只有 spinner |
| `/pricing` | `out/pricing.html`（9.8 KB） | ✅ SSG，完整內容在 HTML |
| `/privacy` | `out/privacy.html`（7.0 KB） | ✅ SSG |
| `/terms` | `out/terms.html` | ✅ SSG |
| `/refund` | `out/refund.html` | ✅ SSG |
| `/faq` | `out/faq.html`（20.3 KB） | ✅ SSG，全部 Q&A 在 HTML |
| `/research`, `/verify`, `/explain`, `/history` | 各自 `.html` | 需 auth 的 app 頁面，CSR-only（可接受） |

---

## 2. Landing Page 的 HTML 可見度檢查 🚨

**最嚴重的問題。**

`pages/index.tsx:537-551`:
```tsx
export default function Home() {
  const { isSignedIn, isLoaded } = useUser();
  if (!isLoaded) {
    return <div className="min-h-screen flex items-center justify-center"...>
      <div className="w-6 h-6 border-2 rounded-full animate-spin" ... />
    </div>;
  }
  return isSignedIn ? <Dashboard /> : <LandingPage />;
}
```

SSG 建置時 Clerk 的 `useUser()` 永遠回 `isLoaded=false`，所以 pre-render 進 HTML 的是 **spinner，不是 LandingPage**。這表示：
- `LandingPage` 元件內部透過 `<Head>` 定義的 `<title>`、`og:title`、`og:description`、`canonical`、`og:url`（`pages/index.tsx:259-268`）**完全沒進初始 HTML**
- 整個 Hero（Vela 大字、`heroTitle`、`heroSub`、typewriter prompts、三張 product showcase 卡）都沒進 HTML

**實際 `out/index.html` `<body>` 內容（貼原文）：**

```html
<body>
  <div id="__next">
    <div class="min-h-screen flex items-center justify-center"
         style="background:linear-gradient(135deg, #0a1628 0%, ...)">
      <div class="w-6 h-6 border-2 rounded-full animate-spin"
           style="border-color:rgba(255,255,255,0.15);border-top-color:#ff8e6e"></div>
    </div>
  </div>
  <script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{}},"page":"/",...}</script>
</body>
```

**禁用 JS 情況下，爬蟲只看到一個轉圈圈的 spinner，沒有任何文字。**

- Hero 標題 / 副標：❌ 不在初始 HTML
- 三大 value props（Research/Verify/Explain 卡）：❌ 不在初始 HTML
- 任何 meaningful 文字：❌ 完全沒有

對比 `/pricing`：SSG 正常、完整內容包含 H1「Pricing」、定價細節、Free/Pro feature list 都在初始 HTML。同一份 repo 裡證明 SSG 是 work 的，**只是 `/` 被 `isLoaded` gate 擋掉了**。

---

## 3. Meta Tags 與 Social Preview 檢查

針對 `out/index.html` 初始 HTML 逐項檢查：

| Tag | 狀態 | 備註 |
|---|---|---|
| `<title>` | ❌ **不存在** | 定義在 `LandingPage` 裡，被 `isLoaded` gate 擋掉 |
| `<meta name="description">` | ✅ 存在 | 但是 `_app.tsx:31` 的 **fallback 通用描述**（"Research PubMed 36M+, verify..."），非頁面專屬 |
| `<meta property="og:title">` | ❌ **不存在** | 定義在 `LandingPage` 裡，未輸出 |
| `<meta property="og:description">` | ❌ **不存在** | 同上 |
| `<meta property="og:image">` | ✅ 存在 | `_app.tsx:34` 全域 fallback，`https://vela.an-tho.com/og-image.png` 1200x630 |
| `<meta property="og:url">` | ❌ **不存在** | 定義在 `LandingPage` 裡 |
| `<meta property="og:type">` | ✅ 存在 | `_app.tsx:32` `"website"` |
| `<meta property="og:site_name">` | ✅ 存在 | `_app.tsx:33` `"Vela"` |
| `<meta name="twitter:card">` | ✅ 存在 | `_app.tsx:37` `"summary_large_image"` |
| `<meta name="twitter:title">` | ❌ **不存在** | 定義在 `LandingPage` 裡 |
| `<meta name="twitter:description">` | ❌ **不存在** | 同上 |
| `<meta name="twitter:image">` | ✅ 存在 | `_app.tsx:38` |
| `<link rel="canonical">` | ❌ **不存在** | `LandingPage` 有但未輸出 |
| `<meta name="robots">` | ❌ 不存在 | 無 explicit robots（預設 `all`，爬蟲可 index，尚可接受） |

**工具說明：** 使用 Next.js `next/head`。**`_app.tsx` 層級的 `<Head>` 會進 SSG HTML**（證實於所有頁面），但 `index.tsx` 頁面層級的 `<Head>` 只有在該元件實際被 render 到時才會被輸出。因為 `Home` 的 `isLoaded` gate 把 `LandingPage` 擋在 branch 後面，該頁面的 `<Head>` 永遠沒執行。

結果：Landing page **連自己的 title 都沒有**。瀏覽器 tab 會顯示 URL，LinkedIn/Twitter 預覽會 fallback 到最通用的字串。

---

## 4. robots.txt 與 sitemap.xml

✅ 兩個檔案都存在且在 `public/` 下（會直接複製到 build output）。

**`public/robots.txt`：**
```
User-agent: *
Allow: /
Sitemap: https://vela.an-tho.com/sitemap.xml
```
— 乾淨無誤，沒有錯誤 block。

**`public/sitemap.xml`：** 只有 4 筆：`/`、`/terms`、`/privacy`、`/refund`。

**缺的項目：** `/pricing`、`/faq`、`/research`、`/verify`、`/explain`（其中 faq 是內容最豐富的 public 頁面 20KB，竟然沒進 sitemap）。

---

## 5. 關鍵 Public 頁面清單

| URL | 存在 | Meta tags（初始 HTML）| 渲染 | 備註 |
|---|---|---|---|---|
| `/` | ✅ | ❌ 無 title/og:title/canonical | 🚨 spinner-only | 最嚴重 |
| `/about` | ❌ 無此頁 | — | — | 無 about page |
| `/pricing` | ✅ | ✅ title `"Pricing - Vela"` + description | SSG ✅ | OK |
| `/privacy` | ✅ | ✅ title + description（英文唯一） | SSG ✅ | 無 i18n |
| `/terms` | ✅ | ✅ | SSG ✅ | OK |
| `/refund` | ✅ | ✅ | SSG ✅ | OK |
| `/faq` | ✅ | ✅ title `"FAQ — Vela | Clinical AI..."` | SSG ✅ | 內容最豐富，但 sitemap 沒列 |
| `/research` | ✅ | ✅ | CSR（需 auth） | 不該 index |
| `/verify` | ✅ | ✅ | CSR（需 auth） | 不該 index |
| `/explain` | ✅ | ✅ | CSR（需 auth） | 不該 index |
| `/history` | ✅ | ✅ | CSR（需 auth） | 不該 index |

**無獨立 `/about`**，也無 blog / changelog 類內容頁。

---

## 6. 語系與 i18n SEO 處理

**狀況：❌ 完全沒做。**

- 不同語系 **無獨立 URL**、**無 query param**。全部靠 `utils/LangContext.tsx` 在前端讀 `localStorage.vela_lang` 切換 `translations[lang]` 物件
- `LangContext.tsx:15-23` SSR default 永遠是 `'en'`（`if (typeof window === 'undefined') return 'en'`），**SSG 產出的 HTML 文字全部是英文**，其他 15 語系只靠 JS 執行後重繪
- repo-wide grep `hreflang|rel=.alternate` **無任何匹配** → 完全沒有 `<link rel="alternate" hreflang="...">`
- 單一 `<html>` 也沒有 `lang` 屬性的動態化（output 是 `<html>` 沒 lang）

**後果：** Google 只會 index 英文版本，其他 15 語言的 SEO **等於零**。即使用戶從台灣搜「Vela 臨床 AI」，Google 也不會有中文版本可顯示，就算有也會是同一個 URL、同一個英文 snippet。

---

## 7. 核心 Web Vitals 粗估

**Bundle 總大小（`out/_next/static/chunks/`）：3.2 MB**（23 個 JS 檔），其中：
- `_app.js` **494 KB**（含 Clerk + PostHog + Sentry + React）
- `654-*.js` 247 KB（推測 React / runtime）
- `da2a79ec.*.js` **743 KB**（最大 chunk，可能是 PDF.js，explain 頁面才需要但目前看起來是 common chunk）
- `index-*.js` 23 KB

**FCP 估算：** SSG 本身 FCP 應該很快（靜態 HTML），但因為 `/` 只是 spinner，**「有意義內容」的 FCP ≈ JS download + Clerk 初始化**，在 3G 環境下大概 2-4 秒，在 WiFi 下 0.5-1 秒。

**SEO 影響的 performance 問題：**
- Spinner-only landing page → Lighthouse SEO audit 會報「No meaningful content」
- Clerk 的 `clerk.browser.js` 以 `async` 載入但是 beforeInteractive（見 `out/index.html` script 標籤），卻是首頁內容生成的 blocker
- `da2a79ec.*.js` 743 KB 如果是 common chunk（每頁都載）會拖累所有頁 TTI

---

## 8. 最終結論

### Q1：爬蟲可見度評分 → **4 / 10**

- ✅ 有 robots.txt、sitemap、global og:image、Clerk-independent 頁面（pricing/faq/privacy）SSG 正常 → +4
- 🚨 **Landing page 對爬蟲幾乎是空殼**（spinner shell），title / canonical / page-specific og:title 全都不在 HTML → −4
- 🚨 i18n 完全沒有 SEO 處理（無 hreflang、無語系 URL） → −2

Google 仍會 index 首頁（因為有 fallback description 和全域 og:image），但 SERP 片段會非常通用、不吸引點擊。Pricing/FAQ 會正常出現。LinkedIn/ChatGPT 抓首頁會看到「Vela」品牌字串（從 og:site_name），但抓不到標題和 value props。

### Q2：LinkedIn 分享首頁會長怎樣？

實測預測（基於現有 meta tag）：

- **Title：** 沒有 `og:title` 也沒有 `<title>`，LinkedIn 會 fallback 到 URL `"vela.an-tho.com"` 或空白
- **Description：** `"Research PubMed 36M+, verify drug interactions against FDA, and explain lab results in any language."`（全域 fallback，勉強 OK）
- **Thumbnail：** `https://vela.an-tho.com/og-image.png`（1200×630 ✅）
- **整體：** 縮圖存在但**沒標題**，看起來**破**（標題位置可能是網址或 "Vela"，缺少「Clinical AI for Healthcare Professionals」這個關鍵 positioning 字）

（建議實測：修完後用 LinkedIn Post Inspector 或 `https://www.opengraph.xyz` 驗證。）

### Q3：GTM 啟動前最優先修的三件事

**1. 拿掉 Landing Page 的 `isLoaded` spinner gate（最優先）** — 預估 1 小時
- `pages/index.tsx:540-549` 改成預設 render `<LandingPage />`（unauthenticated 版本），把「判斷已登入後切 Dashboard」放進 `<SignedIn>` / `<SignedOut>` 組件（Clerk 支援這個 pattern 且對 SSG 友善）。
- 這一步會同時修好：landing HTML 有內容 + `<Head>` 裡的 title/og:title/canonical 全部進 static HTML。
- 驗證：`npm run build` 後 `out/index.html` 應該從 2.9 KB 變成 10+ KB，`<title>` 和 `og:title` 會出現。

**2. 加 hreflang + 決定多語系 URL 策略** — 預估 3-5 小時（看要做到多完整）
- 最小版本：全站 `<link rel="alternate" hreflang="x-default" href="https://vela.an-tho.com/" />` + 英文同 URL，先宣告存在多語系。
- 完整版本：landing page 為每個主要市場（zh-TW / ja / en）產生獨立 URL（Next export 可以用 `getStaticPaths`），讓 Google 分別 index。
- 現況下其他 15 語言的 SEO 完全損失，是 GTM 進中文市場最大的 gap。

**3. 補齊 sitemap + Landing 結構化資料** — 預估 1-2 小時
- `public/sitemap.xml` 加入 `/pricing`、`/faq`（faq 最內容豐富、最適合 long-tail SEO）
- landing page 加 `Organization` + `SoftwareApplication` 的 JSON-LD schema.org，幫 Google / ChatGPT browsing 理解「這是什麼產品」
- 加 `<meta name="robots" content="index, follow">` 明確宣告，並對 `/research`、`/verify`、`/explain`、`/history` 加 `noindex`（app 頁面不該被 index）

**其他可延後但值得做：** Privacy Policy 翻譯（目前只有英文，但國際市場重要）、把 `da2a79ec.*.js` 743 KB 的大 chunk 降下來（動態 import PDF.js 到只有 explain 頁面載）。

---

**一句話總結：** 技術底子（Next.js SSG + sitemap + og:image + 多 public 頁面）其實 OK，但 **landing page 被 Clerk 的 `isLoaded` gate 一行程式碼毀掉 SEO**，加上完全沒有 i18n SEO，GTM 前至少要解決這兩件事才不會浪費後續的行銷預算。
