<script setup>
import { ref } from 'vue'

const textoChat = ref('')
const respuestaChat = ref('')
const cargandoChat = ref(false)

const props = defineProps({
  backendUrl: {
    type: String,
    default: 'http://localhost:5000'
  }
})

const hacerPreguntaChat = async (pregunta) => {
  const p = typeof pregunta === 'string' ? pregunta : textoChat.value
  if (!p.trim()) return

  if (typeof pregunta === 'string') {
    textoChat.value = p
  }
  
  cargandoChat.value = true
  respuestaChat.value = ''
  
  try {
    const res = await fetch(`${props.backendUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pregunta: p })
    })

    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error en el chat')
    
    respuestaChat.value = data.respuesta
  } catch (error) {
    console.error('Error chat:', error)
    respuestaChat.value = 'Hubo un error al consultar a GastoGenie. Inténtalo de nuevo.'
  } finally {
    cargandoChat.value = false
    textoChat.value = ''
  }
}
</script>

<template>
  <section class="glass-card p-6">
    <!-- Asistente Financiero (Chat) -->
    <div class="flex items-center gap-4 mb-6">
      <div class="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center text-2xl shadow-sm">🧞‍♂️</div>
      <div>
        <h2 class="text-xl font-bold text-slate-900 leading-tight">Genie Insights</h2>
        <p class="text-xs uppercase tracking-wider text-slate-500 font-semibold">Asistente Virtual</p>
      </div>
    </div>
    
    <div class="flex gap-2 flex-wrap mb-6">
      <button @click="hacerPreguntaChat('¿Cuánto gasté en comida este mes?')" 
        class="text-xs px-4 py-2 rounded-full border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm active:scale-95 disabled:opacity-50" 
        :disabled="cargandoChat">
        ¿Cuánto gasté en comida?
      </button>
      <button @click="hacerPreguntaChat('Dame un consejo para ahorrar')" 
        class="text-xs px-4 py-2 rounded-full border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm active:scale-95 disabled:opacity-50" 
        :disabled="cargandoChat">
        Consejo para ahorrar
      </button>
    </div>

    <div class="relative flex items-center bg-slate-50 rounded-2xl border border-slate-100 p-1.5 focus-within:ring-2 focus-within:ring-indigo-500/10 focus-within:border-indigo-200 transition-all">
      <input type="text" v-model="textoChat" @keydown.enter="hacerPreguntaChat()" 
        placeholder="Pregunta algo..." 
        class="flex-1 bg-transparent border-none outline-none px-4 text-slate-700 placeholder:text-slate-400" 
        :disabled="cargandoChat" />
      <button @click="hacerPreguntaChat()" 
        class="bg-indigo-600 text-white w-10 h-10 rounded-xl flex items-center justify-center hover:bg-indigo-700 transition-all shadow-md shadow-indigo-200 disabled:opacity-50" 
        :disabled="cargandoChat || !textoChat.trim()">
        <span v-if="cargandoChat" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
        <span v-else>🚀</span>
      </button>
    </div>

    <div v-if="respuestaChat" class="mt-6 animate-slide-up">
      <div class="p-5 bg-gradient-to-br from-indigo-50/50 to-white border border-indigo-100 rounded-2xl relative overflow-hidden">
        <div class="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
        <div class="text-[0.95rem] text-slate-700 leading-relaxed space-y-2" v-html="respuestaChat.replace(/\*\*(.*?)\*\*/g, '<strong class=\'text-indigo-900 font-bold\'>$1</strong>')"></div>
      </div>
    </div>
  </section>
</template>
