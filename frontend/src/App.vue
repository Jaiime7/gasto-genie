<script setup>
import { ref, computed, onMounted } from 'vue'
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

const archivoSeleccionado = ref(null)
const vistaPreviaImagen = ref(null)
const esPdf = ref(false)
const imagenModal = ref(null)

const manejarArchivo = (event) => {
  const file = event.target.files[0]
  if (file) {
    archivoSeleccionado.value = file
    esPdf.value = file.type === 'application/pdf'
    
    if (esPdf.value) {
      vistaPreviaImagen.value = null
    } else {
      const reader = new FileReader()
      reader.onload = (e) => {
        vistaPreviaImagen.value = e.target.result
      }
      reader.readAsDataURL(file)
    }
  } else {
    archivoSeleccionado.value = null
    vistaPreviaImagen.value = null
    esPdf.value = false
  }
}

const modoPrivacidad = ref(false)
const filtroComercio = ref('')

const textoChat = ref('')
const respuestaChat = ref('')
const cargandoChat = ref(false)

// Estados para Planificación Integral
const ingresos = ref([])
const presupuestos = ref([])
const fijos = ref([])
const resumen = ref({ total_ingresos: 0, total_gastos: 0, total_gastos_fijos: 0, balance_final: 0, presupuesto_gastado_porcentaje: 0 })
const mostrarConfiguracion = ref(false)

const nuevoFijo = ref({ nombre: '', monto: 0, categoria: 'Hogar', pagado: false })
const nuevaNomina = ref({ fuente: 'Nómina', monto: 0, fecha: new Date().toISOString().split('T')[0] })
const nuevoPresupuesto = ref({ categoria: '', monto_limit: 0 })

// Estado para Edición
const mostrarModalEdicion = ref(false)
const editandoItem = ref(null)    // Copia editable del objeto
const editandoTipo = ref('')      // 'gasto' | 'ingreso' | 'presupuesto' | 'fijo'

const abrirEdicion = (item, tipo) => {
  editandoItem.value = { ...item }   // Copia superficial para no mutar el original
  editandoTipo.value = tipo
  mostrarModalEdicion.value = true
}

const cerrarEdicion = () => {
  mostrarModalEdicion.value = false
  editandoItem.value = null
  editandoTipo.value = ''
}

const actualizarItem = async () => {
  if (!editandoItem.value) return

  // Validación básica de montos
  if (editandoItem.value.monto !== undefined && parseFloat(editandoItem.value.monto) <= 0) {
    errorMensaje.value = 'El monto debe ser un número positivo.'
    return
  }
  if (editandoItem.value.monto_limite !== undefined && parseFloat(editandoItem.value.monto_limite) <= 0) {
    errorMensaje.value = 'El límite de presupuesto debe ser un número positivo.'
    return
  }

  const endpointMap = {
    gasto:       `/api/gastos/${editandoItem.value.id}`,
    ingreso:     `/api/ingresos/${editandoItem.value.id}`,
    presupuesto: `/api/presupuestos/${editandoItem.value.id}`,
    fijo:        `/api/fijos/${editandoItem.value.id}`,
  }
  const endpoint = `http://localhost:5000${endpointMap[editandoTipo.value]}`

  try {
    const res = await fetch(endpoint, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editandoItem.value)
    })
    const data = await res.json()
    if (!res.ok) {
      console.error('[actualizarItem] Error:', data)
      errorMensaje.value = data.error || 'Error al actualizar.'
      return
    }
    exitoMensaje.value = '✅ Registro actualizado correctamente.'
    cerrarEdicion()
    await cargarGastos()
    await cargarEstadisticas()
    await cargarPlanificacion()
  } catch (e) {
    console.error('[actualizarItem] Excepción:', e)
    errorMensaje.value = 'Error de conexión al actualizar.'
  }
}


const hacerPreguntaChat = async (pregunta) => {
  const p = typeof pregunta === 'string' ? pregunta : textoChat.value
  if (!p.trim()) return

  if (typeof pregunta === 'string') {
    textoChat.value = p
  }
  
  cargandoChat.value = true
  respuestaChat.value = ''
  
  try {
    const res = await fetch('http://localhost:5000/api/chat', {
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
const privacyStyle = computed(() => modoPrivacidad.value ? 'filter: blur(6px); transition: filter 0.3s;' : 'transition: filter 0.3s;')

const gastoTotal = computed(() => {
  return tablaGastos.value.reduce((total, gasto) => total + parseFloat(gasto.monto || 0), 0)
})

const gastoPromedio = computed(() => {
  return tablaGastos.value.length ? (gastoTotal.value / tablaGastos.value.length) : 0
})

const categoriaTop = computed(() => {
  if (tablaGastos.value.length === 0) return 'N/A'
  const counts = {}
  tablaGastos.value.forEach(g => {
    counts[g.categoria] = (counts[g.categoria] || 0) + parseFloat(g.monto || 0)
  })
  return Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b)
})

const tablaFiltrada = computed(() => {
  if (!filtroComercio.value) return tablaGastos.value
  const query = filtroComercio.value.toLowerCase()
  return tablaGastos.value.filter(g => g.comercio.toLowerCase().includes(query))
})

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

const verRecibo = (ruta) => {
  if (ruta.toLowerCase().endsWith('.pdf')) {
    window.open(`http://localhost:5000/uploads/${ruta}`, '_blank')
  } else {
    imagenModal.value = ruta
  }
}

const eliminarGasto = async (id) => {
  if (!confirm('¿Seguro que deseas eliminar este gasto?')) return

  try {
    const res = await fetch(`http://localhost:5000/api/gastos/${id}`, {
      method: 'DELETE'
    })

    if (res.ok) {
      await cargarGastos()
      await cargarEstadisticas()
      exitoMensaje.value = "¡Gasto eliminado correctamente!"
    } else {
      const data = await res.json()
      throw new Error(data.error || 'Error al eliminar el gasto')
    }
  } catch (error) {
    console.error('Error:', error)
    errorMensaje.value = error.message
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

const escanearRecibo = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  errorMensaje.value = ''
  exitoMensaje.value = ''
  cargandoProceso.value = true
  gastoExtraido.value = null

  try {
    const formData = new FormData()
    formData.append('recibo', file)

    const res = await fetch('http://localhost:5000/api/escanear', {
      method: 'POST',
      body: formData
    })

    const data = await res.json()

    if (!res.ok) {
        throw new Error(data.error || data.detalle || 'Error procesando el recibo con la IA.')
    }

    gastoExtraido.value = {
      monto: data.datos.monto || 0,
      comercio: data.datos.comercio || '',
      categoria: data.datos.categoria || '',
      fecha: data.datos.fecha || new Date().toISOString().split('T')[0],
      moneda: data.datos.moneda || 'EUR',
      texto_original: 'Extraído vía Escáner de Recibo.'
    }

    archivoSeleccionado.value = file
    esPdf.value = file.type === 'application/pdf'
    if (esPdf.value) {
      vistaPreviaImagen.value = null
    } else {
      const reader = new FileReader()
      reader.onload = (e) => {
        vistaPreviaImagen.value = e.target.result
      }
      reader.readAsDataURL(file)
    }
    
    exitoMensaje.value = '¡Recibo escaneado correctamente! Revisa los datos y confirma.'

  } catch (err) {
    errorMensaje.value = err.message
  } finally {
    cargandoProceso.value = false
    event.target.value = ''
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
    const formData = new FormData()
    formData.append('monto', gastoExtraido.value.monto)
    formData.append('comercio', gastoExtraido.value.comercio)
    formData.append('fecha', gastoExtraido.value.fecha)
    formData.append('categoria', gastoExtraido.value.categoria)
    formData.append('moneda', gastoExtraido.value.moneda || 'EUR')
    formData.append('texto_original', gastoExtraido.value.texto_original || '')
    
    if (archivoSeleccionado.value) {
      formData.append('recibo', archivoSeleccionado.value)
    }

    // Lógica para Ingresos (Nómina detectada por IA)
    const isIngreso = gastoExtraido.value.tipo_documento === 'ingreso' || gastoExtraido.value.categoria === 'Sueldo'
    const endpoint = isIngreso ? 'http://localhost:5000/api/ingresos' : 'http://localhost:5000/api/gastos'
    
    if (isIngreso) {
        formData.append('fuente', gastoExtraido.value.comercio)
        formData.append('es_nomina', 'true')
    }

    const res = await fetch(endpoint, {
      method: 'POST',
      body: formData
    })

    const data = await res.json()

    if (!res.ok) {
      throw new Error(data.error || 'Error al guardar')
    }

    exitoMensaje.value = isIngreso ? "Ingreso guardado exitosamente" : "¡Gasto guardado exitosamente!"
    gastoExtraido.value = null
    textoGasto.value = ''
    archivoSeleccionado.value = null
    vistaPreviaImagen.value = null
    esPdf.value = false
    
    await cargarGastos()
    await cargarPlanificacion()
    await cargarEstadisticas()

  } catch (err) {
    errorMensaje.value = err.message
  } finally {
    cargandoGuardado.value = false
  }
}

const getGastoPorCategoria = (cat) => {
  return tablaGastos.value
    .filter(g => g.categoria === cat)
    .reduce((acc, curr) => acc + (parseFloat(curr.monto) || 0), 0)
}

const cargarPlanificacion = async () => {
  try {
    const [resI, resP, resF, resSummary] = await Promise.all([
      fetch('http://localhost:5000/api/ingresos'),
      fetch('http://localhost:5000/api/presupuestos'),
      fetch('http://localhost:5000/api/fijos'),
      fetch('http://localhost:5000/api/resumen_financiero')
    ])
    const dataIngresos = await resI.json()
    const dataPres = await resP.json()
    const dataFijos = await resF.json()
    const dataSummary = await resSummary.json()

    if (Array.isArray(dataIngresos)) ingresos.value = dataIngresos
    else console.error('[cargarPlanificacion] Error ingresos:', dataIngresos)

    if (Array.isArray(dataPres)) presupuestos.value = dataPres
    else console.error('[cargarPlanificacion] Error presupuestos:', dataPres)

    if (Array.isArray(dataFijos)) fijos.value = dataFijos
    else console.error('[cargarPlanificacion] Error fijos:', dataFijos)

    if (dataSummary.balance_final !== undefined) resumen.value = dataSummary
    else console.error('[cargarPlanificacion] Error resumen:', dataSummary)
  } catch (e) {
    console.error('[cargarPlanificacion] Fallo general:', e)
  }
}

const guardarNomina = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/ingresos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nuevaNomina.value)
    })
    const data = await res.json()
    if (!res.ok) {
      console.error('[guardarNomina] Error del servidor:', data)
      errorMensaje.value = data.detalle || 'Error al guardar el ingreso.'
      return
    }
    exitoMensaje.value = `Ingreso guardado (ID: ${data.id})`
    await cargarPlanificacion()
    nuevaNomina.value = { fuente: 'Nómina', monto: 0, fecha: new Date().toISOString().split('T')[0] }
  } catch (e) {
    console.error('[guardarNomina] Excepción:', e)
    errorMensaje.value = 'Error de conexión al guardar el ingreso.'
  }
}

const guardarFijo = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/fijos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nuevoFijo.value)
    })
    const data = await res.json()
    if (!res.ok) {
      console.error('[guardarFijo] Error del servidor:', data)
      errorMensaje.value = data.detalle || 'Error al guardar el gasto fijo.'
      return
    }
    await cargarPlanificacion()
    nuevoFijo.value = { nombre: '', monto: 0, categoria: 'Hogar', pagado: false }
  } catch (e) {
    console.error('[guardarFijo] Excepción:', e)
    errorMensaje.value = 'Error de conexión al guardar el gasto fijo.'
  }
}

const eliminarFijo = async (id) => {
  try {
    const res = await fetch(`http://localhost:5000/api/fijos?id=${id}`, { method: 'DELETE' })
    if (!res.ok) {
      const data = await res.json()
      console.error('[eliminarFijo] Error del servidor:', data)
      return
    }
    await cargarPlanificacion()
  } catch (e) {
    console.error('[eliminarFijo] Excepción:', e)
  }
}

const guardarPresupuesto = async () => {
  const hoy = new Date()
  try {
    const res = await fetch('http://localhost:5000/api/presupuestos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        categoria: nuevoPresupuesto.value.categoria,
        monto_limite: nuevoPresupuesto.value.monto_limit,
        mes: hoy.getMonth() + 1,
        año: hoy.getFullYear()
      })
    })
    const data = await res.json()
    if (!res.ok) {
      console.error('[guardarPresupuesto] Error del servidor:', data)
      errorMensaje.value = data.detalle || 'Error al guardar el presupuesto.'
      return
    }
    await cargarPlanificacion()
    nuevoPresupuesto.value = { categoria: '', monto_limit: 0 }
  } catch (e) {
    console.error('[guardarPresupuesto] Excepción:', e)
    errorMensaje.value = 'Error de conexión al guardar el presupuesto.'
  }
}

onMounted(() => {
  cargarGastos()
  cargarEstadisticas()
  cargarPlanificacion()
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

      <div class="dashboard-grid">
        <!-- Sidebar: Control & AI -->
        <aside class="dashboard-sidebar">
          
          <!-- Configuración Mensual Toggle -->
          <button @click="mostrarConfiguracion = !mostrarConfiguracion" class="btn btn-outline" style="width: 100%; margin-bottom: 1rem; background: rgba(139, 92, 246, 0.1); border-color: var(--primary);">
            {{ mostrarConfiguracion ? '📉 Volver al Asistente' : '⚙️ Configuración del Mes' }}
          </button>

          <!-- Sección de Configuración -->
          <div v-if="mostrarConfiguracion" style="display: flex; flex-direction: column; gap: 1.5rem;">
            <!-- Nómina -->
            <section class="glass-card">
              <h3 style="font-size: 1rem; margin-bottom: 1rem;">💰 Nómina/Ingreso</h3>
              <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem;">
                <input type="number" v-model="nuevaNomina.monto" placeholder="Monto" class="form-input">
                <input type="text" v-model="nuevaNomina.fuente" placeholder="Fuente (ej. Nómina)" class="form-input">
                <input type="date" v-model="nuevaNomina.fecha" class="form-input">
                <button @click="guardarNomina" class="btn btn-primary btn-sm">Añadir Ingreso</button>
              </div>
              <!-- Lista de ingresos registrados -->
              <div v-if="ingresos.length > 0">
                <p style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Registrados</p>
                <div v-for="i in ingresos" :key="i.id" style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; padding: 0.5rem; background: rgba(16,185,129,0.07); border-radius: 6px; margin-bottom: 0.4rem; border-left: 3px solid var(--success);">
                  <div>
                    <span style="font-weight: 600;">{{ i.fuente }}</span>
                    <span :style="privacyStyle" style="margin-left: 0.5rem; color: var(--success);">+{{ i.monto }}€</span>
                  </div>
                  <button @click="abrirEdicion(i, 'ingreso')" style="border: none; background: none; cursor: pointer;" title="Editar">✏️</button>
                </div>
              </div>
            </section>

            <!-- Gastos Fijos -->
            <section class="glass-card">
              <h3 style="font-size: 1rem; margin-bottom: 1rem;">🏠 Gastos Fijos</h3>
              <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem;">
                <input type="text" v-model="nuevoFijo.nombre" placeholder="Nombre (ej. Alquiler)" class="form-input">
                <input type="number" v-model="nuevoFijo.monto" placeholder="Monto" class="form-input">
                <button @click="guardarFijo" class="btn btn-primary btn-sm">Añadir Fijo</button>
              </div>
              <div v-for="f in fijos" :key="f.id" style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; padding: 0.5rem; background: rgba(0,0,0,0.1); border-radius: 6px; margin-bottom: 0.4rem;">
                <span>{{ f.nombre }}: <b>{{ f.monto }}€</b></span>
                <div style="display: flex; gap: 0.3rem;">
                  <button @click="abrirEdicion(f, 'fijo')" style="border: none; background: none; cursor: pointer;" title="Editar">✏️</button>
                  <button @click="eliminarFijo(f.id)" style="border: none; background: none; cursor: pointer;">❌</button>
                </div>
              </div>
            </section>

            <!-- Presupuestos -->
            <section class="glass-card">
              <h3 style="font-size: 1rem; margin-bottom: 1rem;">🎯 Definir Presupuesto</h3>
              <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <input type="text" v-model="nuevoPresupuesto.categoria" placeholder="Categoría (ej. Comida)" class="form-input">
                <input type="number" v-model="nuevoPresupuesto.monto_limit" placeholder="Límite €" class="form-input">
                <button @click="guardarPresupuesto" class="btn btn-primary btn-sm">Establecer Límite</button>
              </div>
            </section>
          </div>

          <!-- Asistente Financiero (Chat) -->
          <section v-else class="glass-card">
            <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
              <span style="font-size: 2.2rem; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));">🧞‍♂️</span>
              <h2 style="margin: 0; font-size: 1.3rem; color: #1f2937; font-weight: 800;">Genie Insights</h2>
            </div>
            
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem;">
              <button @click="hacerPreguntaChat('¿Cuánto gasté en comida este mes?')" class="btn btn-outline btn-sm" style="font-size: 0.85rem; padding: 0.4rem 0.8rem; border-radius: 20px;" :disabled="cargandoChat">¿Cuánto gasté?</button>
              <button @click="hacerPreguntaChat('Dame un consejo para ahorrar')" class="btn btn-outline btn-sm" style="font-size: 0.85rem; padding: 0.4rem 0.8rem; border-radius: 20px;" :disabled="cargandoChat">¿Cómo ahorro?</button>
            </div>

            <div style="display: flex; gap: 0.5rem; background: #f9fafb; padding: 0.5rem; border-radius: 12px; border: 1px solid #e5e7eb;">
              <input type="text" v-model="textoChat" @keydown.enter="hacerPreguntaChat()" placeholder="Ej. ¿Cuánto en Comida?" class="form-input" style="flex: 1; margin: 0; border: none; background: transparent; outline: none; box-shadow: none;" :disabled="cargandoChat" />
              <button @click="hacerPreguntaChat()" class="btn btn-primary" :disabled="cargandoChat || !textoChat.trim()" style="padding: 0.5rem 1.2rem; border-radius: 8px;">
                <span v-if="cargandoChat" class="spinner"></span>
                <span v-else>Enviar 🚀</span>
              </button>
            </div>

            <div v-if="respuestaChat" style="margin-top: 1.5rem; padding: 1.5rem; background: linear-gradient(to right, rgba(79, 70, 229, 0.05), rgba(16, 185, 129, 0.05)); border-radius: 12px; border-left: 4px solid #4f46e5;">
              <div style="font-size: 0.95rem; color: #374151; white-space: pre-wrap; line-height: 1.6;" v-html="respuestaChat.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')"></div>
            </div>
          </section>

          <!-- Zona de Entrada (Natural Language) -->
          <section class="glass-card" style="margin-top: 1.5rem;">
            <label for="textoGasto" class="input-label">
              Registrar Gasto:
            </label>
            <div class="textarea-wrapper">
              <textarea
                id="textoGasto"
                v-model="textoGasto"
                class="natural-input"
                placeholder="Ej. Ayer me gasté 35 euros cenando..."
                :disabled="cargandoProceso"
                @keydown.enter.ctrl="procesarGasto"
                style="min-height: 80px;"
              ></textarea>
            </div>
            <div class="btn-container" style="display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap;">
              <button
                @click="procesarGasto"
                :disabled="cargandoProceso || !textoGasto.trim()"
                class="btn btn-primary"
                style="flex: 1; min-width: 140px;"
              >
                <span v-if="cargandoProceso" class="spinner"></span>
                <span v-else>✨</span>
                {{ cargandoProceso ? 'IA...' : 'Procesar' }}
              </button>
              
              <label class="btn btn-outline" style="flex: 1; min-width: 140px; margin: 0;" :style="{ opacity: cargandoProceso ? 0.6 : 1, cursor: cargandoProceso ? 'not-allowed' : 'pointer' }">
                <span v-if="cargandoProceso" class="spinner"></span>
                <span v-else>📄</span>
                Escanear
                <input type="file" accept="image/*,.pdf" style="display: none;" @change="escanearRecibo" :disabled="cargandoProceso">
              </label>
            </div>
          </section>

          <!-- Formulario de Confirmación (en sidebar si cabe) -->
          <section v-if="gastoExtraido" class="glass-card confirmation-section" style="margin-top: 1.5rem;">
            <h2 class="confirmation-header">🧐 Confirmar</h2>
            <div class="form-grid" style="grid-template-columns: 1fr;">
              <div class="form-group">
                <input type="number" step="0.01" v-model="gastoExtraido.monto" class="form-input" placeholder="Monto" />
              </div>
              <div class="form-group">
                <input type="text" v-model="gastoExtraido.comercio" class="form-input" placeholder="Comercio" />
              </div>
              <div class="form-group">
                <input type="date" v-model="gastoExtraido.fecha" class="form-input" />
              </div>
              <div class="form-group">
                <input type="text" v-model="gastoExtraido.categoria" class="form-input" placeholder="Categoría" />
              </div>
              <div class="form-group">
                <input type="file" accept="image/*,.pdf" @change="manejarArchivo" class="form-input" />
              </div>
            </div>
            <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
              <button @click="gastoExtraido = null" class="btn btn-outline btn-sm" style="flex: 1;">X</button>
              <button @click="guardarGasto" :disabled="cargandoGuardado" class="btn btn-success btn-sm" style="flex: 2;">
                💾 {{ cargandoGuardado ? '...' : 'Guardar' }}
              </button>
            </div>
          </section>
        </aside>

        <!-- Main Content: Data & History -->
        <main class="dashboard-main">
          <!-- Stats Cards: Planificación -->
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem;">
            <!-- Ingresos -->
            <div class="stat-box" style="border-top: 4px solid var(--success);">
              <h3>Ingresos</h3>
              <div class="stat-value" :style="privacyStyle">{{ resumen.total_ingresos.toFixed(2) }} <span class="stat-unit">EUR</span></div>
            </div>
            <!-- Gastos Totales -->
            <div class="stat-box" style="border-top: 4px solid var(--error);">
              <h3>Gasto Total <small style="font-size:0.7rem; color: var(--text-muted);">({{ resumen.presupuesto_gastado_porcentaje }}%)</small></h3>
              <div class="stat-value" :style="privacyStyle">{{ resumen.total_gastos.toFixed(2) }} <span class="stat-unit">EUR</span></div>
            </div>
            <!-- Balance Disponible -->
            <div class="stat-box" :style="{ borderTop: '4px solid ' + (resumen.balance_final >= 0 ? 'var(--primary)' : 'var(--error)'), background: 'rgba(139, 92, 246, 0.05)' }">
              <h3>Balance Final</h3>
              <div class="stat-value" :style="privacyStyle" :class="{ 'text-error': resumen.balance_final < 0 }">{{ resumen.balance_final.toFixed(2) }} <span class="stat-unit">EUR</span></div>
            </div>
          </div>

          <!-- Presupuestos: Progreso -->
          <section v-if="presupuestos.length > 0" class="glass-card" style="margin-bottom: 1.5rem;">
            <h2 style="font-size: 1rem; margin-bottom: 1rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Presupuestos del Mes</h2>
            <div v-for="p in presupuestos" :key="p.id" style="margin-bottom: 1rem;">
              <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; margin-bottom: 0.4rem;">
                <span style="font-weight: 600;">{{ p.categoria }}</span>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                  <span>{{ getGastoPorCategoria(p.categoria).toFixed(0) }}€ / {{ p.monto_limite }}€</span>
                  <button @click="abrirEdicion(p, 'presupuesto')" style="border: none; background: none; cursor: pointer; font-size: 0.9rem;" title="Editar">✏️</button>
                </div>
              </div>
              <div style="height: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden;">
                <div 
                  :style="{ 
                    width: Math.min((getGastoPorCategoria(p.categoria) / p.monto_limite) * 100, 100) + '%',
                    backgroundColor: getGastoPorCategoria(p.categoria) > p.monto_limite ? 'var(--error)' : 'var(--primary)'
                  }" 
                  style="height: 100%; transition: width 0.5s ease;"
                ></div>
              </div>
            </div>
          </section>

          <!-- Gráfico -->
          <section class="glass-card" style="margin-bottom: 2rem;">
            <div class="dashboard-wrapper" v-if="chartData.labels.length > 0" style="height: 250px; position: relative;" :style="privacyStyle">
              <Doughnut :data="chartData" :options="chartOptions" />
            </div>
            <div v-else class="empty-state" style="padding: 1rem;">
               <p>Añade gastos para ver el gráfico</p>
            </div>
          </section>

          <!-- Tabla de Gastos -->
          <section class="glass-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; gap: 1rem; flex-wrap: wrap;">
              <input type="text" v-model="filtroComercio" placeholder="🔍 Buscar comercio..." class="form-input" style="max-width: 250px; margin: 0;" />
              
              <label style="display: flex; align-items: center; cursor: pointer; background: rgba(0,0,0,0.05); padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.85rem;">
                <span style="margin-right: 0.5rem; font-weight: bold;">👻 Incógnito</span>
                <input type="checkbox" v-model="modoPrivacidad" />
              </label>
            </div>

            <div class="table-responsive">
              <table class="gastos-table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Comercio</th>
                    <th class="text-right">Total</th>
                    <th class="text-center">Recibo</th>
                    <th class="text-center"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="gasto in tablaFiltrada" :key="gasto.id">
                    <td class="col-date">{{ gasto.fecha }}</td>
                    <td class="col-comercio">
                      <div class="col-comercio-name">{{ gasto.comercio }}</div>
                      <span class="category-tag-sm">{{ gasto.categoria }}</span>
                    </td>
                    <td class="col-total" :style="privacyStyle">
                      <strong>{{ gasto.monto.toFixed(2) }}</strong><span style="font-size: 0.7rem; color: #94a3b8; margin-left: 2px;">{{ gasto.moneda }}</span>
                    </td>
                    <td class="text-center">
                      <button v-if="gasto.ruta_recibo" @click="verRecibo(gasto.ruta_recibo)" class="btn btn-sm" style="background: none; border: none; cursor: pointer; font-size: 1.1rem; filter: saturate(0) brightness(1.2);" title="Ver recibo">
                        {{ gasto.ruta_recibo.toLowerCase().endsWith('.pdf') ? '📄' : '📎' }}
                      </button>
                    </td>
                    <td class="text-center" style="white-space: nowrap;">
                      <button @click="abrirEdicion(gasto, 'gasto')" style="background: none; border: none; cursor: pointer; font-size: 0.9rem; opacity: 0.7;" title="Editar">✏️</button>
                      <button @click="eliminarGasto(gasto.id)" style="background: none; border: none; cursor: pointer; font-size: 0.9rem; opacity: 0.6;">🗑️</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>
      </div>

      <!-- Modal de Edición -->
      <div v-if="mostrarModalEdicion && editandoItem" 
           class="modal-overlay" @click.self="cerrarEdicion"
           style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.75); display: flex; justify-content: center; align-items: center; z-index: 1001;">
        <div class="glass-card" @click.stop style="width: min(480px, 95vw); animation: slideUp 0.3s ease-out; border: 1px solid rgba(139,92,246,0.4);">
          
          <!-- Header del modal -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <h2 style="margin: 0; font-size: 1.2rem; font-weight: 800;">✏️ Editar {{ editandoTipo === 'gasto' ? 'Gasto' : editandoTipo === 'ingreso' ? 'Ingreso' : editandoTipo === 'presupuesto' ? 'Presupuesto' : 'Gasto Fijo' }}</h2>
            <button @click="cerrarEdicion" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer; line-height: 1;">&times;</button>
          </div>

          <!-- Campos para GASTO -->
          <div v-if="editandoTipo === 'gasto'" style="display: flex; flex-direction: column; gap: 0.8rem;">
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Comercio</label>
              <input type="text" v-model="editandoItem.comercio" class="form-input" />
            </div>
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Monto</label>
              <input type="number" step="0.01" min="0.01" v-model="editandoItem.monto" class="form-input" />
            </div>
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Fecha</label>
              <input type="date" v-model="editandoItem.fecha" class="form-input" />
            </div>
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Categoría</label>
              <input type="text" v-model="editandoItem.categoria" class="form-input" />
            </div>
          </div>

          <!-- Campos para INGRESO -->
          <div v-if="editandoTipo === 'ingreso'" style="display: flex; flex-direction: column; gap: 0.8rem;">
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Fuente</label>
              <input type="text" v-model="editandoItem.fuente" class="form-input" />
            </div>
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Monto</label>
              <input type="number" step="0.01" min="0.01" v-model="editandoItem.monto" class="form-input" />
            </div>
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Fecha</label>
              <input type="date" v-model="editandoItem.fecha" class="form-input" />
            </div>
          </div>

          <!-- Campos para PRESUPUESTO -->
          <div v-if="editandoTipo === 'presupuesto'" style="display: flex; flex-direction: column; gap: 0.8rem;">
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Categoría</label>
              <input type="text" v-model="editandoItem.categoria" class="form-input" />
            </div>
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Límite mensual (€)</label>
              <input type="number" step="0.01" min="0.01" v-model="editandoItem.monto_limite" class="form-input" />
            </div>
          </div>

          <!-- Campos para GASTO FIJO -->
          <div v-if="editandoTipo === 'fijo'" style="display: flex; flex-direction: column; gap: 0.8rem;">
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Nombre</label>
              <input type="text" v-model="editandoItem.nombre" class="form-input" />
            </div>
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Monto mensual (€)</label>
              <input type="number" step="0.01" min="0.01" v-model="editandoItem.monto" class="form-input" />
            </div>
            <div>
              <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">Categoría</label>
              <input type="text" v-model="editandoItem.categoria" class="form-input" />
            </div>
          </div>

          <!-- Botones de acción -->
          <div style="display: flex; gap: 0.75rem; margin-top: 1.5rem;">
            <button @click="cerrarEdicion" class="btn btn-outline" style="flex: 1;">Cancelar</button>
            <button @click="actualizarItem" class="btn btn-success" style="flex: 2;">💾 Guardar cambios</button>
          </div>
        </div>
      </div>

      <!-- Modal para Imagen -->
      <div v-if="imagenModal" class="modal-overlay" @click="imagenModal = null" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.85); display: flex; justify-content: center; align-items: center; z-index: 1000; cursor: pointer;">
        <div style="position: relative; max-width: 90%; max-height: 90%;" @click.stop>
          <button @click="imagenModal = null" style="position: absolute; top: -40px; right: -40px; background: none; border: none; color: white; font-size: 3rem; cursor: pointer; line-height: 1;">&times;</button>
          <img :src="`http://localhost:5000/uploads/${imagenModal}`" style="max-width: 100%; max-height: 90vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);" />
        </div>
      </div>
    </div>
  </div>
</template>