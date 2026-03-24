<script setup>
import { ref, computed, onMounted } from 'vue'
import GenieChat from './components/GenieChat.vue'
import DashboardCharts from './components/DashboardCharts.vue'
import ExpenseForms from './components/ExpenseForms.vue'

// Logic for charts and shared state remains here for orchestration

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

const errorMensaje = ref('')
const exitoMensaje = ref('')

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

const nombreEditable = computed({
  get: () => {
    if (!editandoItem.value) return ''
    return editandoItem.value.comercio || editandoItem.value.fuente || editandoItem.value.nombre || editandoItem.value.categoria || ''
  },
  set: (val) => {
    if (!editandoItem.value) return
    if (editandoItem.value.comercio !== undefined) editandoItem.value.comercio = val
    else if (editandoItem.value.fuente !== undefined) editandoItem.value.fuente = val
    else if (editandoItem.value.nombre !== undefined) editandoItem.value.nombre = val
    else if (editandoItem.value.categoria !== undefined) editandoItem.value.categoria = val
  }
})

const montoEditable = computed({
  get: () => {
    if (!editandoItem.value) return 0
    return editandoItem.value.monto !== undefined ? editandoItem.value.monto : (editandoItem.value.monto_limite || 0)
  },
  set: (val) => {
    if (!editandoItem.value) return
    const num = parseFloat(val) || 0
    if (editandoItem.value.monto !== undefined) editandoItem.value.monto = num
    else if (editandoItem.value.monto_limite !== undefined) editandoItem.value.monto_limite = num
  }
})

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


// Functions to refresh data
const refrescarDatos = async () => {
  await cargarGastos()
  await cargarPlanificacion()
  await cargarEstadisticas()
  await cargarHistorico()
  await cargarAnalisisAvanzado()
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

// Removidos métodos de escaneo y procesamiento (ahora en ExpenseForms.vue)

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
    const res = await fetch(`http://localhost:5000/api/fijos/${id}`, { method: 'DELETE' })
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

// Estados para Fase 11: Savings Goals & Análisis IA
const objetivos = ref([])
const historicoMensual = ref([])
const analisisIA = ref(null)
const cargandoAnalisis = ref(false)
const nuevoObjetivo = ref({ nombre: '', meta_monto: 0, fecha_limite: '' })

const cargarObjetivos = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/objetivos')
    objetivos.value = await res.json()
  } catch (e) { console.error('Error objetivos:', e) }
}

const cargarHistorico = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/historico_mensual')
    historicoMensual.value = await res.json()
  } catch (e) { console.error('Error historico:', e) }
}

const cargarAnalisisAvanzado = async () => {
  cargandoAnalisis.value = true
  try {
    const res = await fetch('http://localhost:5000/api/analisis_avanzado')
    analisisIA.value = await res.json()
  } catch (e) { console.error('Error analisis:', e) }
  finally { cargandoAnalisis.value = false }
}

const crearObjetivo = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/objetivos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nuevoObjetivo.value)
    })
    if (res.ok) {
      cargarObjetivos()
      nuevoObjetivo.value = { nombre: '', meta_monto: 0, fecha_limite: '' }
    }
  } catch (e) { console.error('Error crear objetivo:', e) }
}

const abonarObjetivo = async (id, montoActual) => {
  const abono = prompt('¿Cuánto quieres añadir a este objetivo?', '10')
  if (!abono || isNaN(abono)) return
  
  try {
    await fetch(`http://localhost:5000/api/objetivos/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ monto_actual: montoActual + parseFloat(abono) })
    })
    cargarObjetivos()
  } catch (e) { console.error('Error abono:', e) }
}

const eliminarObjetivo = async (id) => {
  if (!confirm('¿Seguro que quieres eliminar este objetivo?')) return
  try {
    await fetch(`http://localhost:5000/api/objetivos/${id}`, { method: 'DELETE' })
    cargarObjetivos()
  } catch (e) { console.error('Error eliminar objetivo:', e) }
}

const eliminarIngreso = async (id) => {
  if (!confirm('¿Seguro que quieres eliminar este ingreso?')) return
  try {
    const res = await fetch(`http://localhost:5000/api/ingresos/${id}`, { method: 'DELETE' })
    if (res.ok) await cargarPlanificacion()
  } catch (e) { console.error('Error eliminar ingreso:', e) }
}

const eliminarPresupuesto = async (id) => {
  if (!confirm('¿Seguro que quieres eliminar este presupuesto?')) return
  try {
    const res = await fetch(`http://localhost:5000/api/presupuestos/${id}`, { method: 'DELETE' })
    if (res.ok) await cargarPlanificacion()
  } catch (e) { console.error('Error eliminar presupuesto:', e) }
}

const chartDataMensual = computed(() => {
  return {
    labels: historicoMensual.value.map(h => h.mes),
    datasets: [
      {
        label: 'Ingresos',
        backgroundColor: '#10b981',
        data: historicoMensual.value.map(h => h.ingresos)
      },
      {
        label: 'Gastos',
        backgroundColor: '#ef4444',
        data: historicoMensual.value.map(h => h.gastos)
      }
    ]
  }
})

const chartOptionsBar = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } }
  },
  layout: {
    padding: { bottom: 10 }
  }
}

const onMountedTasks = async () => {
  cargarGastos()
  cargarEstadisticas()
  cargarPlanificacion()
  cargarObjetivos()
  cargarHistorico()
  cargarAnalisisAvanzado()
}

onMounted(onMountedTasks)
</script>

<template>
  <div class="min-h-screen bg-slate-50 py-10 px-4 sm:px-6 lg:px-8 font-['Inter',_sans-serif]">
    <div class="max-w-7xl mx-auto space-y-10">
      
      <!-- Header -->
      <header class="flex flex-col md:flex-row md:items-center justify-between gap-6 animate-slide-up">
        <div>
          <h1 class="text-4xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            GastoGenie <span class="text-3xl">🧞‍♂️</span>
          </h1>
          <p class="text-slate-500 font-medium mt-1">Tu Asistente Financiero Inteligente</p>
        </div>
        
        <div class="flex items-center gap-4">
          <button @click="mostrarConfiguracion = !mostrarConfiguracion" 
            class="px-5 py-2.5 rounded-2xl font-bold bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:shadow-sm transition-all active:scale-95 flex items-center gap-2 outline-none">
            <span v-if="mostrarConfiguracion">📉 Panel de Control</span>
            <span v-else>⚙️ Configuración</span>
          </button>
          
          <div class="h-10 w-px bg-slate-200 hidden md:block"></div>
          
          <label class="flex items-center gap-3 cursor-pointer bg-white px-4 py-2 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all">
            <span class="text-[10px] uppercase font-bold tracking-widest text-slate-400">👻 Privacidad</span>
            <input type="checkbox" v-model="modoPrivacidad" class="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300 transition-all" />
          </label>
        </div>
      </header>

      <!-- Mensajes Globales -->
      <transition name="fade">
        <div v-if="errorMensaje || exitoMensaje" class="fixed top-6 right-6 z-50 flex flex-col gap-3 min-w-[320px] max-w-md">
          <div v-if="errorMensaje" class="bg-white border-l-4 border-red-500 rounded-2xl shadow-xl p-5 flex items-start gap-4 animate-slide-up">
            <div class="flex-shrink-0 w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-red-600">⚠️</div>
            <div class="flex-1">
              <h4 class="text-sm font-bold text-slate-900 uppercase tracking-wider mb-1">Error</h4>
              <p class="text-sm text-slate-500 leading-relaxed">{{ errorMensaje }}</p>
            </div>
            <button @click="errorMensaje=''" class="text-slate-300 hover:text-slate-500">&times;</button>
          </div>
          <div v-if="exitoMensaje" class="bg-white border-l-4 border-emerald-500 rounded-2xl shadow-xl p-5 flex items-start gap-4 animate-slide-up">
            <div class="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">✅</div>
            <div class="flex-1">
              <h4 class="text-sm font-bold text-slate-900 uppercase tracking-wider mb-1">Éxito</h4>
              <p class="text-sm text-slate-500 leading-relaxed">{{ exitoMensaje }}</p>
            </div>
            <button @click="exitoMensaje=''" class="text-slate-300 hover:text-slate-500">&times;</button>
          </div>
        </div>
      </transition>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-10">
        <!-- Sidebar -->
        <aside class="lg:col-span-4 space-y-8 animate-slide-up" style="animation-delay: 0.1s">
          <transition name="fade" mode="out-in">
            <div v-if="mostrarConfiguracion" class="space-y-6">
              <h2 class="text-xs uppercase font-bold tracking-[0.2em] text-slate-400 mb-2">Ajustes Mensuales</h2>
              <!-- Nómina -->
              <section class="glass-card p-6">
                <div class="flex items-center gap-3 mb-5">
                    <div class="w-8 h-8 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center text-lg">💰</div>
                    <h3 class="font-bold text-slate-800">Ingresos</h3>
                </div>
                <div class="space-y-4">
                  <input type="text" v-model="nuevaNomina.fuente" placeholder="Fuente" class="form-input text-sm">
                  <div class="grid grid-cols-2 gap-4">
                    <input type="number" v-model="nuevaNomina.monto" placeholder="Monto" class="form-input text-sm">
                    <input type="date" v-model="nuevaNomina.fecha" class="form-input text-sm">
                  </div>
                  <button @click="guardarNomina" class="btn btn-primary w-full bg-emerald-600 hover:bg-emerald-700 shadow-emerald-50 py-2.5 text-sm">Añadir Ingreso</button>
                </div>
                <div v-if="ingresos.length > 0" class="mt-6 pt-6 border-t border-slate-50 space-y-2">
                    <div v-for="i in ingresos" :key="i.id" class="flex justify-between items-center p-3 rounded-xl bg-slate-50 group hover:bg-white border border-transparent hover:border-slate-100 transition-all">
                        <span class="text-sm font-bold text-slate-700">{{ i.fuente }}</span>
                        <div class="flex items-center gap-3">
                            <span class="text-sm font-extrabold text-emerald-600">+{{ i.monto }}€</span>
                            <button @click="eliminarIngreso(i.id)" class="opacity-0 group-hover:opacity-100 p-1 text-red-400">❌</button>
                        </div>
                    </div>
                </div>
              </section>
              
              <!-- Gastos Fijos -->
              <section class="glass-card p-6">
                <h3 class="font-bold text-slate-800 mb-4">🏠 Gastos Fijos</h3>
                <div class="flex gap-2 mb-4">
                  <input type="text" v-model="nuevoFijo.nombre" placeholder="Nombre" class="form-input text-sm flex-1">
                  <input type="number" v-model="nuevoFijo.monto" placeholder="€" class="form-input text-sm w-20">
                  <button @click="guardarFijo" class="btn btn-primary px-3 bg-indigo-600 text-sm">Añadir</button>
                </div>
                <div v-for="f in fijos" :key="f.id" class="flex justify-between items-center p-3 rounded-xl bg-slate-50 mb-2 border border-transparent hover:border-slate-100 transition-all hover:bg-white group">
                  <span class="text-sm font-bold text-slate-700">{{ f.nombre }}</span>
                  <div class="flex items-center gap-3">
                    <span class="text-sm font-extrabold">{{ f.monto }}€</span>
                    <button @click="eliminarFijo(f.id)" class="opacity-0 group-hover:opacity-100 text-red-400">❌</button>
                  </div>
                </div>
              </section>

              <!-- Presupuestos -->
              <section class="glass-card p-6">
                <h3 class="font-bold text-slate-800 mb-4">🎯 Presupuestos</h3>
                <div class="flex gap-2 mb-4">
                  <input type="text" v-model="nuevoPresupuesto.categoria" placeholder="Categoría" class="form-input text-sm flex-1">
                  <input type="number" v-model="nuevoPresupuesto.monto_limit" placeholder="Límite" class="form-input text-sm w-20">
                  <button @click="guardarPresupuesto" class="btn btn-primary px-3 bg-amber-600 shadow-amber-50 text-sm">Set</button>
                </div>
                <div v-for="p in presupuestos" :key="p.id" class="flex justify-between items-center p-3 rounded-xl bg-slate-50 mb-2 border border-transparent hover:border-slate-100 transition-all hover:bg-white group">
                  <span class="text-sm font-bold text-slate-700">{{ p.categoria }}</span>
                  <div class="flex items-center gap-3">
                    <span class="text-sm font-extrabold text-amber-600">{{ p.monto_limite }}€</span>
                    <button @click="eliminarPresupuesto(p.id)" class="opacity-0 group-hover:opacity-100 text-red-400">❌</button>
                  </div>
                </div>
              </section>
            </div>
            <div v-else class="space-y-8">
              <GenieChat />
              <section class="glass-card p-6">
                <div class="flex flex-col gap-1 mb-6">
                    <h3 class="text-sm font-bold text-slate-900 tracking-tight">🏆 Objetivos de Ahorro</h3>
                    <p class="text-[10px] uppercase font-bold tracking-widest text-slate-400">Hitos del mes</p>
                </div>
                <div class="space-y-6">
                  <div v-for="obj in objetivos" :key="obj.id" class="bg-indigo-50/10 p-4 rounded-2xl border border-indigo-100/50">
                    <div class="flex justify-between items-center mb-3">
                      <span class="font-extrabold text-slate-800 tracking-tight">{{ obj.nombre }}</span>
                      <div class="flex gap-2">
                        <button @click="abonarObjetivo(obj.id, obj.monto_actual)" class="w-8 h-8 rounded-full bg-white flex items-center justify-center shadow-sm hover:scale-110 transition-transform">💰</button>
                        <button @click="eliminarObjetivo(obj.id)" class="w-8 h-8 rounded-full bg-white flex items-center justify-center shadow-sm hover:scale-110 transition-transform">❌</button>
                      </div>
                    </div>
                    <div class="flex justify-between text-xs font-bold mb-2">
                      <span class="text-slate-500">{{ obj.monto_actual }}€ / {{ obj.meta_monto }}€</span>
                      <span class="text-indigo-600">{{ obj.porcentaje }}%</span>
                    </div>
                    <div class="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div :style="{ width: obj.porcentaje + '%' }" class="h-full bg-indigo-600 rounded-full transition-all duration-1000"></div>
                    </div>
                  </div>
                  <div class="pt-4 border-t border-slate-50 flex gap-2">
                    <input type="text" v-model="nuevoObjetivo.nombre" placeholder="Nombre" class="form-input text-xs flex-1" />
                    <input type="number" v-model="nuevoObjetivo.meta_monto" placeholder="Meta" class="form-input text-xs w-20" />
                    <button @click="crearObjetivo" class="btn btn-primary px-4 py-2 text-xs bg-indigo-600">Crear</button>
                  </div>
                </div>
              </section>
            </div>
          </transition>
          <ExpenseForms @onSaved="refrescarDatos" />
        </aside>

        <!-- Main Content -->
        <main class="lg:col-span-8 space-y-10 animate-slide-up" style="animation-delay: 0.2s">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="md:col-span-3 glass-card p-8 bg-gradient-to-br from-indigo-600 to-indigo-800 text-white border-transparent shadow-xl shadow-indigo-100 relative overflow-hidden group">
              <div class="absolute -right-10 -bottom-10 w-48 h-48 bg-white/10 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-1000"></div>
              <div class="relative z-10">
                <h3 class="text-[10px] uppercase font-bold tracking-widest text-indigo-100/70 mb-2">Balance Disponible</h3>
                <div class="flex items-baseline gap-2">
                  <span :style="privacyStyle" class="text-5xl font-black tracking-tight" :class="resumen.balance_final < 0 ? 'text-red-200' : ''">
                    {{ resumen.balance_final.toFixed(2) }}
                  </span>
                  <span class="text-2xl font-bold text-indigo-200">EUR</span>
                </div>
                <div class="mt-6 w-full h-2 bg-white/20 rounded-full overflow-hidden">
                    <div :style="{ width: Math.min(resumen.presupuesto_gastado_porcentaje, 100) + '%' }" class="h-full bg-white shadow-[0_0_12px_white] transition-all duration-1000"></div>
                </div>
              </div>
            </div>
            
            <div class="glass-card p-6 group hover:translate-y-[-4px] transition-all">
              <div class="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center text-xl mb-4 group-hover:scale-110 transition-transform">📈</div>
              <h3 class="text-[10px] uppercase font-bold tracking-widest text-slate-400 mb-1">Ingresos</h3>
              <p :style="privacyStyle" class="text-2xl font-black text-slate-800">{{ resumen.total_ingresos.toFixed(0) }}€</p>
            </div>

            <div class="glass-card p-6 group hover:translate-y-[-4px] transition-all">
              <div class="w-10 h-10 bg-red-50 text-red-500 rounded-2xl flex items-center justify-center text-xl mb-4 group-hover:scale-110 transition-transform">📉</div>
              <h3 class="text-[10px] uppercase font-bold tracking-widest text-slate-400 mb-1">Gastos Totales</h3>
              <p :style="privacyStyle" class="text-2xl font-black text-slate-800">{{ resumen.total_gastos.toFixed(0) }}€</p>
            </div>

            <div class="glass-card p-6 group hover:translate-y-[-4px] transition-all">
              <div class="w-10 h-10 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center text-xl mb-4 group-hover:scale-110 transition-transform">🎯</div>
              <h3 class="text-[10px] uppercase font-bold tracking-widest text-slate-400 mb-1">Gasto Presupuesto</h3>
              <p class="text-2xl font-black text-slate-800">{{ resumen.presupuesto_gastado_porcentaje }}%</p>
            </div>
          </div>

          <!-- Widget Predictor IA -->
          <transition name="fade">
            <section v-if="analisisIA" class="glass-card p-8 bg-white border-indigo-50 shadow-lg shadow-indigo-50/30 relative overflow-hidden">
                <div class="absolute -right-6 -top-6 w-32 h-32 bg-indigo-50 rounded-full blur-3xl opacity-50"></div>
                <div class="flex items-center gap-4 mb-8">
                    <div class="w-12 h-12 bg-indigo-600 text-white rounded-2xl flex items-center justify-center text-2xl shadow-lg">🔮</div>
                    <div>
                        <h2 class="text-xl font-bold text-slate-900 tracking-tight">Análisis Predictivo</h2>
                        <p class="text-[10px] uppercase font-bold tracking-widest text-indigo-500">Genie Intelligence</p>
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10">
                    <div class="space-y-2">
                        <h4 class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Predicción</h4>
                        <p class="text-sm font-semibold text-slate-700 leading-relaxed">{{ analisisIA.prediccion }}</p>
                    </div>
                    <div class="space-y-2">
                        <h4 class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Fugas 🐜</h4>
                        <p class="text-sm font-semibold text-slate-700 leading-relaxed">{{ analisisIA.gastos_hormiga }}</p>
                    </div>
                    <div class="bg-indigo-50/50 p-5 rounded-3xl border border-indigo-100 flex items-center">
                        <p class="text-sm font-bold text-indigo-900 italic leading-relaxed text-center w-full">"{{ analisisIA.consejo_ahorro }}"</p>
                    </div>
                </div>
            </section>
          </transition>

          <!-- Gráficos -->
          <DashboardCharts :chartData="chartData" :chartOptions="chartOptions" :chartDataMensual="chartDataMensual" :chartOptionsBar="chartOptionsBar" />

          <!-- Transacciones -->
          <section class="glass-card shadow-xl overflow-hidden border-slate-100">
            <div class="p-8 border-b border-slate-50 flex flex-col sm:flex-row justify-between items-center bg-white gap-4">
              <div>
                <h3 class="text-xl font-bold text-slate-900 tracking-tight">Transacciones</h3>
                <p class="text-xs text-slate-400 font-medium italic mt-1">Historial del mes corriente</p>
              </div>
              <div class="relative">
                <span class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
                <input type="text" v-model="filtroComercio" placeholder="Buscar..." class="bg-slate-50 border-none rounded-2xl pl-10 pr-4 py-2.5 text-sm outline-none w-full sm:w-64 focus:ring-2 focus:ring-indigo-500/10 transition-all font-medium">
              </div>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-slate-50 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                    <th class="px-8 py-4">Fecha</th>
                    <th class="px-8 py-4">Comercio / Categoría</th>
                    <th class="px-8 py-4 text-right">Monto</th>
                    <th class="px-8 py-4 text-center">Recibo</th>
                    <th class="px-8 py-4"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-50">
                  <tr v-for="gasto in tablaFiltrada" :key="gasto.id" class="hover:bg-slate-50/80 transition-all group font-medium text-slate-600">
                    <td class="px-8 py-5 text-sm italic text-slate-400">{{ gasto.fecha }}</td>
                    <td class="px-8 py-5">
                      <div class="flex flex-col">
                        <span class="font-bold text-slate-900">{{ gasto.comercio }}</span>
                        <span class="text-[10px] uppercase font-bold text-indigo-500 mt-0.5">{{ gasto.categoria }}</span>
                      </div>
                    </td>
                    <td class="px-8 py-5 text-right font-black text-slate-900" :style="privacyStyle">
                        <span class="text-lg">{{ gasto.monto.toFixed(2) }}</span>
                        <span class="text-[10px] ml-1 text-slate-400 uppercase tracking-widest">{{ gasto.moneda }}</span>
                    </td>
                    <td class="px-8 py-5 text-center">
                        <button v-if="gasto.ruta_recibo" @click="verRecibo(gasto.ruta_recibo)" class="w-8 h-8 rounded-xl bg-white border border-slate-100 flex items-center justify-center shadow-sm">
                            {{ gasto.ruta_recibo.toLowerCase().endsWith('.pdf') ? '📄' : '📎' }}
                        </button>
                    </td>
                    <td class="px-8 py-5 text-right">
                        <div class="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button @click="abrirEdicion(gasto, 'gasto')" class="p-2 hover:bg-white rounded-xl text-sm transition-all">✏️</button>
                            <button @click="eliminarGasto(gasto.id)" class="p-2 hover:bg-white rounded-xl text-red-500 text-sm transition-all">🗑️</button>
                        </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>
      </div>

      <!-- Modal Edición -->
      <transition name="fade">
        <div v-if="mostrarModalEdicion && editandoItem" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-md" @click.self="cerrarEdicion">
          <div class="bg-white w-full max-w-lg rounded-[2.5rem] shadow-2xl p-10 animate-slide-up relative overflow-hidden border border-slate-100">
            <div class="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-full blur-3xl opacity-50 -mr-16 -mt-16"></div>
            <div class="relative z-10">
                <div class="flex justify-between items-center mb-10">
                    <div>
                        <h2 class="text-2xl font-black text-slate-900 tracking-tight">Editar Registro</h2>
                        <p class="text-xs font-bold text-indigo-500 uppercase tracking-widest mt-1">Actualización manual</p>
                    </div>
                    <button @click="cerrarEdicion" class="w-10 h-10 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-all font-black">&times;</button>
                </div>
                <div class="space-y-6">
                    <div class="space-y-2">
                        <label class="text-[10px] uppercase font-extrabold tracking-widest text-slate-400">Comercio / Nombre</label>
                        <input type="text" v-model="nombreEditable" class="form-input text-sm" />
                    </div>
                    <div class="space-y-2">
                        <label class="text-[10px] uppercase font-extrabold tracking-widest text-slate-400">Monto total (€)</label>
                        <input type="number" v-model="montoEditable" class="form-input text-lg font-black text-indigo-600" />
                    </div>
                    <div class="flex gap-4 mt-12 pt-6">
                        <button @click="cerrarEdicion" class="flex-1 py-4 rounded-3xl font-bold text-slate-500 hover:bg-slate-50 transition-all uppercase text-xs tracking-widest">Descartar</button>
                        <button @click="actualizarItem" class="flex-1 py-4 rounded-3xl bg-indigo-600 text-white font-black shadow-xl shadow-indigo-100 hover:bg-indigo-700 transition-all uppercase text-xs tracking-widest">Guardar</button>
                    </div>
                </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- Visor Recibo -->
      <transition name="fade">
        <div v-if="imagenModal" class="fixed inset-0 z-[200] flex items-center justify-center p-6 bg-slate-900/90 backdrop-blur-xl" @click="imagenModal = null">
            <div class="relative max-w-4xl max-h-full animate-slide-up overflow-hidden rounded-[3rem] border-4 border-white/10 shadow-2xl">
                <button @click="imagenModal = null" class="absolute top-6 right-6 w-12 h-12 bg-black/50 backdrop-blur-md text-white rounded-full text-2xl flex items-center justify-center hover:bg-black/80 transition-all z-10">&times;</button>
                <img :src="'http://localhost:5000/uploads/' + imagenModal" alt="Recibo" class="max-w-full max-h-[85vh] object-contain rounded-[2.5rem]" />
            </div>
        </div>
      </transition>

    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
