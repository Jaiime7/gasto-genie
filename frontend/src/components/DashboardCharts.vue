<script setup>
import { Doughnut, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement
} from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, ArcElement, CategoryScale, LinearScale, BarElement)

const props = defineProps({
  chartData: {
    type: Object,
    required: true
  },
  chartOptions: {
    type: Object,
    required: true
  },
  chartDataMensual: {
    type: Object,
    required: true
  },
  chartOptionsBar: {
    type: Object,
    required: true
  }
})
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <!-- Gráfico 1: Distribución por Categoría -->
    <section class="glass-card p-6 flex flex-col min-h-[400px]">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider">Distribución</h3>
          <p class="text-xs text-slate-500 font-medium mt-1">Gasto por Categoría</p>
        </div>
        <span class="px-3 py-1 bg-indigo-50 text-indigo-600 text-[10px] font-bold rounded-full uppercase tracking-widest border border-indigo-100">Este Mes</span>
      </div>
      <div class="flex-1 relative flex items-center justify-center w-full">
        <Doughnut v-if="chartData && chartData.datasets[0].data.length > 0" :data="chartData" :options="chartOptions" />
        <div v-else class="text-slate-400 text-sm italic text-center">
          No hay gastos registrados para este mes.
        </div>
      </div>
    </section>

    <!-- Gráfico 2: Ingresos vs Gastos (Histórico) -->
    <section class="glass-card p-6 flex flex-col min-h-[400px]">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider">Tendencia</h3>
          <p class="text-xs text-slate-500 font-medium mt-1">Análisis Mensual</p>
        </div>
        <span class="px-3 py-1 bg-emerald-50 text-emerald-600 text-[10px] font-bold rounded-full uppercase tracking-widest border border-emerald-100">Histórico</span>
      </div>
      <div class="flex-1 relative w-full">
        <Bar v-if="chartDataMensual && chartDataMensual.datasets[0].data.length > 0" :data="chartDataMensual" :options="chartOptionsBar" />
        <div v-else class="flex items-center justify-center h-full text-slate-400 text-sm italic">
          Cargando datos históricos...
        </div>
      </div>
    </section>
  </div>
</template>
