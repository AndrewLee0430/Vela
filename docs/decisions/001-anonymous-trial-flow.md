# Decision 001: Anonymous Trial Flow

**Status**: Proposed · pending team review
**Date**: 2026-04-18
**Version**: 0.2(supersedes v0.1 of same decision)
**Author**: andre (solo founder)
**Supersedes**: (none — first decision record)
**Superseded by**: (none — this is current)

---

## TL;DR

Vela 的 Landing Page 承諾 "No account required to try",但實際上點 "Try it for free" 會被 Clerk sign-in 擋住。此決策紀錄提出**兩層 UX / 三層資料**的設計,兌現 Privacy-first 承諾,同時對齊維運計畫 v3 的 10 credits/day 成本預算。

**關鍵決策**:
- 使用者感知兩層(Try free / Pro),內部資料分三層(L0 匿名 / L1 註冊免費 / L2 Pro)
- L0 credits:Research 2 / Verify 2 / **Explain 0**(保留 Explain 作為 L1 解鎖誘因)
- L1 credits:Research 2 / Verify 2 / Explain 1(= 10 credits total,對齊維運計畫)
- L1 同 L0 次數,升級感來自四個**解鎖新功能**:Explain / History / 跨裝置 / 個人化 + 品質升級
- L1 brand name:"Vela for Work"
- L0 使用 GPT-4.1-mini,L1 升級到 GPT-4.1
- Daily budget cap: $2 USD/day ($60/month hard ceiling)
- 排入 Phase 0,位於 § 2.4 之後、§ 2.7 之前,工期 1.5-2 天

### v0.1 → v0.2 主要變更

- **L1 credit 從 6/15/5 降為 2/2/1**,嚴格對齊維運計畫 § 8.3 的 10 credits/day 上限
- **L0 完全不開放 Explain**,把它當成 L1 的解鎖誘因(差異化更強)
- **L0 Verify 從 3 降為 2**,與 L1 一致(避免 L0 比 L1 還多的反邏輯)
- 新增 "Vela for Work" brand naming 與 CTA 文案設計
- L1 升級感的訴求從「量多」改為「解鎖 + 品質」
- 成本試算重算對齊新 credit 配置

---

## 1. Context(背景脈絡)

### 1.1 現況

使用者流程實測(2026-04-18 無痕視窗):

1. 打開 https://vela.an-tho.com
2. Landing Page 顯示承諾「🔒 Anonymous by Default. No identity verification. No account required to try.」
3. 點「Try it for free — no sign-up needed」按鈕
4. **被 redirect 到 Clerk sign-in 頁面,無法繼續**

### 1.2 PRD 承諾不一致

Master PRD v1.2 § 0.3「Privacy-first 定義」明列:

> We don't verify your identity or license
> We don't require your real name
> **No account required to try**

但實際上必須註冊 Clerk 帳號才能送第一個查詢。**這是承諾跳票**。

### 1.3 為什麼是 Phase 0 blocker

- **GTM 前置**:Phase 1A Week 1-2 要發 LinkedIn 第一篇 post「Why I built a medical AI that doesn't verify identity」。現況下 post credibility 為零。
- **差異化武器**:Vela 相對 OpenEvidence 的核心差異化是「不做身份驗證」。現況部分失去這個差異化。
- **L3 擴散基礎**:GTM v7.1 的 L3 被動渠道策略依賴「使用者進站 → 自發試用 → 口耳相傳」。試用門檻越低,L3 效應越強。

### 1.4 業界對照

查詢型 / 搜尋型 AI 產品,零登入試用是標配:

| 產品 | 零登入可做 |
|---|---|
| Perplexity | 完整查詢 + 答案 + citations |
| ChatGPT (2024+) | 完整對話(有限量) |
| Claude.ai | 訪客模式有限對話 |
| DuckDuckGo AI | 完全零登入 |

**Vela 目前的「必須登入才能試」在同類賽道是異常設計**。

---

## 2. Decision(決策)

### 2.1 高階設計:兩層 UX / 三層資料

對使用者感知:

- **Try it free**(零登入即可開始)
- **Pro $9.99/月**(完整功能)

內部資料分三層:

| 層級 | 身份 | 主要 Job-to-be-done |
|---|---|---|
| L0 匿名 | 沒登入 | 「這產品能不能解我的問題?」 |
| L1 註冊免費("Vela for Work") | Clerk 登入 | 「我要把這個納入日常工作流嗎?」 |
| L2 Pro 訂閱 | 付費 | 「這是我工作的關鍵工具」 |

### 2.2 為什麼需要 L1 層(不合併成兩層)

L1 不是為了給使用者多一點 quota,而是為了 **Vela 自己的資料飛輪**:

- **Cross-device identity**:使用者手機查完,電腦繼續看
- **Cohort retention 分析**:PRD Phase 1B 驗收指標「pharmacist Free → Pro 轉換率 ≥ 其他角色 2 倍」完全依賴 cohort tracking
- **Feedback 品質**:穩定身份讓 FeedbackBar 資料可信度提升一個數量級
- **Payment 前置**:Dodo 訂閱需要穩定 user ID
- **Power user 識別**:未來 user interview、testimonial、beta 測試名單來源

**把 L1 當成「為了讓資料飛輪轉起來」的投資層**,不是「給使用者的中間福利」。

### 2.3 Credit 配置(對齊維運計畫 v3 § 8.3)

| | Research | Verify | Explain | Model | Credit 總 |
|---|---|---|---|---|---|
| **L0 匿名** | 2/day | 2/day | **❌ 不開放** | GPT-4.1-mini | — |
| **L1 "Vela for Work"** | 2/day | 2/day | **1/day** | GPT-4.1 | **10 credits** ✅ |
| **L2 Pro** | ~30/day | ~100/day | ~50/day | GPT-4.1 | 100 credits cap |

**Credit 設計原則**:
- L0 次數是**讓使用者驗證 Vela 有用的最小集合**(Research 2 + Verify 2)
- L0 拿掉 Explain,讓它成為**L1 的解鎖誘因**(不是「量升級」是「功能升級」)
- L1 嚴格對齊維運計畫 § 8.3 的 10 credits/day,不超出既有成本預算
- L2 保留壓倒性優勢(~50x 查詢量 + PDF upload + Export + 365-day history)

### 2.4 L0 → L1 升級感設計(重要)

**核心 insight**:L1 跟 L0 次數相同,升級感不靠「量」,而靠「**四個解鎖新功能 + 品質升級**」。

| 維度 | L0 匿名 | L1 "Vela for Work" | 升級感來源 |
|---|---|---|---|
| Research 次數 | 2/day | 2/day | 同量但品質更深 ✅ |
| Verify 次數 | 2/day | 2/day | 同量但品質更深 |
| **Explain** | **❌ 不開放** | **1/day** | ⭐ **解鎖新功能** |
| **Model 品質** | GPT-4.1-mini | GPT-4.1 | ✅ **更好臨床推理** |
| **History** | Stateless | 7 天 | ⭐ **解鎖新功能** |
| **跨裝置同步** | ❌ | ✅ | ⭐ **解鎖新功能** |
| **個人化範例** | 通用池 | role-based | ⭐ **解鎖新功能** |
| FeedbackBar 送出 | 顯示但提示登入 | 可送出 | 小加值 |

**三個「解鎖新功能」(Explain / History / 跨裝置)+ 一個「品質升級」**。比純量升級有感 10 倍。

### 2.5 L1 Brand Name 與行銷語言("Vela for Work")

**命名**:L1 層在對外溝通時稱為 **"Vela for Work"**(免費帳戶版)。

**絕對不講的語言**:
- ❌ "GPT-4.1-mini vs GPT-4.1"
- ❌ "Upgraded AI model"
- ❌ "Better language model"
- ❌ "Advanced LLM"

**應該講的語言**:
- ✅ "Enhanced clinical reasoning"(強化的臨床推理)
- ✅ "Deeper answers"(更深入的答案)
- ✅ "Richer citation depth"(更豐富的引用)
- ✅ "Vela for Work"(工作用 Vela)
- ✅ "Full clinical context"(完整臨床脈絡)

### 2.6 Daily Budget Cap

**$2 USD/day(= $60/month hard ceiling)**,財務最後防線,防止:
- 流量爆發的成本失控
- 惡意攻擊(scraper / competitor sabotage)

超過 cap 後,新匿名請求返回 429 並顯示「Daily free trial capacity reached. Sign up (free) to continue, or try again tomorrow.」

**不影響已註冊 L1/L2 使用者**。

**重要**:$2/day 是**天花板**不是日常支出。實際預期:
- Phase 0 前期(無 GTM):$0.1-0.5/day
- Phase 1A 第一篇 post 後:$0.8-1.5/day
- LinkedIn post 爆紅:可能連續幾天撞 cap

### 2.7 UX 升級路徑(非阻斷式)

**時機 1:Landing Page(首次進站)**
- 按鈕文案:"Try it free — no sign-up"
- 點下去**直接進 Research 頁面**,不經過 Clerk
- Navbar 右上角「Sign in / Sign up」灰色小字,不強調

**時機 2:第 3 次查詢完成後(inline soft CTA)**
- 答案下方顯示可關閉的小 banner:
  > Enjoying Vela?
  > Sign up free — get deeper answers, saved history, and Explain
  > [Sign up, 30 sec] [Maybe later]

**時機 3:Quota 用完(最後防線)**
- Modal 顯示三個選項:
  ```
  You've used today's trial (3 queries)
  ─────────────────────────────

  📋 Sign up free (Vela for Work)
     Deeper answers + history + Explain feature
     [Sign up, 30 sec]

  ⏰ Continue tomorrow
     Trial mode resets in 24h

  ⚡ Go Pro ($9.99/mo)
     100+ queries/day + PDF upload + 365-day history
  ```

**絕對禁止**:
- 在查詢中途跳出註冊 CTA
- 第 1 次或第 2 次查詢後主動彈 CTA
- 把「明天再來」選項拿掉(違反 Privacy-first 承諾)

### 2.8 Landing Page 與 Pricing Page 文案

**Landing Page(SignedOut state)主 CTA 下方顯示**:

```
Try Vela free — no sign-up needed
Start with Research (2/day) + Verify (2/day)

─────────────────────────────

Want more? Sign up free to unlock:
  ✨ Explain — analyze medical reports in plain language
  📋 7-day history — across all your devices
  🎯 Role-based examples — pharmacist, nurse, physician
  🧠 Deeper clinical reasoning
```

**Pricing Page 三欄對照**:

```
                    Try       Vela for Work    Pro
                    (no auth) (free account)   ($9.99/mo)
─────────────────────────────────────────────────────────
Research queries    2/day     2/day            ~30/day
Verify queries      2/day     2/day            ~100/day
Explain (reports)   —         1/day            ~50/day
AI model           Quick      Full             Full
History            —          7 days           365 days + search
Cross-device       —          ✓                ✓
PDF upload         —          —                ✓
Export PDF         —          —                ✓
```

---

## 3. Technical Implementation(技術實作)

### 3.1 Backend

#### Anonymous identity middleware

```python
# api/middleware/anonymous_identity.py (NEW)

import hashlib
from fastapi import Request

def get_anonymous_id(request: Request) -> str:
    """
    匿名 session 的穩定 ID = IP + browser fingerprint。
    前端透過 X-Anon-Fingerprint header 送 PostHog distinct_id。
    SHA-256 前 16 字元,不可逆 (privacy-first)。
    """
    ip = get_client_ip(request)
    fingerprint = request.headers.get("X-Anon-Fingerprint", "")
    return hashlib.sha256(f"{ip}:{fingerprint}".encode()).hexdigest()[:16]
```

#### Quota service extension

```python
# api/services/usage_service.py (MODIFY)

ANONYMOUS_LIMITS = {"research": 2, "verify": 2, "explain": 0}  # Explain disabled
L1_LIMITS = {"research": 2, "verify": 2, "explain": 1}          # = 10 credits total
L2_LIMITS = {"research": 100, "verify": 100, "explain": 100}    # de-facto unlimited

class UsageService:
    async def check_quota(
        self,
        user_id: str | None,
        anon_id: str | None,
        feature: str,
    ) -> QuotaResult:
        if user_id:
            return await self._check_registered(user_id, feature)
        return await self._check_anonymous(anon_id, feature)

    async def _check_anonymous(self, anon_id: str, feature: str):
        # Explicit reject for Explain at L0
        if feature == "explain":
            raise FeatureNotAvailable(
                feature="explain",
                tier="anonymous",
                upgrade_hint="Sign up free to unlock Explain feature"
            )

        key = f"anon_quota:{anon_id}:{feature}:{today_utc()}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, 86400)  # 24h TTL

        limit = ANONYMOUS_LIMITS[feature]
        if count > limit:
            raise QuotaExceeded(
                tier="anonymous",
                feature=feature,
                limit=limit,
                upgrade_hint=f"Sign up (free) for 'Vela for Work' — includes Explain + history"
            )
        return QuotaResult(remaining=limit - count, tier="anonymous")
```

#### Auth middleware 改為可選

```python
# api/middleware/auth.py (MODIFY)

async def require_auth_or_anonymous(request: Request) -> User | AnonymousUser:
    token = extract_bearer_token(request)
    if token:
        return await verify_clerk_jwt(token)
    return AnonymousUser(anon_id=get_anonymous_id(request))
```

#### Model tier routing

```python
# api/providers/factory.py (MODIFY)

def get_generator(is_anonymous: bool = False):
    """
    Anonymous users use GPT-4.1-mini for cost control.
    Registered users use GPT-4.1 for full clinical reasoning.
    """
    model = "gpt-4.1-mini" if is_anonymous else "gpt-4.1"
    return get_provider().chat_model(model)
```

#### Daily budget cap

```python
# api/middleware/cost_budget.py (NEW)

ANONYMOUS_DAILY_BUDGET_USD = 2.00  # = $60/month hard ceiling

async def check_anonymous_budget(request: Request):
    if not isinstance(request.state.user, AnonymousUser):
        return  # Registered users bypass this check

    today = today_utc()
    spent = float(await redis.get(f"anon_cost:{today}") or 0)
    if spent >= ANONYMOUS_DAILY_BUDGET_USD:
        raise AnonymousBudgetExhausted(
            budget=ANONYMOUS_DAILY_BUDGET_USD,
            message_i18n_key="errors.anonymous_budget_exhausted"
        )
```

### 3.2 Frontend

#### Landing Page CTA

```tsx
// pages/index.tsx (MODIFY)

<Link href="/research">
  Try it free — no sign-up
</Link>
// 移除原本強制 redirect 到 /sign-in 的邏輯
```

#### Pages support anonymous

```tsx
// pages/research.tsx, pages/verify.tsx (MODIFY)

export default function Research() {
  const { isSignedIn } = useUser();
  const [anonId] = useState(() => posthog.get_distinct_id());

  const makeRequest = async (query: string) => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (isSignedIn) {
      headers["Authorization"] = `Bearer ${await getToken()}`;
    } else {
      headers["X-Anon-Fingerprint"] = anonId;
    }

    // existing SSE logic continues
  };
}
```

#### Explain page: L0 redirect to sign-up

```tsx
// pages/explain.tsx (MODIFY)

export default function Explain() {
  const { isSignedIn } = useUser();

  if (!isSignedIn) {
    return <ExplainLockedForAnonymous />; // Show sign-up CTA
  }

  // existing Explain logic continues
}
```

#### Soft CTA component

```tsx
// components/AnonymousUpgradeCTA.tsx (NEW)

type Trigger = "third_query" | "quota_hit" | "explain_locked";

export function AnonymousUpgradeCTA({ trigger }: { trigger: Trigger }) {
  const { isSignedIn } = useUser();
  if (isSignedIn) return null;

  const messages = {
    third_query: {
      title: "Enjoying Vela?",
      body: "Sign up free — get deeper answers, saved history, and Explain",
    },
    quota_hit: { /* Modal content */ },
    explain_locked: {
      title: "Explain is a free feature — sign up to unlock",
      body: "Upload medical reports and get plain-language analysis",
    },
  };

  return <InlineBanner {...messages[trigger]} />;
}
```

### 3.3 Database schema

```sql
-- For analytics and cost tracking only. No PII.
CREATE TABLE anonymous_usage (
    anon_id VARCHAR(16) NOT NULL,     -- SHA-256 first 16 chars
    feature VARCHAR(20) NOT NULL,
    day DATE NOT NULL,
    count INTEGER DEFAULT 0,
    total_cost_usd NUMERIC(10,4) DEFAULT 0,
    PRIMARY KEY (anon_id, feature, day)
);

-- Daily cron: delete rows older than 7 days (privacy-first)
-- This runs in api/services/cleanup_service.py (existing 180-day cleanup)
```

### 3.4 Config(env-driven,避免改 code)

```bash
# Recommended: move quota limits to env vars or config file
# so adjustments don't require redeploy.

ANONYMOUS_LIMIT_RESEARCH=2
ANONYMOUS_LIMIT_VERIFY=2
ANONYMOUS_LIMIT_EXPLAIN=0     # 0 = disabled for anonymous

L1_LIMIT_RESEARCH=2
L1_LIMIT_VERIFY=2
L1_LIMIT_EXPLAIN=1

ANONYMOUS_DAILY_BUDGET_USD=2.00
ANONYMOUS_MODEL_TIER=mini
```

### 3.5 PostHog tracking

New events (via `utils/analytics.ts track()`):

```typescript
track("anonymous_query_submitted", { feature, anon_id });
track("anonymous_quota_hit", { feature, attempts });
track("anonymous_cta_shown", { trigger, query_count });
track("anonymous_cta_clicked", { trigger });
track("anonymous_to_registered", { signup_method });
track("explain_locked_viewed", { anon_id });  // NEW: L0 users hitting Explain
// PostHog alias anonymous distinct_id → Clerk user_id on signup
```

---

## 4. Abuse Prevention(防濫用)

### 4.1 Multi-layer defense

| 層級 | 機制 | 擋住 | 擋不住 |
|---|---|---|---|
| 1 | IP rate limit(擴充既有 `RATE_LIMITS`)| 人工手動濫用 | 分散 IP |
| 2 | Browser fingerprint(PostHog distinct_id + UA) | 同瀏覽器清 cookie 重試 | 換瀏覽器/裝置 |
| 3 | Proof of Work challenge(前端 2-3 秒 SHA-256 prefix,可選) | Script 自動化 | 人肉慢速 |
| 4 | **Daily budget cap $2/day** | 成本災難 | (不需擋,cap 就是終點) |
| 5 | Anomaly detection(Sentry / PostHog alert) | 協調攻擊 | — |

### 4.2 不使用 reCAPTCHA 的理由

reCAPTCHA v3(隱形驗證)雖然是主流防 bot 工具,但跟 Vela 有三層衝突:

1. **Privacy 衝突**:reCAPTCHA 把使用者行為資料送給 Google,與「Privacy-first」承諾矛盾
2. **GDPR 合規風險**:歐盟多次判決 reCAPTCHA 未經同意使用屬違法 tracking
3. **LinkedIn 敘事受損**:「not even me」的承諾被戳破

若未來真需要額外 bot 防護,優先順序:
- 先做 PoW(自家實作,零外部依賴)
- PoW 不夠再考慮 Cloudflare Turnstile(privacy-respecting)
- **永遠不走 reCAPTCHA**

### 4.3 可接受的 abuse 成本

不追求 zero abuse,而是**可預測範圍內**。最壞情況每月 $60,視為「開放試用行銷預算」。

### 4.4 不做的事

- ❌ 手機號碼驗證(違反 privacy-first)
- ❌ CAPTCHA(破壞體驗)
- ❌ Email verification before first query(違反「無需註冊即可試」)
- ❌ reCAPTCHA(見 4.2)

---

## 5. Cost Analysis(成本試算)

### 5.1 單次查詢成本

| Feature | 匿名(mini) | 註冊(4.1) |
|---|---|---|
| Research | ~$0.005 | ~$0.022 |
| Verify | ~$0.003 | ~$0.003 |
| Explain | N/A(不開放) | ~$0.014 |

**Note**: 這些是 order-of-magnitude 估計。實際數字透過 `api/services/cost_tracker.py` 校準。

### 5.2 L0 匿名流量成本(新配置)

- 每人每日上限成本(100% utilization):2 × $0.005 + 2 × $0.003 = **$0.016**
- 實際(60% utilization):~$0.010/人/天
- Daily cap $2/day → 可服務 **~200 人/天**
- 月上限成本 **$60**

### 5.3 L1 註冊流量成本

- 每人每日上限成本(100% utilization):2 × $0.022 + 2 × $0.003 + 1 × $0.014 = **$0.062**
- 實際(60% utilization):~$0.037/人/天

**對照維運計畫 v3 § 8.3 原本預估**:
- 原假設每活躍 Free 用戶月成本 ~$0.18 → 每日 $0.006
- 新配置實際每日 ~$0.037 → 月成本 ~$1.11

**差異原因**:維運計畫的 $0.18 假設 credits 成本低估,實際 GPT-4.1 token 成本比想像高。**這是維運計畫需要校準的地方**,不是本決策造成的問題。

### 5.4 三種情境推估(L0 匿名部分)

**保守情境**
- 流量:70 人/天
- 成本:~$0.7/day = $21/月
- 匿名 → L1 轉換 8% × L1 → L2 轉換 5%
- 新增 Pro:~8/月 = $80 MRR
- **Net: +$59/月**

**基準情境**
- 流量:150 人/天(接近 $2 cap)
- 成本:~$1.5/day ≈ $45/月
- 新增 Pro:~17/月 = $170 MRR
- **Net: +$125/月**

**樂觀情境(LinkedIn post 發酵)**
- 流量:500+ 人/天(cap 觸發,實際只服務前 ~200 人)
- 成本:$60/月(因 cap)
- 被擋使用者部分轉 L1 註冊
- 新增 Pro:~28/月 = $280 MRR
- **Net: +$220/月**

### 5.5 風險情境

**惡意 scraper**:多層防護後實際穿透 ~5%,加上 $60 cap = 最壞 $60/月損失
**分散式攻擊**:$60 cap 是終點,實際損失 ≤ $60/月

### 5.6 12 個月 break-even

保守預估:**2-3 個月內淨正**,12 個月累積淨貢獻 $1,500-$3,500,並累積 ~5,000-10,000 匿名觸及(L3 擴散基礎)。

---

## 6. Consequences(後果與追蹤)

### 6.1 正面

- 兌現 Privacy-first 承諾 → Landing Page / PRD / GTM 文案與實作一致
- LinkedIn 第一篇 post「privacy-first manifesto」可信度滿分
- 相對 OpenEvidence 的結構性差異化確立
- L3 擴散基礎建立
- 匿名 cohort 資料開始累積,為 Phase 1A/1B 決策提供依據
- **L1 升級誘因更強**(Explain 解鎖 + 品質升級 + 三個新功能),不依賴量增加

### 6.2 負面

- Phase 0 時程延長 1.5-2 天
- 每月固定 ~$20-60 營運成本(trade-off 可接受)
- 技術複雜度增加(新 middleware、model tier routing、budget cap 監控)
- Abuse 風險存在(mitigated by multi-layer defense)
- **L0/L1 次數相同**可能讓部分使用者覺得「升級不划算」(依賴 UI 清楚展示 Explain + history + 跨裝置的價值)

### 6.3 需要追蹤的指標(Phase 1A Week 4 review)

| 指標 | 訊號 | 動作 |
|---|---|---|
| L0 quota 用完比例 < 10% | quota 太寬 | L0 降 Research 到 1 |
| L0 quota 用完比例 > 40% | quota 太緊 | L0 放寬或 L1 誘因加大 |
| **L0 試 Explain 被擋比例** | 若 < 20% | 沒人好奇 Explain,L1 的 Explain 解鎖誘因弱化 |
| **L0 試 Explain 被擋比例** | 若 > 50% | Explain 是真實剛需,L1 轉換動機強 |
| 匿名 → L1 轉換率 < 3% | L1 誘因不夠 | CTA 文案優化或 L1 差距拉大 |
| 匿名 → L1 轉換率 > 15% | 誘因太強 / 流量低 | 考慮擴大 L0 預算 |
| Daily cap 每天觸發 | 流量超預期 | 提 cap 到 $5/day 或優化成本 |
| Daily cap 從未觸發 | GTM 流量問題 | 非 cost 問題,重新檢視 GTM |

### 6.4 可退出機制

若 3-6 個月後資料顯示匿名轉換太差:
- **降級為軟提示方案**:保留 L0 但每次查詢後有 CTA
- **L0 開放 Explain 1 次**:如果「Explain 解鎖」沒成為升級動機
- **合併 L0/L1**:若證明 cohort tracking 非必要(較困難,需謹慎)

---

## 7. Alternatives Considered(已考慮的替代方案)

### 7.1 方案 B:軟提示註冊

每次查詢完都顯示 CTA,即使 quota 未用完。

- **優點**:conversion 更積極
- **缺點**:TA 群 privacy-sensitive,每次 CTA 反而傷信任
- **拒絕理由**:跟 privacy-first narrative 衝突

### 7.2 方案 C:改話術,保持登入要求

只修改 Landing Page 文案,承認需要 email。

- **優點**:15 分鐘可完成,零技術風險
- **缺點**:自願放棄 vs OpenEvidence 最有力差異化
- **拒絕理由**:長期護城河損失大於短期省時間

### 7.3 兩層方案(合併 L0/L1)

對使用者:Try free(含 email 註冊)→ Pro。完全拿掉 L0 匿名層。

- **優點**:簡單,資料飛輪完整
- **缺點**:放棄 privacy-first 承諾
- **拒絕理由**:解決不了原本的 gap

### 7.4 L1 給更多量(v0.1 舊設計:6/15/5 = 43 credits)

- **優點**:升級感強
- **缺點**:嚴重超出維運計畫 v3 的 10 credits/day 預算
- **拒絕理由**:成本無法控制,違反既有財務規劃

### 7.5 L0 開放 Explain(v0.1 舊設計:2/5/2)

- **優點**:使用者能完整試所有 feature
- **缺點**:Explain 是 Vela 的差異化殺手級功能,給匿名使用者會弱化 L1 升級動機
- **拒絕理由**:Explain 作為 L1 解鎖誘因的心理效果更強

---

## 8. Open Questions(團隊討論前需釐清)

會議前團隊成員各自思考:

1. **$60/月固定成本可接受嗎?**(若否,是否接受 $30/月 = cap $1/day,流量減半)
2. **Phase 0 延長 1.5-2 天可接受嗎?**(從 2.4/2.7/2.1 哪項擠時間?)
3. **匿名使用者走 GPT-4.1-mini 品質可接受嗎?** 建議做 10 題真實 query 的 mini vs 4.1 盲測驗證
4. **「明天再來」選項絕對保留嗎?**(這是 privacy-first 承諾的底線)
5. **L0 完全不開放 Explain 會不會讓使用者試不出 Vela 的殺手級價值?**(還是反而成為 L1 升級誘因?)
6. **Phase 1A Week 4 review 由誰主導?**

---

## 9. Related Documents

- **PRD**:`docs/PRD.md` § 0.3(Privacy-first 定義)、§ 2.8(本決策的 PRD anchor)
- **GTM**:Vela_GTM_v7.1.docx § 5(渠道策略)、§ 12(R5 法律風險)、§ 15.0 v7.1 補充紀錄
- **維運計畫**:Vela_維運計畫_v3.docx § 8.3(10 credits/day 成本預算)
- **FEATURE_AUDIT**:`FEATURE_AUDIT.md` — Discovered Gap G1
- **CLAUDE.md**:Current Development Status — G1 標記 pending

---

## 10. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-04-18 | andre | Initial draft based on gap discovery |
| **0.2** | **2026-04-18** | **andre** | **L1 credit 對齊維運計畫 10 credits 上限;L0 拿掉 Explain 作為 L1 解鎖誘因;新增 "Vela for Work" naming 與 CTA 文案;成本重算** |

---

## 11. Approval

| Role | Name | Status | Date |
|---|---|---|---|
| Solo Founder | andre | ☐ Approved / ☐ Pending | |
| (if applicable) Team Member | | ☐ Approved / ☐ Pending | |
| (if applicable) Advisor | | ☐ Reviewed / ☐ Pending | |

決議後填入負責人、完成日期,並把 status 從 **Proposed** 改為 **Accepted** 或 **Rejected**。
