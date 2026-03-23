<script setup>
import { ref, onMounted } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const textoGasto = ref('')
const cargandoProceso = ref(false)
const cargandoGuardado = ref(false)
const errorMensaje = ref('')
const exitoMensaje = ref('')
const gastoExtraido = ref(null)
const tablaGastos = ref([])
const chartData = ref({
  labels: [],
  datasets: [{
    backgroundColor: ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'],
    data: []
  }]
})
const chartOptions = ref({
  responsive: true,
  maintainAspectRatio: false
})

const cargarEstadisticas = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/estadisticas')
    if (res.ok) {
      const data = await res.json()
      chartData.value = {
        labels: data.map(d => d.categoria),
        datasets: [{
          backgroundColor: ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'],
          data: data.map(d => d.total)
        }]
      }
    }
  } catch (error) {
    console.error('Error cargando estadísticas:', error)
  }
}

const cargarGastos = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/gastos')
    if (res.ok) {
      tablaGastos.value = await res.json()
    }
  } catch (error) {
    console.error('Error cargando historial:', error)
  }
}

const procesarGasto = async () => {
  if (!textoGasto.value.trim()) {
    errorMensaje.value = "Por favor, escribe un gasto primero."
    return
  }
  
  errorMensaje.value = ''
  exitoMensaje.value = ''
  cargandoProceso.value = true
  gastoExtraido.value = null

  try {
    const res = await fetch('http://localhost:5000/api/procesar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: textoGasto.value })
    })

    const data = await res.json()

    if (!res.ok) {
        throw new Error(data.error || data.detalle || 'Error procesando el gasto con la Inteligencia Artificial.')
    }

    gastoExtraido.value = {
      monto: data.monto || 0,
      comercio: data.comercio || '',
      categoria: data.categoria || '',
      fecha: data.fecha || new Date().toISOString().split('T')[0],
      moneda: data.moneda || 'EUR',
      texto_original: textoGasto.value
    }

  } catch (err) {
    errorMensaje.value = err.message
  } finally {
    cargandoProceso.value = false
  }
}

const guardarGasto = async () => {
  errorMensaje.value = ''
  cargandoGuardado.value = true

  try {
    const res = await fetch('http://localhost:5000/api/gastos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(gastoExtraido.value)
    })

    const data = await res.json()

    if (!res.ok) {
      throw new Error(data.error || 'Error al guardar el gasto')
    }

    exitoMensaje.value = "¡Gasto guardado exitosamente!"
    gastoExtraido.value = null
    textoGasto.value = ''
    
    await cargarGastos()
    await cargarEstadisticas()

  } catch (err) {
    errorMensaje.value = err.message
  } finally {
    cargandoGuardado.value = false
  }
}

onMounted(() => {
  cargarGastos()
  cargarEstadisticas()
})
</script>

<template>
  <div class="app-wrapper">
    <div class="app-container">
      
      <!-- Header -->
      <header class="app-header">
        <h1 class="app-title">
          GastoGenie <span>🧞‍♂️</span>
        </h1>
        <p class="app-subtitle">Tu Smart Expense Tracker</p>
      </header>

      <!-- Mensajes Globales -->
      <div v-if="errorMensaje" class="alert alert-error">
        <p class="alert-title">Error</p>
        <p>{{ errorMensaje }}</p>
        <button @click="errorMensaje=''" class="btn-close">&times;</button>
      </div>
      
      <div v-if="exitoMensaje" class="alert alert-success">
        <p class="alert-title">¡Éxito!</p>
        <p>{{ exitoMensaje }}</p>
        <button @click="exitoMensaje=''" class="btn-close">&times;</button>
      </div>

      <!-- Zona de Entrada (Natural Language) -->
      <section class="glass-card">
        <label for="textoGasto" class="input-label">
          ¿En qué gastaste hoy? Cuéntamelo de forma natural:
        </label>
        <div class="textarea-wrapper">
          <textarea
            id="textoGasto"
            v-model="textoGasto"
            class="natural-input"
            placeholder="Ej. Ayer me gasté 35 euros cenando pizza con mis amigos en Ginos..."
            :disabled="cargandoProceso"
            @keydown.enter.ctrl="procesarGasto"
          ></textarea>
          <div class="keyboard-hint">Ctrl + Enter para enviar</div>
        </div>
        <div class="btn-container">
          <button
            @click="procesarGasto"
            :disabled="cargandoProceso || !textoGasto.trim()"
            class="btn btn-primary"
          >
            <span v-if="cargandoProceso" class="spinner"></span>
            <span v-else>✨</span>
            {{ cargandoProceso ? 'Generando Magia...' : 'Procesar Gasto' }}
          </button>
        </div>
      </section>

      <!-- Formulario de Corrección / Confirmación -->
      <section v-if="gastoExtraido" class="glass-card confirmation-section">
        <h2 class="confirmation-header">
          <span>🧐</span> Revisa y confirma los datos
        </h2>
        
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Monto</label>
            <div class="form-input-wrapper">
              <input type="number" step="0.01" v-model="gastoExtraido.monto" class="form-input" />
              <div class="currency-badge">{{ gastoExtraido.moneda }}</div>
            </div>
          </div>
          
          <div class="form-group">
            <label class="form-label">Comercio</label>
            <input type="text" v-model="gastoExtraido.comercio" class="form-input" />
          </div>
          
          <div class="form-group">
            <label class="form-label">Fecha</label>
            <input type="date" v-model="gastoExtraido.fecha" class="form-input" />
          </div>
          
          <div class="form-group">
            <label class="form-label">Categoría</label>
            <input type="text" v-model="gastoExtraido.categoria" class="form-input" />
          </div>
        </div>
        
        <div class="btn-container">
          <button @click="gastoExtraido = null" class="btn btn-outline">
            Cancelar / Reescribir
          </button>
          <button 
            @click="guardarGasto" 
            :disabled="cargandoGuardado"
            class="btn btn-success"
          >
            <span v-if="cargandoGuardado" class="spinner"></span>
            <span v-else>💾</span>
            {{ cargandoGuardado ? 'Guardando...' : 'Confirmar y Guardar' }}
          </button>
        </div>
      </section>

      <!-- Dashboard y Tabla de Gastos -->
      <section class="glass-card">
        <div class="history-header">
          <h2 class="history-title">Dashboard & Historial</h2>
          <span class="badge">{{ tablaGastos.length }} registros</span>
        </div>
        
        <div class="dashboard-wrapper" v-if="chartData.labels.length > 0" style="height: 300px; margin-bottom: 2rem; position: relative;">
          <Doughnut :data="chartData" :options="chartOptions" />
        </div>

        <div class="table-responsive">
          <table class="gastos-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Comercio</th>
                <th>Categoría</th>
                <th class="text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="gasto in tablaGastos" :key="gasto.id">
                <td class="col-date">{{ gasto.fecha }}</td>
                <td class="col-comercio">{{ gasto.comercio }}</td>
                <td><span class="category-tag">{{ gasto.categoria }}</span></td>
                <td class="col-total">
                  <span class="total-amount">{{ gasto.monto.toFixed(2) }}</span>
                  <span class="total-currency">{{ gasto.moneda }}</span>
                </td>
              </tr>
              <tr v-if="tablaGastos.length === 0">
                <td colspan="4">
                  <div class="empty-state">
                    <span class="empty-icon">📭</span>
                    <p class="empty-title">Aún no hay gastos registrados.</p>
                    <p class="empty-subtitle">¡Añade tu primer gasto usando GastoGenie!</p>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

    </div>
  </div>
</template>