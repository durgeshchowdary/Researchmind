export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export function renderEvidenceHtml(value: string): string {
  return escapeHtml(value).replace(/\*\*(.*?)\*\*/g, '<mark class="evidence-mark">$1</mark>');
}

export function highlightTermsHtml(value: string, terms: string[]): string {
  const escaped = escapeHtml(value);
  const uniqueTerms = Array.from(new Set(terms.map((term) => term.trim()).filter(Boolean))).sort(
    (left, right) => right.length - left.length,
  );

  if (!uniqueTerms.length) {
    return escaped;
  }

  const pattern = new RegExp(`\\b(${uniqueTerms.map(escapeRegExp).join("|")})\\b`, "gi");
  return escaped.replace(pattern, '<mark class="evidence-mark">$1</mark>');
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
