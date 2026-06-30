import { marked } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'

// Configure marked with syntax highlighting
marked.setOptions({
  gfm: true,
  breaks: true,
})

const renderer = new marked.Renderer()

// Code blocks with copy button and syntax highlighting
renderer.code = (code: string, language?: string) => {
  const lang = language || 'text'
  let highlighted = code
  try {
    if (hljs.getLanguage(lang)) {
      highlighted = hljs.highlight(code, { language: lang }).value
    } else {
      highlighted = hljs.highlightAuto(code).value
    }
  } catch { /* use raw */ }

  const escapedCode = code.replace(/`/g, '\\`').replace(/\${/g, '\\${')
  return `
    <div class="code-block" style="position:relative">
      <button class="code-copy-btn" onclick="(function(btn){
        navigator.clipboard.writeText(\`${escapedCode}\`).then(()=>{
          btn.textContent='Copied!';setTimeout(()=>btn.textContent='Copy',2000);
        });
      })(this)">Copy</button>
      <pre><code class="hljs language-${lang}">${highlighted}</code></pre>
    </div>
  `
}

// Inline code
renderer.codespan = (code: string) => {
  return `<code>${code}</code>`
}

marked.use({ renderer })

export function renderMarkdown(content: string): string {
  if (!content) return ''
  const raw = marked.parse(content) as string
  return DOMPurify.sanitize(raw, {
    ADD_TAGS: ['pre', 'code', 'button'],
    ADD_ATTR: ['onclick', 'class', 'style'],
    ALLOW_DATA_ATTR: false,
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel|data|media):|[^&:\/?#]*(?:[\/?#]|$))/i,
  })
}

export function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
