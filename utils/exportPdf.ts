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

function escapeHtml(s: string): string {
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export async function exportResearchPdf(question: string, answer: string, citations: Citation[]) {
    const date = new Date().toLocaleDateString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
    });

    const refsBlock = citations.length > 0
        ? citations.map((c, i) => formatCitation(c, i + 1)).join('\n\n')
        : 'No citations available.';

    const plainAnswer = stripMarkdown(answer);

    const element = document.createElement('div');
    element.innerHTML = `
<div style="font-family: Georgia, 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; color: #1a1a1a; max-width: 700px; margin: 0 auto;">
  <h1 style="font-size: 18pt; margin-bottom: 4pt;">Vela Research Report</h1>
  <div style="color: #666; font-size: 10pt; margin-bottom: 1.5rem;">Generated: ${date}</div>
  <div style="background: #f5f5f5; padding: 12px 16px; border-left: 3px solid #ff8e6e; margin-bottom: 1.5rem; font-style: italic;">${escapeHtml(question)}</div>
  <div style="white-space: pre-wrap; margin-bottom: 2rem;">${escapeHtml(plainAnswer)}</div>
  <h2 style="font-size: 14pt; border-bottom: 1px solid #ccc; padding-bottom: 4pt; margin-bottom: 1rem;">References</h2>
  <div style="font-size: 10pt; white-space: pre-wrap; line-height: 1.8;">${escapeHtml(refsBlock)}</div>
  <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; font-size: 9pt; color: #888;">
    Exported from Vela (vela.an-tho.com)<br>
    This report is generated from published medical literature.<br>
    Vela is a research tool, not a medical device. It does not provide medical advice.
  </div>
</div>`;

    try {
        const html2pdf = (await import('html2pdf.js')).default;
        await html2pdf()
            .set({
                margin: [15, 15, 15, 15],
                filename: `vela-research-${Date.now()}.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2 },
                jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
            })
            .from(element)
            .save();
    } catch {
        // Fallback: open in new window for print
        const w = window.open('', '_blank');
        if (!w) return;
        w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Vela Research Report</title></head><body>${element.innerHTML}</body></html>`);
        w.document.close();
        w.addEventListener('afterprint', () => w.close());
        setTimeout(() => w.print(), 300);
    }
}
