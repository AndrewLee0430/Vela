import type { Citation } from '../components/CitationPanel';

function formatCitation(c: Citation, index: number): string {
    const parts: string[] = [];
    if (c.authors) parts.push(c.authors);
    if (c.title) parts.push(`"${c.title}."`);
    if (c.journal) parts.push(c.journal + '.');
    if (c.year) parts.push(c.year + '.');

    let line = `[${index}] ${parts.join(' ')}`;

    const ids: string[] = [];
    if (c.source_type === 'pubmed' && c.source_id) ids.push(`PMID: ${c.source_id}`);
    if (c.url) ids.push(c.url);
    if (ids.length) line += '\n    ' + ids.join(' | ');

    return line;
}

function stripMarkdown(md: string): string {
    return md
        .replace(/^#{1,6}\s+/gm, '')
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/\*(.*?)\*/g, '$1')
        .replace(/`(.*?)`/g, '$1')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/^[-*]\s+/gm, '  - ')
        .replace(/^>\s+/gm, '')
        .replace(/---+/g, '');
}

export function exportResearchPdf(question: string, answer: string, citations: Citation[]) {
    const date = new Date().toLocaleDateString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
    });

    const refsBlock = citations.length > 0
        ? citations.map((c, i) => formatCitation(c, i + 1)).join('\n\n')
        : 'No citations available.';

    const plainAnswer = stripMarkdown(answer);

    const html = `<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Vela Research Report</title>
<style>
  @page { margin: 2cm; }
  body { font-family: Georgia, "Times New Roman", serif; font-size: 12pt; line-height: 1.6; color: #1a1a1a; max-width: 700px; margin: 0 auto; padding: 2rem; }
  h1 { font-size: 18pt; margin-bottom: 4pt; }
  .meta { color: #666; font-size: 10pt; margin-bottom: 1.5rem; }
  .query { background: #f5f5f5; padding: 12px 16px; border-left: 3px solid #ff8e6e; margin-bottom: 1.5rem; font-style: italic; }
  .answer { white-space: pre-wrap; margin-bottom: 2rem; }
  .refs-title { font-size: 14pt; border-bottom: 1px solid #ccc; padding-bottom: 4pt; margin-bottom: 1rem; }
  .refs { font-size: 10pt; white-space: pre-wrap; line-height: 1.8; }
  .footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; font-size: 9pt; color: #888; }
</style>
</head><body>
<h1>Vela Research Report</h1>
<div class="meta">Generated: ${date}</div>
<div class="query">${escapeHtml(question)}</div>
<div class="answer">${escapeHtml(plainAnswer)}</div>
<h2 class="refs-title">References</h2>
<div class="refs">${escapeHtml(refsBlock)}</div>
<div class="footer">
Exported from Vela (vela.an-tho.com)<br>
This report is generated from published medical literature.<br>
Vela is a research tool, not a medical device. It does not provide medical advice.
</div>
</body></html>`;

    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(html);
    w.document.close();
    w.addEventListener('afterprint', () => w.close());
    // Small delay to let styles render before print dialog
    setTimeout(() => w.print(), 300);
}

function escapeHtml(s: string): string {
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
