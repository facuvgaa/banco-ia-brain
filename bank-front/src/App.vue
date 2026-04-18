<script setup>
import { ref } from 'vue'
import ChatHeader from './components/ChatHeader.vue'
import axios from 'axios'

const isThinking = ref(false) 
const newMessage = ref('')

const messages = ref([
  { id: 1, text: "¡Hola perro! Sistema Moustro_Bank activo. ¿Qué consulta tenés?", sender: 'ai' }
])

const handleSendMessage = async () => {
  if (!newMessage.value.trim()) return

  const userText = newMessage.value
  messages.value.push({ id: Date.now(), text: userText, sender: 'user' })
  
  isThinking.value = true
  newMessage.value = ''

  try {
   
    const response = await axios.post('http://localhost:8080/api/chat', {
      prompt: userText
    })

    
    messages.value.push({
      id: Date.now(),
      text: response.data.reply, 
      sender: 'ai'
    })
  } catch (error) {
    
    console.error("Error conectando con el cluster:", error)
    messages.value.push({
      id: Date.now(),
      text: "Error de conexión. ¿Levantaste el backend de Java, facha?",
      sender: 'ai'
    })
  } finally {
    isThinking.value = false
  }
}
</script>

<template>
  <div class="neon-background flex flex-col h-screen font-sans selection:bg-emerald-500/30 overflow-hidden">
    
    <ChatHeader />

    <main class="flex-1 overflow-y-auto p-4 md:p-8 flex flex-col gap-6 relative z-10">
      
      <div v-for="msg in messages" :key="msg.id" 
           :class="['max-w-[85%] md:max-w-[70%] p-4 rounded-2xl shadow-xl transition-all', 
                    msg.sender === 'ai' 
                    ? 'bg-zinc-900/80 border border-zinc-800 self-start rounded-tl-none text-zinc-300' 
                    : 'bg-emerald-600 text-white self-end rounded-tr-none shadow-emerald-900/20']">
        <p v-if="msg.sender === 'ai'" class="text-[10px] text-emerald-400 font-black uppercase tracking-tighter mb-1">Moustro_Agent</p>
        <p class="text-sm leading-relaxed">{{ msg.text }}</p>
      </div>

      <div v-if="isThinking" class="self-start flex items-center gap-3 bg-zinc-900/30 p-3 rounded-xl border border-zinc-800/50">
        <div class="h-3 w-3 rounded-full bg-moustro-green"></div>
        <span class="text-[10px] font-mono text-zinc-500 uppercase tracking-widest italic">Esperando cluster...</span>
      </div>

    </main>

    <footer class="p-4 bg-zinc-900/50 border-t border-zinc-800 backdrop-blur-md relative z-10">
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
      <div class="mt-4 text-center text-zinc-600 text-[10px] font-mono">
        LOGGED AS: FACUVEGA | NODES_CONNECTED: 3
      </div>
    </footer>

  </div>
</template>