# TECH_DEBT.md — Vela Pre-Existing Gaps & Polish Items

Active tech debt entries identified during shipping. Format preserved verbose because each entry is dense diagnosis context — compressing to a table loses why/how-to-apply specificity.

**Priority levels**:
- **[P0]** — blocks shipping or user-facing
- **[P1]** — affects code quality or upcoming task
- **[P2]** — best practice / future maintenance
- **[P3]** — quality-of-life / cosmetic / opportunistic (added 2026-05-06 during §4.5 UX polish 3/3 — supersedes the earlier "no P3 tier" claim in the [P2] No backend PostHog client entry)

**Resolution targets**:
- "→ Phase 0 Retrospective" — work in retro phase
- "→ Phase 1A polish" — work after Phase 0 ends
- "→ next opportunity" — when convenient

When entries are resolved, mark with the resolving commit SHA (git log is the record), then remove.

---

- **[P2 → Phase 1B Week 4 polish] Verify 答案品質 nuance issues — dogfooding 發現 (2026-05-06)**
  - **背景**: solo founder 2026-05-06 dogfood query「為什麼亞洲老年人 polypharmacy 問題嚴重」的人工 review。所有 4 個 citation 真實存在 (PMID 38368398, 35268461, 37968631, 37574369)，無 hallucination。Retrieval 基礎正常運作。
  - **發現 5 個 nuance issues**:
    1. **Citation scope mismatch detection**: retrieval 取回的 citation population scope 與 query population scope 不 match 時，LLM 沒識別、沒 flag，silent 混入結論。範例：query「亞洲老年人」、retrieval 取回 PMID 37968631 (UK 東倫敦巴基斯坦移民老年人)，LLM 把它當作亞洲在地 evidence 引用。
    2. **Geographic over-generalization**: query 涉及廣域地理 (亞洲、全球、東亞)，LLM 沒 flag「我有哪些地區的 evidence、沒有哪些」。範例：query「亞洲老年人」、evidence 只覆蓋中國 + 馬來西亞 + 東倫敦巴基斯坦移民，沒有日韓泰越，但答案 framing 為通用「亞洲」結論。
    3. **Citation ranking bias toward recency over scope match**: 對 query 最 match 的 citation 沒被推到 anchor 位置。範例：query「亞洲社區老年人 polypharmacy」最 match 的是 PMID 37574369 (馬來西亞 primary care 393 人)，但 ranking 在第 4 位，前 3 位是中國 inpatient research，scope 較窄。
    4. **Counterintuitive finding 缺乏 mechanism explanation**: statistical association 直接呈現給使用者，沒附背後的 mechanism。範例：「多重用藥與死亡率略低相關」一般使用者會誤讀為「多吃藥較好」，實際 ChiOTEAF 研究的 mechanism 是「房顫族群中積極治療反映」。
    5. **LLM 自我評價字句**: 答案結尾出現「參考文獻均來自 2022 年以後，證據屬於近期且具代表性」這類 LLM 自評。應禁止 LLM 評價自己引用的品質。
  - **影響範圍**: 對藥師讀者影響 medium (會自己判讀)，對一般使用者影響 high (誤導風險)。不是 broken system，是 polish issue。
  - **Resolution**: 拆兩個 task 對應 Phase 1B
    - **Task A (Week 4)**: issue #1, #2, #4, #5 為 system prompt 類，順手放進 Verify 強制英文 + drug name resolution (ADR 003) 的 verify_system.md 修改階段。預估 system prompt polish 工時 +0.5-1 天 (Week 4 從 1.5-2 天延長到 2-2.5 天)。
    - **Task B (Week 7-8)**: issue #3 為 RAG retrieval ranking 改進，需單獨 evaluate。風險：改 ranking 演算法會影響所有 query 的答案，需要 regression test。建議在 Week 7-8 polish 階段 evaluate，視 risk 決定 Phase 1B vs Phase 1C 排程。
  - **驗證方法**: 持續 dogfooding 累積 5-10 個 query 樣本，混合 narrow query (e.g. metformin 腎功能調整) + broad query (e.g. 亞洲心血管疾病) + 邊緣 query (e.g. 越南藥品 BPOM 等同)，確認上述 issue 是系統性問題或 edge case。
  - **與顧問視角的對齊**: 另一顧問 review 同一份答案認為品質「臨床產品水準、零幻覺」。本 entry 不否定該視角 (retrieval 基礎沒壞、citation 真實、訊息萃取成功)，但採嚴格標準 polish 以對齊 PRD § 0.1 醫療專業者 TA 的 evidence rigour 期待。對 B2C 受眾另一顧問標準也合理。
  - **Discovered**: 2026-05-06 during solo founder dogfooding session

- **[P0 — Must resolve in 2.8]** localhost Clerk sign-in flow missing
  - **Partial progress**: Auth split (require_auth + require_auth_or_anonymous) completed in Round 1 (7a8c5a8). Remaining 3 items for Round 2 (frontend sign-in pages + ClerkProvider config + Clerk SDK config verification).
  - Root cause: `_app.tsx` ClerkProvider 使用 Clerk Hosted mode (no `signInUrl` / `signUpUrl` props), localhost 無法登入建立 session
  - Evidence: 2.4 localhost testing 時,前端無法登入;curl 用 production `await Clerk.session.getToken()` 取新鮮 JWT 測試後端,user_id 正確寫入 DB (user_3BQM...) → 證明 code 正確,只是環境限制
  - Resolution in 2.8:
    1. 加 `pages/sign-in/[[...index]].tsx` 和 `pages/sign-up/[[...index]].tsx`
    2. `_app.tsx` ClerkProvider 加 `signInUrl="/sign-in"` / `signUpUrl="/sign-up"` / fallback redirect URLs
    3. 補 AUTHORIZED_PARTIES config if Clerk SDK 要求

- **[P1 → Round 2B + 3 完成後一起 E2E 測試]** Clerk email sign-up/sign-in end-to-end 驗證
  - **背景**: 2026-04-22 localhost /sign-in 已確認 Clerk Development instance 有 email input(切 Dev instance + 啟用 email code verification 後解決)。Production instance email 設定也已確認 ON。
  - **尚未驗證**:
    - Email code 能否真的發到使用者信箱(依賴 Clerk email 發送能力)
    - 新使用者透過 email 註冊 → Clerk user 建立 → backend JWT 驗證成功 → /research 能載入
    - Email 與 SSO Google 同一 email 時,Clerk 如何處理(期待:同一 Clerk user)
  - **測試順序**(Round 2B + 3 完成後一起做):
    1. 無痕視窗 /sign-up → 輸入全新 email → 收 code → 輸入 → 完成註冊 → redirect /research
    2. 無痕視窗 /sign-in → 輸入 #1 註冊的 email → 收 code → 登入成功
    3. 新 email 註冊 → logout → 改用同 email Google SSO → 看 Clerk 是否合併 user
  - **Priority**: P1(2.8 完整驗收一部分),軟啟動前必須通過
  - **Discovered**: 2026-04-22 during Clerk Dev/Prod instance diagnostic

- **[P1] print() violations in api/** (54 處, audited 2026-04-19)
  - 生產路徑 9 處(影響 Sentry + log aggregation):
    - `fda.py:149/152/177` — FDA 請求失敗用 print 而非 logger
    - `simple_cache.py:90/111/179/183` — cache 事件(179/183 每次 cached call 都吵)
    - `vector_store.py:38/46` — 啟動 log;L46 含 ✅ emoji 在 Windows CP950 會爆
  - Test harness (`if __name__ == "__main__":`) 45 處,低優先
  - `fda_cached.py` 整檔為 dead code (CLAUDE.md 已標),可順手刪除
  - Resolution: 排入 Phase 0 Retrospective 一次清理
  - **2026-05-05 update**: Re-confirmed during §4.5 PHASE A smoke test on Windows local uvicorn — the `print()` at `vector_store.py:46` containing U+2705 (✅) crashes uvicorn boot under cp950 console. Workaround for local dev: `PYTHONIOENCODING=utf-8 PYTHONUTF8=1 uvicorn ...`. Production unaffected (Linux/UTF-8). Fix is still pending — replace with `logging.getLogger(__name__).info(...)` per CLAUDE.md Rule 4.
  - **2026-05-21 update**: Re-discovered during §3.1 PHASE B test work — the crash is now at `vector_store.py:52` (line shifted; same `print(f"✅ Vector store loaded...")` from commit 3e4471ed). Concrete test impact: blocks `import api.server` from any pytest module on Windows, which prevents constructing a `TestClient(app)` with dependency overrides → blocks endpoint-level integration tests (POST 403 free-user gate, POST 422 missing-field, GET 404, GET 200 round-trip, rate-limit). Workaround used in §3.1 PHASE B: idempotency verified at the SQL layer via `sqlite_insert.on_conflict_do_update` instead of through the endpoint (see `tests/models/test_user_profile.py`). One-line fix still pending; not P0 because production is Linux/UTF-8.

- **[P2] PowerShell 運行 `.env` parse warning**
  - `python-dotenv` 啟動時 warn `could not parse statement starting at line 1/2`
  - 不影響功能但 log 很吵
  - 可能原因:`.env` 檔 UTF-8 BOM,或前兩行有 shell export 語法
  - Resolution: Phase 0 Retrospective 清 .env 編碼

- **[P2] Chinese variant handling 已 spread(2026-04-20 完成),但 {response_language} pattern 仍不一致**
  - Verify 2.9 用 `{response_language}` 變數注入 system prompt
  - Research / Explain 用 `get_language_instruction()` append 到 user message
  - 兩套都 work,但 pattern 不一致,未來擴充語言 feature 要同步改兩處
  - Resolution: Phase 1A i18n mop-up 時統一 pattern(建議走 Verify 2.9 的 `{response_language}` 路線,同步 extract Research/Explain prompt to api/prompts/)
  - Discovered: 2026-04-20 during 2.9 Chinese variant handling spread

- **[P2] zh-TW / zh-CN severity Critical/Major 邊界 drift**
  - zh-TW dict: Critical=危急, Major=嚴重
  - zh-CN dict: Critical=严重, Major=重度
  - 兩套設計:zh-TW 是 Taiwan 醫療 triage 4 級視覺語彙,zh-CN 是結構對稱
  - Bilingual user 可能困惑(同字不同 severity)
  - Resolution: Phase 1A 找台灣 + 大陸母語醫療人員 review,決定統一或保留 drift

- **[P1] Research/Explain prompt 仍 inline 在 Python files(PRD § 6.5 違規)**
  - `generator.py` 有 4 個 inline prompt string(`_get_system_prompt` + `FALLBACK_PROMPTS` × 3)
  - `explain_service.py` 有 1 個 inline prompt(`EXPLAIN_GENERATION_PROMPT`)
  - 違反 PRD § 6.5 "All system prompts 在 api/prompts/ 目錄下獨立檔案"
  - 2.9 當下為了 scope 保護選擇 inline 編輯,未抽檔
  - Resolution: 2.7 Explain 臨床推理強化時順便 extract `explain_service.py`(已完成 — Step 5 e05102e);Research 的 prompt extract 排 Phase 1A
  - Discovered: 2026-04-20 during 2.9 Chinese variant handling spread diagnostic

- **[P2] Dead code in `api/rag/generator.py`**
  - `FALLBACK_PROMPTS["verify"]` (dict entry at line ~34): Verify 走 `api/prompts/verify_system.md` 不經 `generator.generate_stream`,此 key 從未被呼叫
  - `FALLBACK_PROMPTS["document"]` (dict entry at line ~34): 舊 patient-letter / consultation feature,全 codebase grep 無 caller
  - `_get_system_prompt()` `query_type == "verify"` branch (line ~263): 同上
  - Verification method: grep `query_type` + `FALLBACK_PROMPTS\[` 確認無活 caller,或 trace 從 /api endpoints 哪些 route 到 `generator.generate_stream`
  - Resolution: Phase 1A i18n mop-up 或 2.7 Explain 抽檔時順手 sweep dead code
  - Risk if kept: wasted maintenance attention, false impression for future readers, ~150-300 prompt tokens wasted per call (dead FALLBACK entries not triggered but pollute code)
  - Discovered: 2026-04-20 during 2.9 Chinese variant handling spread (diagnostic flagged)

- **[P0 → 已部分解決, status unclear]** Landing Page 收尾
  - 發現 2026-04-20(2.9 ship 後)
  - **兩個問題:**
    1. **Hero placeholder 硬寫英文** — 已解 (commit a22ce9f "Landing Page i18n 16-language expansion" 2026-04-21)
    2. **Privacy section 過長** — 5 條「我們承諾」+ 3 條「它不代表什麼」共 8 個 bullet。Privacy section 簡化狀態 unclear — verify at Phase 0 Retrospective.
       - 決策(solo founder 2026-04-20 review):
         - **刪除**:3 條「它不代表什麼」全部(移至 Privacy Policy 處理,該頁為 Phase 1A i18n mop-up)
         - **壓縮**:5 條承諾 → 3 條:
           - ✓ 不需驗證身分或執照
           - ✓ 預設匿名,不要求真實姓名
           - ✓ 資料不外流、不訓練 AI 模型
  - **Resolution at Phase 0 Retrospective**: verify Privacy section state in production. If still 8-bullet, apply the simplification per spec. Logged 1101dcc.

- **[P1 → Phase 0 Retrospective] CLAUDE.md 結構性精簡 — ✅ DOING NOW (2026-04-30 doc reorg)**
  - 問題:
    - 當前 ~574 行 (post § 2.7 結案),違反 LLM instruction budget 最佳實踐(社群共識 < 300 行)
    - 多處內容為 reference material 而非 instruction(architecture 詳細、env vars、file paths),違反 Progressive Disclosure pattern
    - Current Development Status / Discovered Gaps 與 FEATURE_AUDIT.md / decision docs 有 drift 風險
  - **Resolution in progress (2026-04-30 commits 3fdeddc, 59002d1, [this commit])**:
    1. ✅ Drift sync (3fdeddc)
    2. ✅ Architecture extract → docs/architecture.md (59002d1)
    3. ✅ STATE.md / BACKLOG.md / ARCHIVE.md / TECH_DEBT.md split (this commit)
    4. PRD.md status markers (next commit)
    5. ADR 002 doc reorg rationale (final commit)
  - 驗收:CLAUDE.md ~150 lines after this commit; new doc structure documented in ADR.
  - Discovered: 2026-04-21(Landing Page ship 後 solo founder 討論 instruction budget best practice 時識別)

- **[P2]** Clerk JWT authorized_parties (azp) claim 未驗證
  - **現況**: `api/server.py` 使用 hand-rolled `jose_jwt.decode` with `options={"verify_aud": False}`,依賴 JWKS RS256 簽名驗證 + issuer 隱式信任。未檢查 `azp` claim。
  - **風險**: 理論上若攻擊者能取得 Clerk 公開 JWKS 並知道 issuer,可能能 forge token 通過 signature verify。實務上極難(需拿到使用者 session token 或攻破 Clerk infra),但 defense-in-depth 標準作業應驗證 authorized_parties。
  - **Resolution**:
    - 新建 `CLERK_AUTHORIZED_PARTIES` env var(allowlist of origin URLs)
    - `api/server.py` JWT decode 後手動檢查 `azp` claim 在 allowlist 中
    - 或:改用 `fastapi_clerk_auth` 套件的完整驗證鏈(當前 import 未使用)
  - **Priority**: P2(未有明確攻擊 vector 但屬 best practice);排入 Phase 0 Retrospective 或 Phase 1A 安全 review
  - **Discovered**: 2026-04-22 during 2.8 Round 2A Clerk config diagnose

- **[P2 → Round 3 或 Phase 1A]** 阻止 signed-in user 訪問 `/sign-in` 和 `/sign-up`
  - **現況**: logged-in user 打 `/sign-in` 會看到 Clerk SignIn card,可能困惑
  - **解法**: `pages/sign-in/[[...index]].tsx` 和 `pages/sign-up/[[...index]].tsx` 頂部加 `<SignedIn><RedirectToResearch /></SignedIn>` wrapper(或 useEffect + router.push('/research'))
  - **Priority**: P2 UX polish
  - **Discovered**: 2026-04-22 during 2.8 Round 2B diagnose

- **[P2 → Phase 1A]** Backend error response shape 不統一
  - **現況**: pre-Round 1B endpoints 回 `{error: "code"}`,Round 1B 新 `api/errors.py` 回 `{type: "code", ...}`
  - **Round 2B frontend 處理**: dual-read pattern 兼容 `const code = data.type ?? data.error`
  - **解法**: Phase 1A 統一 endpoint error shape(建議走 `{type, message}` 新 shape),frontend 簡化掉 dual-read
  - **Priority**: P2 consistency
  - **Discovered**: 2026-04-22 during 2.8 Round 2B diagnose

- **[P1 → Round 3 已部分解決, verification needed]** Anonymous quota message 不 surface 正確 type
  - **現況**: E2E Test 4 發現 anon daily quota 耗盡時,前端顯示通用 "Too many requests. Please wait a moment and try again.",而非 Round 2B 預期的 "Daily free limit reached. Sign up to continue."
  - **Root cause 假設**: FastAPI `HTTPException(status_code=429, detail={type: "anonymous_quota_exceeded", ...})` 序列化後 response body 是 `{detail: {type: ...}}` 而非 `{type: ...}` → `utils/sse.ts` 的 dual-read `data.type ?? data.error` 抓不到(真實路徑應為 `data.detail?.type ?? data.type ?? data.error`)
  - **Round 3 commit 24b1d79 shipped AnonymousUpgradeCTA infrastructure**. Quota message specific fix verification still needed.
  - **Verification needed at Phase 0 Retrospective**: trigger anon daily quota in prod, confirm correct message + CTA path appears.
  - **Priority**: P1(軟啟動前必須 fix,影響 anon-to-signup 轉換訊息)
  - **Discovered**: 2026-04-22 during 2.8 Round 2B Test 4 E2E

- **[P2]** No backend PostHog client (`api/` has no `import posthog`)
  - **現況**: All PostHog events flow through `utils/analytics.ts` `track()` from the frontend. Server-side events (e.g. PRD §4.5 需求 7 `share_link_visited`, which fires when LinkedIn/X/Facebook bots scrape OG cards) cannot be captured.
  - **Risk for §4.5**: `share_link_visited` was specced as backend-fired with `referrer_domain` + `is_first_view`. Per 2026-05-05 PRD §4.5 修訂, this event is being moved to frontend (accepts that bot views are not counted — arguably correct behavior, view_count remains accurate via server increment).
  - **Resolution if needed later**: Add `posthog` to requirements.txt + module-level `Posthog(api_key, host=...)` in `api/server.py` + helper for server-side `track()`. ~10 lines. Required only if a future feature needs server-side analytics that frontend cannot emit.
  - **Priority**: P2 — current §4.5 design absorbs this gap; no other open need. (TECH_DEBT.md has no P3 tier; lowest is P2.)
  - **Discovered**: 2026-05-05 during §4.5 PHASE A smoke test (PostHog server-side fire was specced but no client existed).

- **[P2]** ShareButton anonymous gating uses redirect, not in-context AnonymousUpgradeCTA modal
  - **現況**: `components/ShareButton.tsx` for anonymous users routes to `/sign-up` via `router.push` instead of opening `components/AnonymousUpgradeCTA.tsx` modal in-place. PRD §4.5 修訂 1 specced "AnonymousUpgradeCTA 風格" prompt; PHASE B chose redirect to keep scope narrow.
  - **Conversion impact**: redirect breaks the user's high-intent moment ("I just got an answer, I want to share") by yanking them off the current page. Modal pattern (per ADR 001 / commit 24b1d79) preserves context. Anonymous → registered conversion rate from share-locked trigger is likely lower than from other triggers (`third_query`, etc.) for this reason. Magnitude unknown until data comes in.
  - **PostHog attribution preserved**: `share_modal_opened` fires with `gated:true, gate_reason:'anonymous'` so the funnel is measurable.
  - **Resolution**: extend AnonymousUpgradeCTA with a new `trigger='share_locked'` value (~5-10 LOC). Update ShareButton to render `<AnonymousUpgradeCTA trigger='share_locked' onClose={...} />` instead of `router.push('/sign-up')`. Re-test 8k flow.
  - **Priority**: P2 — measurable conversion cost, but not blocking §4.5 ship. Pick up when GTM data shows share-locked → signup conversion underperforming other triggers, OR opportunistically during Phase 1B Anonymous Trial Flow polish (per STATE.md Phase 1B Week 7 work item).
  - **Discovered**: 2026-05-06 during §4.5 PHASE B implementation; deviation accepted by reviewer to avoid widening PHASE B scope.
  - **2026-05-06 update**: Resolution scope unchanged but now applies to BOTH `variant='inline'` (history.tsx) and `variant='navbar'` (research/verify/explain pages, commit ca571ce). When implemented, fix in one place propagates to both call sites since both share the same anon-gating code path inside `components/ShareButton.tsx`.

- **[P2 → Dodo 付費啟用前]** `CLERK_SECRET_KEY` 仍是 `sk_live_` 對 Dev instance user checkout 會 500
  - **現況**: Round 2B JWT Dev/Prod mismatch fix 只改 `CLERK_JWKS_URL` 指向 Dev instance (`joint-guppy-23.clerk.accounts.dev`);`CLERK_SECRET_KEY` 仍為 Prod `sk_live_NhG...`
  - **影響範圍**: Dodo checkout path 會用 `CLERK_SECRET_KEY` call Clerk Backend API 取 user email/name;Dev instance user ID 對 Prod secret key 查不到 → 500 error
  - **現行不爆的原因**: Round 2B 測試只跑 Research + Verify,沒動到 Dodo checkout;Dodo 付費要到 Phase 1A 才啟用
  - **解法** (Dodo 付費啟用前):
    - 改用 Dev instance secret key(`sk_test_...`)for localhost + Dev user 測試
    - 或將 Prod env 與 Dev env 的 Clerk 設定徹底分離(`fly secrets` vs `.env`)
    - 驗證 `/api/checkout/dodo` + `/api/webhook/dodo` 路徑對 Dev user 能順利 create subscription
  - **Priority**: P2(不 block 當前軟啟動;Dodo 付費啟用是 Phase 1A scope)
  - **Discovered**: 2026-04-22 during 2.8 Round 2B Test 5 Clerk JWT Dev/Prod mismatch fix

- **[P2]** Native-speaker review pending for §4.5 share i18n legal-weighted strings
  - **現況**: `utils/i18n-share.ts` ships 16-locale ShareTranslations (commit b378659). en + zh-TW user-reviewed for legal precision; ja user-reviewed PASS during PHASE B live test. Other 12 locales (zh-CN, ko, es, fr, de, it, pt, th, ar, hi, bn, he, vi) are machine-translation baseline.
  - **Risk**: legal-weighted strings — `modalConsentCheckbox` (consent attestation list of identifiers + irrevocability clause), `publicDisclaimer` (visitor-facing AI medical disclaimer), `publicShortDisclaimer`, `settingsRevokeConfirm` — translation accuracy in those 12 locales unverified. Specific identifier list (病患姓名/身分證字號/病歷號/健保號) and "無法完全收回" clause must survive translation in any language Share is opened to.
  - **Resolution**: native-speaker review of the 4 legal-weighted keys × 12 unreviewed locales (= 48 strings). Trigger: before opening Share to non-en/zh-TW/ja traffic in production. Reviewer can pre-launch focus on Vela target locales (likely ja already done; ko + es + th worth prioritizing for SE Asia GTM).
  - **Priority**: P2 — gates non-en/zh-TW/ja Share traffic; not blocking en/zh-TW soft launch.
  - **Discovered**: 2026-05-06 during §4.5 UX polish 2.5 i18n rollout.

- **[P2]** /terms + /privacy pages are en-only — i18n retrofit pending
  - **現況**: pages/terms.tsx + pages/privacy.tsx are hardcoded English JSX with no i18n infrastructure (no useLang(), no per-locale dict, no markdown content). Both predate the §4.5 share i18n 16-locale rollout (commit b378659). 17 sections total (9 Terms + 8 Privacy) are en-only despite the rest of the product being 16-locale.
  - **Risk**: legal compliance — non-en/zh-TW users see the entire ToS + Privacy Policy in English regardless of their UI locale, which weakens consent validity in jurisdictions requiring local-language disclosure (notably zh-TW, ja, ko per Vela's Tier 1 GTM target). Discovered 2026-05-08 during §4.5 PHASE D when Share clauses were added en-only to match existing pattern.
  - **Resolution**: dedicated commit to refactor /terms + /privacy to 16-locale i18n. Approximately 238 legal-weighted strings (17 sections × 14 added locales). Translation should be reviewed by qualified legal translator per locale, NOT machine-translation baseline (this is a hard commitment to users, unlike share i18n strings which are UI labels). Native-speaker review process should align with existing P2 entry "Native-speaker review pending for share i18n legal-weighted strings".
  - **Priority**: P2 — gates non-en production traffic at scale (Tier 1 GTM expansion to JP/KR/ID/VN/PH would require this). Not blocking soft launch in en + zh-TW markets if both legal pages have at least zh-TW translation by then. Consider doing zh-TW first as a Phase 1A gate (since zh-TW is Vela's home market), then ja + ko before Phase 1B Tier 1 expansion.
  - **Discovered**: 2026-05-08 during §4.5 PHASE D recon (commit 6f7a154 follow-up).

- **[P3]** scripts/cost_report_7d.py untracked file
  - **現況**: `git status` consistently shows `scripts/cost_report_7d.py` as untracked across multiple §4.5 commits (PHASE B onward). Out of §4.5 scope; not committed nor gitignored.
  - **Risk**: minor — untracked file accumulates noise in `git status`. Could be ops tooling, dead exploration, or pending feature.
  - **Resolution**: at Phase 0 Retrospective, decide one of: (a) commit if it's wanted ops tooling, (b) `.gitignore` if it's dev-only artifact, (c) delete if dead.
  - **Priority**: P3 — quality-of-life only.
  - **Discovered**: 2026-05-05 during §4.5 PHASE B; persisted through subsequent commits.

- **[P3]** Backend dotenv loader doesn't read .env.local
  - **現況**: FastAPI backend reads `.env` but NOT `.env.local`. During §4.5 PHASE B local dev, user set `VELA_PUBLIC_BASE_URL=http://localhost:3000` in `.env.local` (Next.js convention) but backend continued falling back to production URL hardcoded default. User had to set `$env:VELA_PUBLIC_BASE_URL` via PowerShell process env to override.
  - **Risk**: dev quality-of-life paper cut. Easy to accidentally generate share URLs pointing to production from localhost. (Did happen once during this work — user spent 30min debugging "share URL goes to production landing page" before identifying the env-loading mismatch.)
  - **Resolution**: pick one — (a) extend backend dotenv loader to chain `.env.local` before `.env` (matches Next.js convention; least surprise); (b) document in `.env.example` that backend-side vars (`VELA_PUBLIC_BASE_URL`, `SHARE_CREATED_BY_SALT`) belong in `.env`, not `.env.local`. (a) is preferred for symmetry.
  - **Related backend latent bug**: `VELA_PUBLIC_BASE_URL` fallback when unset defaults to production URL. Should fall back to `http://localhost:3000` if `TEST_MODE=true` and not set. Bundle the fix with (a).
  - **Priority**: P3 — dev-only.
  - **Discovered**: 2026-05-06 during §4.5 PHASE B smoke test 8l.

- **[P3]** components/Untitled stale backup file
  - **現況**: `components/Untitled` is a tracked file containing an old copy of CitationPanel.tsx with the StarRating component still defined and referenced. Discovered 2026-05-08 during Commit 211d9f7 (5-star UI removal) — the active CitationPanel.tsx was cleaned but the Untitled backup still has the dead code.
  - **Risk**: minor — stale backup files clutter codebase grep results and risk being mistaken for the active component. No runtime impact (file is not imported by any active code).
  - **Resolution**: at Phase 0 Retrospective, delete `components/Untitled` (or rename to `.bak` and gitignore). Verify it's truly orphaned via `git grep "Untitled" -- '*.tsx' '*.ts'` first.
  - **Priority**: P3 — codebase hygiene.
  - **Discovered**: 2026-05-08 during dogfooding star-removal commit.

- **[P2 → Phase 0 production deploy checklist]** `/explore/category/:category` dev rewrites gap
  - **現況**: §4.6 PHASE D shipped category listing pages at `/explore/category/:category` (commit a8361f5). The Next.js static export rewrites work in production via Fly.io / CDN, but `npm run dev` does not rewrite `/explore/category/foo` → the category listing page. During PHASE D live test, navigation from breadcrumb category link 404'd on localhost.
  - **影響範圍**: dev-only — production unaffected (static export + edge rewrites resolve correctly). Affects local dogfooding + future development of Explore category UI.
  - **Resolution**: ~15 min followup commit — add `rewrites()` config in `next.config.js` (or equivalent middleware) so `/explore/category/:category` resolves to the static page in dev. Gate on Phase 0 production deploy checklist so dev + prod parity is verified before soft launch.
  - **Priority**: P2 — not blocking production ship; blocks local dogfooding of category listing UI.
  - **Discovered**: 2026-05-13 during §4.6 PHASE D live test (PHASE D dogfooding).

- **[P2 → Phase 0 production deploy checklist]** CLI sync overwrites DB status with markdown status, silently un-publishing pages
  - **現況**: `scripts/explore_cli.py` (PHASE C, commit 0f139d2) sync command reads the `status:` frontmatter from each markdown file and writes it to the `explore_page.status` DB column. If a markdown file was created with `status: draft` and the DB row was later flipped to `published` (via direct SQL or admin UI), the next CLI sync silently overwrites `published` → `draft`, un-publishing the page without warning.
  - **影響範圍**: caused live test case (a) FAIL during PHASE D dogfooding — `/explore/metformin-contraindications-renal` returned 404 until the markdown `status:` was bumped to `published` and re-synced. Could silently break published pages in production if CLI is run after a manual DB status change.
  - **3 candidate fixes** (decide at Phase 0 deploy checkpoint):
    1. **Markdown-as-source-of-truth (current behavior, make explicit)**: keep current logic but log a WARNING when CLI flips a DB `published` → `draft`. Force a `--force-unpublish` flag to actually demote. Safest if content workflow is "markdown is authoritative".
    2. **DB-as-source-of-truth for status**: CLI never writes `status` column; only writes content fields. Status is managed via separate admin UI / SQL. Requires admin tooling.
    3. **Two-way merge**: CLI writes markdown `status` only if DB row is missing OR DB `status='draft'`. Never demote `published` → `draft` via CLI. Compromise — keeps markdown as primary source for new content while preventing silent unpublish.
  - **Resolution**: pick one of the 3 fixes at Phase 0 production deploy checkpoint, before any production content is published via CLI. Recommendation: fix #3 (two-way merge, no demote) is least surprising and requires no new tooling.
  - **Priority**: P2 — silent data corruption potential; not blocking ship but must resolve before production content sync.
  - **Discovered**: 2026-05-13 during §4.6 PHASE D live test case (a) FAIL diagnosis.

- **[P2 → Phase 0 production deploy checklist]** Locale fallback — Accept-Language non-en/zh-TW returns 404 on /explore pages
  - **現況**: §4.6 PHASE B sitemap-explore.xml hreflang logic skips missing locales (commit 8fb10ca). Explore pages exist in en + zh-TW only at PHASE D ship. When a user (or SEO crawler) hits `/explore/<slug>` with `Accept-Language: ja` / `ko` / `es` / etc., the server returns 404 instead of falling back to en (or zh-TW for zh-* variants).
  - **影響範圍**: production blocker for SEO crawler discovery in non-Tier-1 locales. Google / Bing crawlers identifying as non-en locales (e.g. Googlebot-Mobile crawling from JP region) would see 404 and drop the page from index. Also blocks human users from non-Tier-1 locales reading existing en content while translations are pending.
  - **Resolution**: at Phase 0 production deploy checklist — implement locale fallback chain. Recommended order: requested locale → en (universal fallback). For zh-* variants: zh-CN → zh-TW → en. Implement in the Next.js `/explore/[slug]` page resolver or middleware. Verify with Google Rich Results Test (PHASE E acceptance) hitting from multiple Accept-Language headers.
  - **Priority**: P2 — production SEO blocker for non-Tier-1 locales; must resolve before soft launch if non-en/zh-TW indexing is desired.
  - **Discovered**: 2026-05-13 during §4.6 PHASE D live test (Accept-Language testing).

- **[P3]** `api/providers/factory.py` creates a new Provider instance on every `get_xxx_provider()` call
  - **現況**: Each call to `get_generator_provider()` / `get_lightweight_provider()` / `get_embedder_provider()` etc. instantiates a fresh `OpenAIProvider` / `GroqProvider` (which constructs a new `AsyncOpenAI` httpx client). Acceptable for current call frequency — most call sites cache the binding at module load or class `__init__` (e.g. `VectorStore.__init__`).
  - **Risk**: minor — if any hot path repeatedly calls a factory (e.g. inside a per-request loop), HTTP client churn could hurt latency. No such hot path exists today.
  - **Resolution**: at Phase 0 Retrospective or next opportunity, consider `functools.lru_cache` on factory functions, or module-level singletons keyed by `(provider_name, model)`. Validate via profiling before optimizing.
  - **Priority**: P3 — quality-of-life / future maintenance.
  - **Discovered**: 2026-05-13 during §2.1 PHASE B (wiring 3 Low files to Provider abstraction).

- **[P2 → Phase 1A §3.1] Clerk publicMetadata.plan dormant dual-source vs user_usage.plan_type — discovered 2026-05-19 pre-deploy audit**
  - **背景**: Frontend `_app.tsx` PostHog identify() reads `publicMetadata.plan` and forwards as person property. Backend gating uses `user_usage.plan_type` exclusively. Manual Clerk Dashboard inspection of the only real Pro user (user_3BN1HkLU7kw7458c351oqMVwmv9, Andrew personal) confirmed `publicMetadata.plan` has never been written. TypeScript signature suggests alternative source-of-truth that doesn't exist in practice.
  - **影響範圍**: No active drift today (publicMetadata.plan reads `undefined` → fallback path). Risk surfaces if any external system (Clerk Dashboard rule, future webhook, manual admin action) writes `publicMetadata.plan` without coordinating with user_usage. Then frontend identify() and backend gate disagree on plan_type, silently. PostHog person properties become unreliable for plan-segmented analytics.
  - **Resolution**: Phase 1A §3.1 audit decision G4 already taken: user_usage.plan_type is authoritative; drop publicMetadata.plan read path from `_app.tsx::identify()`. Concrete change: remove `plan` property from `publicMetadata` TypeScript signature in `types/clerk.ts` (or equivalent); update `_app.tsx::identify()` to source plan_type from backend `/api/user/usage` instead.
  - **驗證方法**: After fix, verify `_app.tsx` no longer references `publicMetadata.plan`; PostHog identify event includes `plan_type` from backend response.
  - **Discovered**: 2026-05-19 pre-deploy DB state audit (3 Pro users in user_usage: 1 real + 1 orphan-now-cleaned + 1 TEST_MODE marker; orphan row had `dodo_customer_id = test_cust_*` Dodo sandbox leftover, cleaned same session)

- **[P2 → Phase 1A §3.1] Clerk user.deleted webhook → user_usage cleanup not wired — discovered 2026-05-19**
  - **背景**: user_3B939OrkarbJWpfTT8nCi9kDJ1B was deleted from Clerk Dashboard at unknown earlier date but user_usage row persisted with plan_type='pro'. No automatic sync between Clerk user.deleted webhook and user_usage table. Manually cleaned 2026-05-19 via psycopg2 transaction; full backup preserved in docs/retrospectives/phase-0-2026-05.md § 1.2.
  - **影響範圍**: Low for current production scale (1 known orphan row in 2 months). Risk compounds over time + after soft launch: deleted users leave dangling user_usage rows skewing plan_type distribution analytics, holding stale Dodo customer references, no path for Right-to-Erasure GDPR compliance.
  - **Resolution**: Phase 1A §3.1 scope. Wire Clerk webhook `user.deleted` event to a new handler in `api/server.py` that performs (soft-delete vs hard-delete decision TBD during §3.1 work) on the user_usage row. Decision tradeoff: hard-delete simpler but loses analytics history; soft-delete (e.g. `deleted_at` timestamp column) preserves history but adds complexity to all queries.
  - **驗證方法**: After implementation, test in dev by deleting a test Clerk user, verify user_usage row updated/removed per chosen strategy. Add idempotency: webhook may fire multiple times; handler must be safe under repeated invocation.
  - **Discovered**: 2026-05-19 pre-deploy DB state audit; related to G4 publicMetadata.plan entry above (both are user lifecycle governance issues; consider folding into a single user lifecycle ADR during §3.1 design)

- **[P3 → opportunistic] deploy.ps1 hardcoded 10-second settle insufficient for vector store cold start — discovered 2026-05-19**
  - **背景**: `deploy.ps1` Step 2 sleeps 10 seconds after `fly deploy` exit before running Step 3 machine status check. But vector store load (FAISS + 690 documents) takes 30-60 seconds on cold machine boot. Manual workaround during 2026-05-19 deploy: insert additional 60-second sleep before running PART B.3 smoke curls.
  - **影響範圍**: Low operational. Affects deploy day operator experience only — if operator runs PART B smoke immediately after deploy.ps1 exit, vector store may still be loading and queries silently return 0 results until ready. Confusing but not user-facing.
  - **Resolution**: Two options. (A) Parameterize settle time via env var (e.g. `DEPLOY_SETTLE_SEC=60`). (B) Replace fixed sleep with poll loop hitting `/health` or `/api/status` until 200, timeout after N seconds. Option B is correct long-term but adds complexity; Option A is 3 LoC.
  - **Discovered**: 2026-05-19 production deploy day, observed during PART B verification

- **[P3 → opportunistic] Raw SQL migration introspection missing — no schema_versions table — discovered 2026-05-19**
  - **背景**: Production Neon migrations are applied manually via `psql -f migrations/00X.sql`. Pre-deploy audit verified migrations 002-005 applied via table-presence inference (e.g. `shared_query` table exists → 004 applied), NOT via a versioning table. No `alembic_version` table exists (project doesn't use alembic); no equivalent introspection mechanism.
  - **影響範圍**: Currently fine while migration count is low (5 migrations total). Fragile as migration count grows: "what's applied" inferred from side-effects, easy to lose track during a multi-day deploy or rollback scenario. Phase 1A §3.1 introduces migration 006 (user_profile) — natural point to add lightweight introspection.
  - **Resolution**: Add a minimal `schema_versions(filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT NOW())` table in a new migration (could bundle with 006). Update existing `migrations/00X.sql` files to `INSERT INTO schema_versions (filename) VALUES ('00X_name.sql') ON CONFLICT DO NOTHING;` at end. Backfill 002-005 entries manually in production. Eliminates "is X migration applied" guesswork forever.
  - **Discovered**: 2026-05-19 pre-deploy state audit (Claude Code investigation found no alembic_version table and inferred migration state from public schema table list)

- **[P3 → Phase 1B Week 4] Research response missing canonical clinical terms — 4 WARN pattern (2026-05-19 golden run)**
  - **背景**: 2026-05-19 golden eval 4 個 WARN 中 3 個(R03/R09/R20)為 Research response 漏掉 canonical clinical 元素:
    - R03: AFib anticoagulation indications 沒提 CHA2DS2-VASc(THE stroke risk scoring tool)
    - R09: Lithium therapy monitoring 沒提 thyroid function(standard protocol — 30% 引起 subclinical hypothyroidism per literature)
    - R20: ACE-I in pregnancy 沒提 safer alternatives(methyldopa / labetalol — physician 自然 follow-up question after "contraindicated")
  - **第 4 個 WARN(E26)**: empty_input error 路徑正確(blocked = ✅),wording 觸發 fuzzy must_contain miss,unrelated 議題,low priority
  - **Pattern**: Research generator / RAG retrieval 可能對「canonical scoring tools」「standard monitoring protocols」「alternative drug recommendations」有 systematic under-coverage。3/3 Research WARN 都是 "missing canonical term" 而非 hallucination / fabrication / off-topic — pattern 一致。
  - **Hypothesis**:
    - (a) RAG retrieval 偏向 high-citation general papers,specialty-specific scoring tool papers ranking 較低 — retrieval-side gap
    - (b) Generator prompt 沒明確要求「contraindicated → suggest alternatives」/「monitoring → list all canonical parameters」logical chain — prompt-side gap
    - (c) Token limit 截斷 detail — output-length gap (less likely given other detail present)
  - **影響範圍**: Medium for clinical user trust. Physicians expect canonical terms (CHA2DS2-VASc, MELD, BISAP, INR target ranges, etc.) — their absence reads as "incomplete answer" even if the medical content is correct.
  - **Resolution**: Phase 1B Week 4 Verify 強制英文 + system prompt polish window,順手 evaluate Research prompt 是否需要 reinforcement on canonical terms。Candidate intervention: Research system prompt 加一段「if answer involves treatment decision, always mention canonical scoring tools (e.g. CHA2DS2-VASc for AFib, MELD for liver), standard monitoring protocols (e.g. thyroid for lithium, INR for warfarin), or alternative drugs when stating contraindication」.
  - **驗證方法**: Phase 1B Week 4 fix 後重跑 R03 / R09 / R20,目標全 PASS (min_score ≥ 70). 如果還 WARN 表示 root cause 是 retrieval 不是 prompt,需要 deeper RAG eval (Hypothesis a).
  - **Related**: Synergy with TECH_DEBT entry "Verify 答案品質 nuance issues — dogfooding 發現 (2026-05-06)" Task A which also addresses Verify/Research system prompt polish in Week 4. Both can share the same work session.
  - **Discovered**: 2026-05-19 post-deploy golden eval run (96.7% overall pass rate, 4 WARN, 0 FAIL — no regression)

- **[P2 → Phase 2 candidate] chat-history privacy model — docs were stale + behavior is "honest but not maximal"**
  - **Discovered**: 2026-05-25 during blog llms.txt fact-check (the public-facing privacy claim audit that preceded /llms.txt copy).
  - **Background — actual shipped behavior**: L0 anonymous queries are not tied to any account / not written to ChatHistory. L1 (signed-in free, "Vela for Work") + L2 Pro both write to ChatHistory on every successful Research / Verify / Explain request. Universal 180-day retention via `_cleanup_old_records` at `api/server.py:179–197`. No per-tier distinction. No `history_enabled` opt-in toggle exists anywhere (verified via repo-wide grep `history_enabled|enable_history|store_history` → 0 hits; no DB column on user_usage or user_profile; no Settings UI; no frontend flag).
  - **Public surface (pages/privacy.tsx) is HONEST and matches code**: §1 "Anonymized and sanitized query content"; §2 "We do not store PHI" (PHI gate at request boundary enforces); §4 "up to 6 months ... automatically deleted" (matches 180-day cleanup exactly). No public over-claim.
  - **Stale internal-PRD claims now reconciled in this commit (docs/PRD.md §6.4 + §2.8)**: §6.4 line 2111 previously said "chat_history 僅 Pro 使用者明確開啟時" (false — never implemented). §6.4 line 2115 previously said "絕不儲存:查詢原始文字(Free 使用者)" (false — L1 free queries DO write to ChatHistory; Research sanitizes-for-log first, Verify stores drug-names-only, Explain stores `report_text[:500]` after PHI gate). §2.8 line 716 previously said "7 天 history" for L1 (ambiguous — was display scope, not retention). All three reconciled with this commit's PRD edits.
  - **Why this is P2 not P0/P1**: the public-facing claims are accurate. No user was promised a thing the code doesn't deliver. No regulatory exposure, no privacy fraud. The drift was internal-doc-only.
  - **Two follow-up considerations for Phase 2 (candidates, NOT bugs)**:
    - **(a) "Anonymized" wording precision**: pages/privacy.tsx §1 uses "Anonymized and sanitized query content". ChatHistory rows do carry the Clerk `user_id` string — so strictly this is **pseudonymized** (re-identifiable with the auth provider's records), not **anonymized** (irreversibly de-linked). Defensible under most privacy regimes but worth a legal-wording review before any compliance audit (e.g. GDPR Article 4 distinguishes the two). Cheap fix if needed: change "Anonymized" → "Pseudonymized" or rephrase.
    - **(b) Stronger privacy model fits the brand**: Vela's positioning is Privacy-first (§0.3) and the landing card explicitly says "NO ACCOUNT NEEDED". For a Privacy-first product, a stronger chat-history model (free tier not stored at all, or shorter retention + Pro-only opt-in toggle) would better live up to positioning. This is a candidate feature — only worth building if there's market/regulatory pull. Implementation surface: new `history_enabled` column on user_profile, Settings UI toggle, write-site gates at the 5 ChatHistory locations in api/server.py (697, 898, 938, 1024, 1128), per-tier `_cleanup_old_records` retention logic.
  - **Resolution target**: Phase 2 candidate (neither blocks anything today). If pursued: change scope ~1d for option (a) wording-only, ~3-4d for option (b) opt-in feature + retention-per-tier.
  - **Reference**: investigation chat session 2026-05-25 (preserved verbatim); public privacy.tsx §1-§4; docs/PRD.md §6.4 + §2.8 reconciled lines.
