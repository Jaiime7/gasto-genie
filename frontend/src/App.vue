<script setup>
import { ref } from 'vue'

// Variable reactiva para guardar el mensaje del backend
const mensajeBackend = ref('')

// Función para llamar a Flask
const conectarBackend = async () => {
  try {
    const respuesta = await fetch('http://localhost:5000/api/status')
    const datos = await respuesta.json()
    mensajeBackend.value = datos.mensaje
  } catch (error) {
    mensajeBackend.value = 'Error de conexión. ¿Está Flask encendido en la otra terminal?'
    console.error(error)
  }
}
</script>

<template>
  <main class="contenedor">
    <h1>GastoGenie 🧞‍♂️</h1>
    <p>Prueba de conexión local</p>
    
    <button @click="conectarBackend">
      Conectar con Flask
    </button>

    <div v-if="mensajeBackend" class="resultado">
      {{ mensajeBackend }}
    </div>
  </main>
</template>

<style scoped>
.contenedor {
  text-align: center;
  padding: 3rem;
  font-family: system-ui, sans-serif;
}
button {
  padding: 12px 24px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  background-color: #42b883; /* Verde característico de Vue */
  color: white;
  border: none;
  border-radius: 8px;
  transition: background-color 0.2s;
}
button:hover {
  background-color: #33a06f;
}
.resultado {
  margin-top: 24px;
  padding: 16px;
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  color: #2c3e50;
  font-weight: 500;
}
</style>