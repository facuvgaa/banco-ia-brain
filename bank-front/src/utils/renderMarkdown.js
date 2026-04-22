import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({
  gfm: true,
  breaks: true,
})

/**
 * Convierte Markdown (negrita, tablas, listas…) a HTML seguro.
 * El chat antes usaba `{{ text }}` → el navegador mostraba literal ** y pipes de tablas.
 */
export function renderMarkdown(raw) {
  if (raw == null || String(raw).trim() === '') return ''
  const html = marked.parse(String(raw), { async: false })
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
}
