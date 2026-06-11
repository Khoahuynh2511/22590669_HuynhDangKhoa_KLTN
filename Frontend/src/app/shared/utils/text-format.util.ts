export function normalizeLineBreaks(text: string): string {
  return text
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n/g, '\n')
    .replace(/\\r/g, '\n')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/<br\s*\/?>/gi, '\n');
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function stripDescriptionNoise(text: string): string {
  return text
    .replace(/-{10,}o0o0o0o0o-{10,}/gi, '')
    .replace(/-{5,}[o0o0o0o0o]+-{5,}/gi, '')
    .replace(/[-]{10,}/g, '')
    .replace(/\*{3}(.*?)\*{3}/gs, '$1')
    .replace(/\*{2,}/g, '')
    .replace(/\*(?=\S)/g, '')
    .trim();
}

export function formatDescriptionHtml(text: string): string {
  if (!text) {
    return '';
  }

  let formatted = stripDescriptionNoise(normalizeLineBreaks(text));
  formatted = escapeHtml(formatted);

  formatted = formatted.replace(/Ngày \d+:/g, '<strong class="day-header">$&</strong>');
  formatted = formatted.replace(/Quý khách/g, '<span class="highlight-text">Quý khách</span>');

  const paragraphs = formatted
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter((block) => block.length > 0);

  if (paragraphs.length === 0) {
    return '';
  }

  return paragraphs
    .map((block) => {
      if (block.startsWith('<strong class="day-header">')) {
        return `<div class="desc-day-block">${block.replace(/\n/g, '<br>')}</div>`;
      }

      if (block.includes('***') || block.startsWith('Lưu ý') || block.startsWith('Ghi chú')) {
        return `<div class="note-box">${block.replace(/\n/g, '<br>')}</div>`;
      }

      return `<p>${block.replace(/\n/g, '<br>')}</p>`;
    })
    .join('');
}

export interface DescriptionDayBlock {
  day: string;
  content: string;
}

export function splitDescriptionByDays(text: string): DescriptionDayBlock[] {
  if (!text) {
    return [];
  }

  const normalized = stripDescriptionNoise(normalizeLineBreaks(text));
  const dayPattern = /Ngày \d+:/g;
  const markers = [...normalized.matchAll(dayPattern)];

  if (markers.length === 0) {
    return [{ day: '', content: normalized }];
  }

  const days: DescriptionDayBlock[] = [];

  for (let i = 0; i < markers.length; i += 1) {
    const start = markers[i].index ?? 0;
    const end = i < markers.length - 1 ? (markers[i + 1].index ?? normalized.length) : normalized.length;
    const section = normalized.substring(start, end).trim();
    const titleEnd = section.indexOf('\n');
    const day = titleEnd >= 0 ? section.substring(0, titleEnd).trim() : section;
    const content = titleEnd >= 0 ? section.substring(titleEnd + 1).trim() : '';

    days.push({ day, content });
  }

  return days;
}

export function truncateDescription(text: string, maxLength: number): string {
  const normalized = stripDescriptionNoise(normalizeLineBreaks(text));

  if (normalized.length <= maxLength) {
    return normalized;
  }

  const truncated = normalized.substring(0, maxLength);
  const lastBreak = Math.max(
    truncated.lastIndexOf('\n\n'),
    truncated.lastIndexOf('\n'),
    truncated.lastIndexOf('. ')
  );

  if (lastBreak > maxLength * 0.6) {
    return `${truncated.substring(0, lastBreak).trim()}...`;
  }

  const lastSpace = truncated.lastIndexOf(' ');
  if (lastSpace > maxLength * 0.75) {
    return `${truncated.substring(0, lastSpace).trim()}...`;
  }

  return `${truncated.trim()}...`;
}
