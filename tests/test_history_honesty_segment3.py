# -*- coding: utf-8 -*-
"""HISTORY HONESTY car segment 3 — frontend carry-across wiring (Rule 19 / Rule 17).

THE BUSINESS RULES (what breaks if each test fails):

1. The Research trust signal (FallbackBanner / ProvenanceLine) must be ONE shared
   component consumed by /research AND /history. Two page-local copies drift
   silently — the fly-214 class: a mitigation written for surface #1 never
   reaches surface #2 (CLAUDE.md Rule 19).
2. The ProvenanceLine tooltip must be legible in BOTH colour schemes (baton
   §3.6 item 4: `bg-white … text-gray-600` was light-only).
3. /history must render the caveat from the PERSISTED flag: a fallback row shows
   the banner, a grounded row with citations shows the provenance line, and an
   UNKNOWN row (pre-segment-2, no key) shows NEITHER — absence is never rendered
   as grounded (TECH_DEBT `[HONESTY][P2]` /history fallback indication).
4. The /history mode badge must be localized through the EXISTING nav keys
   (`navResearch` / `navVerify` / `navExplain`), not an English literal map.
5. `research_completed` must NOT fire after an SSE `error` (`research_failed`
   already did) — analytics honesty (baton §3.6 item 3).
6. The Verify AI-severity note (the v199 honest-relabel, BACKLOG [P1]
   fake-authority close condition) must SURVIVE the icon+tooltip redesign on
   the shared card: present as tooltip text AND as the icon's accessible name,
   reachable by hover, keyboard focus AND tap — and the card must still be the
   one both /verify and /history render.

⚠️ SCOPE, STATED HONESTLY (the test_research_answer_scroll.py idiom): these are
SOURCE assertions with comments stripped. The BEHAVIOURAL half — the decision
helper executed against fixtures and the shared components actually rendered
through react-dom/server — lives in tests/history_render_fallback_guard.mjs §4,
run inside the pytest count by tests/test_history_render_fallback.py.
"""
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_RESEARCH = _ROOT / "pages" / "research.tsx"
_HISTORY = _ROOT / "pages" / "history.tsx"
_VERIFY = _ROOT / "pages" / "verify.tsx"
_TRUST = _ROOT / "components" / "ResearchTrustSignal.tsx"
_CARD = _ROOT / "components" / "VerifyInteractionCard.tsx"


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def _src(path: Path) -> str:
    assert path.exists(), f"{path.relative_to(_ROOT)} is missing"
    return _strip_comments(path.read_text(encoding="utf-8"))


# ── 1. One shared component, two consumers ──────────────────────────────────

def test_trust_signal_components_are_shared_not_page_local():
    """Rule 19: research.tsx must IMPORT the two components from components/
    and no longer define them locally; history.tsx imports the same module."""
    research = _src(_RESEARCH)
    history = _src(_HISTORY)
    trust = _src(_TRUST)
    assert not re.search(r"function\s+ProvenanceLine\s*\(", research), (
        "pages/research.tsx still defines ProvenanceLine locally — a second copy "
        "on /history would drift from it"
    )
    assert not re.search(r"function\s+FallbackBanner\s*\(", research), (
        "pages/research.tsx still defines FallbackBanner locally"
    )
    imp = r"import\s*\{[^}]*\bFallbackBanner\b[^}]*\}\s*from\s*'\.\./components/ResearchTrustSignal'"
    assert re.search(imp, research) and "ProvenanceLine" in re.search(imp, research).group(0), (
        "pages/research.tsx does not import { FallbackBanner, ProvenanceLine } from "
        "../components/ResearchTrustSignal"
    )
    assert re.search(imp, history) and "ProvenanceLine" in re.search(imp, history).group(0), (
        "pages/history.tsx does not import { FallbackBanner, ProvenanceLine } from "
        "../components/ResearchTrustSignal"
    )
    assert re.search(r"export\s+function\s+ProvenanceLine\s*\(", trust)
    assert re.search(r"export\s+function\s+FallbackBanner\s*\(", trust)


def test_shared_components_take_lang_as_a_prop_not_a_hook():
    """VerifyInteractionCard precedent: the shared component receives `lang`
    and calls getUI(lang); a hook inside it would couple the render guard (and
    any non-page consumer) to LangContext."""
    trust = _src(_TRUST)
    assert "useLang" not in trust, "components/ResearchTrustSignal.tsx calls useLang() — pass lang as a prop"
    assert re.search(r"lang\s*:\s*LangCode", trust), "the shared components do not declare a `lang: LangCode` prop"
    assert re.search(r"getUI\(lang\)", trust), "the shared components do not resolve strings via getUI(lang)"
    research = _src(_RESEARCH)
    assert re.search(r"<FallbackBanner\s+lang=\{lang\}\s*/>", research), (
        "/research no longer passes lang to <FallbackBanner/>"
    )
    assert re.search(r"<ProvenanceLine\s+citations=\{citations\}\s+lang=\{lang\}\s*/>", research), (
        "/research no longer passes citations + lang to <ProvenanceLine/>"
    )


def test_research_render_site_keeps_the_loading_guard_and_mutual_exclusivity():
    """The /research render rule is unchanged by the extraction: !loading gate,
    fallback wins, provenance only with ≥1 citation, else null."""
    research = _src(_RESEARCH)
    assert re.search(
        r"\{!loading\s*&&\s*\(isFallback\s*\?\s*<FallbackBanner\s+lang=\{lang\}\s*/>\s*:\s*"
        r"citations\.length\s*>\s*0\s*\?\s*<ProvenanceLine\s+citations=\{citations\}\s+lang=\{lang\}\s*/>\s*:\s*null\)\}",
        research,
    ), "the /research trust-signal render rule changed shape during the extraction"


# ── 2. Tooltip theme tokens (§3.6 item 4) ───────────────────────────────────

def test_provenance_tooltip_uses_theme_tokens_not_light_only_classes():
    trust = _src(_TRUST)
    assert "bg-white" not in trust, "ProvenanceLine tooltip still uses bg-white (light-only)"
    assert not re.search(r"text-gray-\d", trust), "ProvenanceLine tooltip still uses text-gray-* (light-only)"
    assert "--color-paper-2" in trust and "--color-card-border" in trust, (
        "the tooltip surface/border are not theme tokens (--color-paper-2 / --color-card-border)"
    )


# ── 3. /history renders the caveat from the persisted flag ──────────────────

def test_history_renders_trust_signal_from_the_persisted_flag():
    history = _src(_HISTORY)
    assert re.search(r"function\s+researchTrustSignal\s*\(", history), (
        "the researchTrustSignal decision helper is gone — the .mjs guard extracts it verbatim"
    )
    assert re.search(r"<FallbackBanner\s+lang=\{lang\}\s*/>", history), "/history never renders <FallbackBanner/>"
    assert re.search(r"<ProvenanceLine\s+citations=\{researchParsed\.citations\}\s+lang=\{lang\}\s*/>", history), (
        "/history never renders <ProvenanceLine/> from the stored citation list"
    )
    # The decision is keyed on the strict boolean, never on truthiness of the key.
    assert re.search(r"fallback\s*===\s*true", history), "the banner branch is not keyed on fallback === true"
    assert re.search(r"fallback\s*===\s*false", history), "the provenance branch is not keyed on fallback === false"


# ── 4. Badge i18n through the existing nav keys ─────────────────────────────

def test_history_badge_is_localized_through_existing_nav_keys():
    history = _src(_HISTORY)
    assert not re.search(r"research\s*:\s*'Research'", history), (
        "pages/history.tsx still carries the English FEATURE_LABELS literal map"
    )
    for key in ("navResearch", "navVerify", "navExplain"):
        assert re.search(r"\.%s\b" % key, history), f"/history badge does not read extra.{key}"


# ── 5. research_completed not on error ──────────────────────────────────────

def test_research_completed_is_guarded_by_the_errored_flag():
    research = _src(_RESEARCH)
    assert re.search(r"let\s+errored\s*=\s*false", research), "no client-local `errored` flag in runSearch"
    err_block = re.search(r"data\.type\s*===\s*'error'\)\s*\{(.*?)\n\s*\}\s*\n\s*else\s+if\s*\(data\.type\s*===\s*'done'", research, re.S)
    assert err_block, "the SSE error → done handler pair changed shape"
    assert re.search(r"errored\s*=\s*true", err_block.group(1)), "the SSE `error` handler does not set errored = true"
    assert re.search(r"if\s*\(\s*!errored\s*\)\s*\{?\s*track\('research_completed'", research), (
        "track('research_completed') is not guarded by `if (!errored)`"
    )


# ── 6. Verify ⓘ icon + tooltip keeps the honest relabel ─────────────────────

def test_ai_severity_note_survives_as_icon_tooltip_on_the_shared_card():
    card = _src(_CARD)
    assert "getAiSeverityNote(lang)" in card, "the AI-severity note is no longer read on the shared card"
    assert "ⓘ" in card, "the ⓘ marker is gone from the shared card"
    assert re.search(r"aria-label=\{note\}", card), "the icon has no aria-label carrying the note"
    assert re.search(r"title=\{note\}", card), "the icon has no title carrying the note"
    assert re.search(r"role=\"tooltip\"[^>]*>\s*\{note\}", card, re.S) or re.search(r"\{note\}\s*</span>", card), (
        "the note text is not rendered inside the tooltip element"
    )
    # hover + keyboard focus + tap
    assert "group-hover:block" in card, "tooltip does not open on hover"
    assert "group-focus-within:block" in card, "tooltip does not open on keyboard focus (Tab)"
    assert re.search(r"onClick=\{", card) and "useState" in card, (
        "tooltip has no tap/click toggle — a hover-only tooltip vanishes on phones"
    )
    # The SAME tokenised tooltip surface as ProvenanceLine — literally shared, not copied.
    assert re.search(r"import\s*\{[^}]*\bTOOLTIP_STYLE\b[^}]*\}\s*from\s*'\./ResearchTrustSignal'", card), (
        "the card tooltip does not import TOOLTIP_STYLE from ./ResearchTrustSignal"
    )
    assert re.search(r"style=\{TOOLTIP_STYLE\}", card), "the card tooltip does not apply TOOLTIP_STYLE"
    assert re.search(r"export\s+const\s+TOOLTIP_STYLE\b", _src(_TRUST)), "TOOLTIP_STYLE is not exported by the shared component file"
    # Both consumers still render the shared card.
    assert re.search(r"<VerifyInteractionCard\b", _src(_VERIFY)), "/verify no longer renders VerifyInteractionCard"
    assert re.search(r"<VerifyInteractionCard\b", _src(_HISTORY)), "/history no longer renders VerifyInteractionCard"


# ── Negative controls — the patterns reject plausible wrong versions ────────

def test_the_guards_actually_fire():
    assert "ProvenanceLine" not in _strip_comments("// function ProvenanceLine( in prose\n")
    assert not re.search(r"<FallbackBanner\s+lang=\{lang\}\s*/>", "<FallbackBanner />")
    assert not re.search(r"if\s*\(\s*!errored\s*\)\s*\{?\s*track\('research_completed'",
                         "track('research_completed', {")
    assert not re.search(r"aria-label=\{note\}", 'title={getAiSeverityNote(lang)}')
    assert re.search(r"\.navResearch\b", "extra.navResearch") and not re.search(r"\.navResearch\b", "navResearch:")
