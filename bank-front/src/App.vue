<script setup>
import { onMounted, onUnmounted, ref, computed, watch, nextTick } from 'vue'
import ChatHeader from './components/ChatHeader.vue'
import { chatService, CHAT_USER_ID } from './services/api'
import { renderMarkdown } from './utils/renderMarkdown'

const pendingReplies = ref(0)
const newMessage = ref('')
/** Hasta no tener onopen, no hay WebSocket: mandar el chat puede “perder” la respuesta en Kafka. */
const wsReady = ref(false)
const wsError = ref(false)

const messages = ref([
  {
    id: 1,
    text: '¡Hola perro! Sistema Moustro_Bank activo. ¿Qué consulta tenés?',
    sender: 'ai',
    mdReady: true,
  },
])

const isThinking = computed(() => pendingReplies.value > 0)

const chatMainEl = ref(null)
const scrollChatToBottom = () => {
  nextTick(() => {
    requestAnimationFrame(() => {
      const el = chatMainEl.value
      if (!el) return
      el.scrollTop = el.scrollHeight
    })
  })
}
watch(
  () => [messages.value.length, pendingReplies.value, isThinking.value],
  () => scrollChatToBottom(),
  { flush: 'post' },
)

const streamBase = import.meta.env.VITE_API_URL.replace(/\/$/, '')

const buildWebSocketUrl = () => {
  const base = streamBase
  const ws = base
    .replace(/^https:\/\//i, 'wss://')
    .replace(/^http:\/\//i, 'ws://')
  return `${ws}/chat/ws?customerId=${encodeURIComponent(CHAT_USER_ID)}`
}

/** Si no baja a 0, el evento `reply` no llegó por WebSocket (o el pipeline no publicó a chat-response). */
const REPLY_TIMEOUT_MS = 120_000
let replyWaitTimer = null

const clearReplyWaitTimer = () => {
  if (replyWaitTimer != null) {
    clearTimeout(replyWaitTimer)
    replyWaitTimer = null
  }
}

const scheduleReplyWait = () => {
  clearReplyWaitTimer()
  replyWaitTimer = setTimeout(() => {
    replyWaitTimer = null
    if (pendingReplies.value <= 0) return
    pendingReplies.value = 0
    messages.value.push({
      id: Date.now(),
      text:
        'Timeout: no llegó respuesta por WebSocket. En F12 → Network, ¿la conexión a `api/chat/ws` termina en 101 Switching Protocols? ' +
        'En terminal: `docker logs moustro-classifier` y `docker logs core-service` (Kafka `chat-response`). ' +
        'Flujo: chat-queries → Bedrock+Redis → master/workflow → chat-response → tu navegador.',
      sender: 'ai',
      mdReady: true,
    })
  }, REPLY_TIMEOUT_MS)
}

const TYPEWRITER_MS = 14
let typewriterTimer = null
const clearTypewriter = () => {
  if (typewriterTimer != null) {
    clearTimeout(typewriterTimer)
    typewriterTimer = null
  }
}

const startTypewriter = (messageId, fullText) => {
  clearTypewriter()
  const run = (pos) => {
    const m = messages.value.find((x) => x.id === messageId)
    if (!m) return
    m.text = fullText.slice(0, pos)
    scrollChatToBottom()
    if (pos >= fullText.length) {
      m.mdReady = true
      m.streaming = false
      return
    }
    typewriterTimer = setTimeout(() => run(pos + 1), TYPEWRITER_MS)
  }
  run(1)
}

const handleSocketReply = (raw) => {
  let payload
  try {
    payload = JSON.parse(raw)
  } catch {
    return
  }
  if (payload.type !== 'reply') return
  if (pendingReplies.value > 0) pendingReplies.value--
  if (pendingReplies.value === 0) clearReplyWaitTimer()
  const text = payload.text == null ? '' : String(payload.text)
  const id = Date.now()
  messages.value.push({
    id,
    text: '',
    sender: 'ai',
    mdReady: false,
    streaming: true,
  })
  if (text.length === 0) {
    const m = messages.value.find((x) => x.id === id)
    if (m) {
      m.mdReady = true
      m.streaming = false
    }
    return
  }
  startTypewriter(id, text)
}

let socket = null
let unmounted = false

const connectWebSocket = () => {
  if (typeof WebSocket === 'undefined') {
    wsError.value = true
    return
  }
  const url = buildWebSocketUrl()
  try {
    socket = new WebSocket(url)
  } catch (e) {
    console.error('WebSocket', e)
    wsError.value = true
    return
  }
  socket.onopen = () => {
    if (unmounted) return
    wsError.value = false
    wsReady.value = true
  }
  socket.onmessage = (e) => {
    if (e.data == null) return
    handleSocketReply(e.data)
  }
  socket.onerror = () => {
    if (!unmounted) wsError.value = true
  }
  socket.onclose = () => {
    wsReady.value = false
  }
}

onMounted(() => {
  connectWebSocket()
  setTimeout(() => {
    if (!wsReady.value && !unmounted) {
      wsError.value = true
    }
  }, 12_000)
})

onUnmounted(() => {
  unmounted = true
  clearReplyWaitTimer()
  clearTypewriter()
  if (socket) {
    socket.close()
    socket = null
  }
})

const handleSendMessage = async () => {
  if (!newMessage.value.trim() || isThinking.value || !wsReady.value) return
  if (!socket || socket.readyState !== WebSocket.OPEN) return

  const userText = newMessage.value
  messages.value.push({ id: Date.now(), text: userText, sender: 'user' })
  newMessage.value = ''
  pendingReplies.value++

  try {
    await chatService.sendMessage(userText)
    scheduleReplyWait()
  } catch (error) {
    if (pendingReplies.value > 0) pendingReplies.value--
    clearReplyWaitTimer()
    console.error('Error conectando con el cluster:', error)
    messages.value.push({
      id: Date.now(),
      text: 'Error de conexión. ¿Levantaste el backend de Java, facha?',
      sender: 'ai',
      mdReady: true,
    })
  }
}
</script>

<template>
  <div
    class="neon-background flex h-dvh min-h-0 flex-col font-sans selection:bg-emerald-500/30 overflow-hidden"
  >
    <ChatHeader />

    <main class="flex min-h-0 flex-1 flex-col relative z-10">
      <div
        ref="chatMainEl"
        class="chat-scroll flex-1 min-h-0 touch-pan-y overflow-y-auto overflow-x-clip overscroll-y-contain p-4 md:p-8 [scrollbar-gutter:stable]"
      >
        <div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="[
              'shrink-0 w-full max-w-[min(100%,32rem)] p-4 rounded-2xl shadow-xl transition-shadow md:max-w-[min(100%,28rem)]',
              msg.sender === 'ai'
                ? 'self-start border border-zinc-800 bg-zinc-900/80 rounded-tl-none text-zinc-300'
                : 'self-end bg-emerald-600 text-white rounded-tr-none shadow-emerald-900/20',
            ]"
          >
            <p
              v-if="msg.sender === 'ai'"
              class="mb-1 text-[10px] font-black uppercase tracking-tighter text-emerald-400"
            >
              Moustro_Agent
            </p>
            <p
              v-if="msg.sender === 'user'"
              class="whitespace-pre-wrap text-sm leading-relaxed"
            >
              {{ msg.text }}
            </p>
            <template v-else>
              <p
                v-if="!msg.mdReady"
                class="ai-plain text-sm leading-relaxed whitespace-pre-wrap [overflow:visible] max-h-none"
              >
                {{ msg.text }}<span v-if="msg.streaming" class="ml-0.5 inline-block h-3 w-1 bg-emerald-500/80 align-[-0.1em] animate-pulse" />
              </p>
              <div
                v-else
                class="ai-md text-sm leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0 [overflow:visible] max-h-none"
                v-html="renderMarkdown(msg.text)"
              />
            </template>
          </div>

          <div
            v-if="isThinking"
            class="shrink-0 self-start flex items-center gap-3 rounded-xl border border-zinc-800/50 bg-zinc-900/30 p-3"
          >
            <div class="h-3 w-3 rounded-full bg-moustro-green"></div>
            <span
              class="text-[10px] font-mono uppercase tracking-widest italic text-zinc-500"
              >Pensando… (hasta 2 min: Bedrock + Redis + Kafka; la respuesta vuelve por WebSocket)</span
            >
          </div>
        </div>
      </div>
    </main>

    <footer class="shrink-0 border-t border-zinc-800 bg-zinc-900/50 p-4 backdrop-blur-md relative z-10">
      <div class="max-w-4xl mx-auto flex gap-3">
        <input 
          v-model="newMessage"
          @keyup.enter="handleSendMessage"
          type="text" 
          placeholder="Escribí un mensaje..." 
          class="flex-1 bg-zinc-950 border border-zinc-700 rounded-xl p-3 text-sm focus:outline-none focus:border-emerald-500 transition-all"
        />
        <button 
          @click="handleSendMessage"
          class="bg-moustro-green hover:bg-emerald-400 text-black p-3 rounded-xl transition-all active:scale-90 flex items-center justify-center shadow-[0_0_15px_rgba(0,255,153,0.3)]"
        >
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke-width="2.5" 
            stroke="currentColor" 
            class="w-5 h-5"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
          </svg>
        </button>
      </div>
      <p v-if="!wsReady && !wsError" class="mb-2 text-center text-amber-500/90 text-[10px] font-mono">
        Conectando WebSocket… esperá a enviar (si no conecta, el back no reenvía Kafka al navegador).
      </p>
      <p v-if="wsError" class="mb-2 text-center text-rose-400/90 text-[10px] font-mono">
        WebSocket: revisá <code class="px-0.5">http://localhost:8080</code> y CORS, o recargá la página.
      </p>
      <div class="mt-4 text-center text-zinc-600 text-[10px] font-mono">
        LOGGED AS: {{ CHAT_USER_ID }} | WS: {{ wsReady ? 'ok' : '—' }}
      </div>
    </footer>

  </div>
</template>

<style scoped>
.ai-plain {
  min-width: 0;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: anywhere;
}
/* Una sola barra vertical en .chat-scroll; burbujas sin scroll interno */
.ai-md {
  min-width: 0;
  max-width: 100%;
  overflow: visible;
  word-wrap: break-word;
  overflow-wrap: anywhere;
}
.ai-md :deep(strong) {
  font-weight: 700;
  color: rgb(250 250 250);
}
.ai-md :deep(em) {
  font-style: italic;
  color: rgb(212 212 216);
}
.ai-md :deep(a) {
  color: rgb(52 211 153);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.ai-md :deep(ul),
.ai-md :deep(ol) {
  margin: 0.5rem 0;
  padding-left: 1.25rem;
}
.ai-md :deep(li) {
  margin: 0.2rem 0;
}
.ai-md :deep(table) {
  table-layout: fixed;
  width: 100%;
  font-size: 0.8125rem;
  border-collapse: collapse;
  margin: 0.75rem 0;
  border: 1px solid rgb(63 63 70);
  border-radius: 0.5rem;
  overflow: hidden;
}
.ai-md :deep(th),
.ai-md :deep(td) {
  border: 1px solid rgb(63 63 70);
  padding: 0.4rem 0.55rem;
  text-align: left;
  vertical-align: top;
  word-break: break-word;
  hyphens: auto;
}
.ai-md :deep(th) {
  background: rgb(24 24 27 / 0.9);
  color: rgb(161 161 170);
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.ai-md :deep(tr:nth-child(even) td) {
  background: rgb(24 24 27 / 0.35);
}
.ai-md :deep(code) {
  font-size: 0.8em;
  padding: 0.1em 0.35em;
  border-radius: 0.25rem;
  background: rgb(9 9 11);
  border: 1px solid rgb(63 63 70);
}
.ai-md :deep(pre) {
  margin: 0.5rem 0;
  padding: 0.6rem 0.75rem;
  max-width: 100%;
  border-radius: 0.5rem;
  background: rgb(9 9 11);
  border: 1px solid rgb(63 63 70);
  overflow-x: auto;
  overflow-y: hidden;
  font-size: 0.7rem;
  white-space: pre-wrap;
  word-break: break-word;
}
.ai-md :deep(pre code) {
  border: none;
  padding: 0;
  background: transparent;
}
.ai-md :deep(blockquote) {
  margin: 0.5rem 0;
  padding-left: 0.75rem;
  border-left: 3px solid rgb(63 63 70);
  color: rgb(161 161 170);
}
</style>
