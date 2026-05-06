# TECH_DEBT.md — Vela Pre-Existing Gaps & Polish Items

Active tech debt entries identified during shipping. Format preserved verbose because each entry is dense diagnosis context — compressing to a table loses why/how-to-apply specificity.

**Priority levels**:
- **[P0]** — blocks shipping or user-facing
- **[P1]** — affects code quality or upcoming task
- **[P2]** — best practice / future maintenance

**Resolution targets**:
- "→ Phase 0 Retrospective" — work in retro phase
- "→ Phase 1A polish" — work after Phase 0 ends
- "→ next opportunity" — when convenient

When entries are resolved, move to ARCHIVE.md (note discovery + resolution dates).

---

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
