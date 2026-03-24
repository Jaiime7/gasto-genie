<script setup>
import { ref } from 'vue'

const props = defineProps({
  backendUrl: {
    type: String,
    default: 'http://localhost:5000'
  }
})

const emit = defineEmits(['onSaved'])

const entradaNatural = ref('')
const cargandoProcesamiento = ref(false)
const gastoConfirmar = ref(null)
const tipoRegistro = ref('gasto') // 'gasto' o 'ingreso'

const procesarTexto = async () => {
    if (!entradaNatural.value.trim()) return
    cargandoProcesamiento.value = true
    try {
      const res = await fetch(`${props.backendUrl}/api/procesar_natural`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: entradaNatural.value })
      })
      const data = await res.json()
      if (res.ok) {
        gastoConfirmar.value = data
        // Determinar automáticamente si es ingreso o gasto basado en palabras clave (opcional)
        if (entradaNatural.value.toLowerCase().includes('nómina') || entradaNatural.value.toLowerCase().includes('ingreso')) {
          tipoRegistro.value = 'ingreso'
        } else {
          tipoRegistro.value = 'gasto'
        }
      }
    } catch (e) {
      console.error('Error:', e)
    } finally {
      cargandoProcesamiento.value = false
    }
}

const guardarGasto = async () => {
  if (!gastoConfirmar.value) return
  
  const endpoint = tipoRegistro.value === 'ingreso' ? '/api/ingresos' : '/api/gastos'
  const payload = tipoRegistro.value === 'ingreso' 
    ? {
        fuente: gastoConfirmar.value.comercio, // Usamos el comercio como fuente
        monto: gastoConfirmar.value.monto,
        fecha: gastoConfirmar.value.fecha || new Date().toISOString().split('T')[0]
      }
    : gastoConfirmar.value

  try {
    const res = await fetch(`${props.backendUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (res.ok) {
      entradaNatural.value = ''
      gastoConfirmar.value = null
      emit('onSaved')
    }
  } catch (e) {
    console.error('Error:', e)
  }
}

const manejarArchivoEnForm = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  const formData = new FormData()
  formData.append('file', file)
  
  cargandoProcesamiento.value = true
  try {
    const res = await fetch(`${props.backendUrl}/api/escanear_recibo`, {
      method: 'POST',
      body: formData
    })
    const data = await res.json()
    if (res.ok) {
        gastoConfirmar.value = data
        tipoRegistro.value = 'gasto'
    }
  } catch (e) {
    console.error('Error escaneo:', e)
  } finally {
    cargandoProcesamiento.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Entrada Natural: "The Magic Bar" -->
    <section class="glass-card p-6 border-indigo-100 bg-indigo-50/10">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-lg shadow-indigo-100">✨</div>
        <div>
          <h2 class="text-lg font-bold text-slate-800">Entrada Inteligente</h2>
          <p class="text-[10px] uppercase font-bold tracking-widest text-indigo-500">NLP & Vision</p>
        </div>
      </div>
      
      <div class="relative group">
        <textarea 
          v-model="entradaNatural" 
          @keydown.enter.prevent="procesarTexto" 
          placeholder="Ej: Ayer gasté 15e en Starbucks..." 
          class="w-full bg-white border border-slate-200 rounded-3xl p-6 pb-12 text-lg text-slate-700 placeholder:text-slate-300 outline-none focus:ring-4 focus:ring-indigo-500/5 focus:border-indigo-300 transition-all min-h-[140px] resize-none shadow-sm"
          :disabled="cargandoProcesamiento"
        ></textarea>
        
        <div class="absolute bottom-4 right-4 flex items-center gap-3">
          <label class="cursor-pointer group/label">
            <input type="file" class="hidden" @change="manejarArchivoEnForm" accept="image/*,application/pdf" />
            <div class="w-10 h-10 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 group-hover/label:bg-indigo-50 group-hover/label:text-indigo-600 group-hover/label:border-indigo-100 transition-all active:scale-95 shadow-sm">
              📎
            </div>
          </label>
          
          <button @click="procesarTexto" 
            class="h-10 px-6 bg-indigo-600 text-white rounded-full font-bold text-sm shadow-md shadow-indigo-100 hover:bg-indigo-700 transition-all active:scale-95 flex items-center gap-2"
            :disabled="cargandoProcesamiento || !entradaNatural.trim()">
            <span v-if="cargandoProcesamiento" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <span v-else>Procesar</span>
          </button>
        </div>
      </div>
      <p class="mt-3 text-[11px] text-slate-400 font-medium text-center italic">Presiona Enter para procesar automáticamente</p>
    </section>

    <!-- Confirmación Step: Elegant Card -->
    <div v-if="gastoConfirmar" class="animate-slide-up">
      <section class="glass-card p-6 border-indigo-200 bg-white shadow-xl">
        <div class="flex items-center justify-between mb-6">
            <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
                Verificar Datos
            </h3>
            <div class="flex bg-slate-100 p-1 rounded-full border border-slate-200">
                <button @click="tipoRegistro = 'gasto'" 
                    class="px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all"
                    :class="tipoRegistro === 'gasto' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'">Gasto</button>
                <button @click="tipoRegistro = 'ingreso'" 
                    class="px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all"
                    :class="tipoRegistro === 'ingreso' ? 'bg-white text-emerald-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'">Ingreso</button>
            </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="text-[10px] uppercase font-bold tracking-widest text-slate-400">Concepto</label>
            <input type="text" v-model="gastoConfirmar.comercio" class="form-input bg-slate-50 border-transparent focus:bg-white text-sm" />
          </div>
          <div class="space-y-1">
            <label class="text-[10px] uppercase font-bold tracking-widest text-slate-400">Monto (€)</label>
            <input type="number" step="0.01" v-model="gastoConfirmar.monto" class="form-input bg-slate-50 border-transparent focus:bg-white text-sm font-bold text-indigo-600" />
          </div>
          <div class="space-y-1">
            <label class="text-[10px] uppercase font-bold tracking-widest text-slate-400">Categoría</label>
            <input type="text" v-model="gastoConfirmar.categoria" class="form-input bg-slate-50 border-transparent focus:bg-white text-sm" />
          </div>
          <div class="space-y-1">
            <label class="text-[10px] uppercase font-bold tracking-widest text-slate-400">Fecha</label>
            <input type="date" v-model="gastoConfirmar.fecha" class="form-input bg-slate-50 border-transparent focus:bg-white text-sm" />
          </div>
        </div>

        <div class="flex gap-3 mt-8">
          <button @click="gastoConfirmar = null" class="flex-1 px-6 py-3 rounded-2xl border border-slate-200 text-slate-500 font-bold hover:bg-slate-50 transition-all text-sm uppercase tracking-wider">Cancelar</button>
          <button @click="guardarGasto" 
            class="flex-[2] px-6 py-3 rounded-2xl font-bold transition-all text-sm uppercase tracking-wider shadow-lg active:scale-[0.98]"
            :class="tipoRegistro === 'ingreso' ? 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-emerald-100' : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-indigo-100'"
          >Confirmar & Guardar</button>
        </div>
      </section>
    </div>
  </div>
</template>
