<template>
  <div class="exporter-control">
    <div class="control-header">
      <h3 class="control-title">Start Exporter</h3>
    </div>
    
    <div class="control-form">
      <div class="form-group">
        <label class="form-label">Port:</label>
        <input 
          v-model.number="port" 
          type="number" 
          class="input"
          :placeholder="`Default: ${exporterPort}`"
          min="1024"
          max="65535"
        />
      </div>
      
      <button 
        @click="handleStartExporter" 
        class="btn btn-primary"
        :disabled="starting || !port"
      >
        <span v-if="starting" class="loading"></span>
        <span v-else>Start Exporter</span>
      </button>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="exporterInfo" class="exporter-info">
      <div class="success-message">
        <span class="badge badge-success">Exporter Started</span>
      </div>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">Network:</span>
          <span class="info-value">{{ exporterInfo.network }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Stack:</span>
          <span class="info-value">{{ exporterInfo.stack }}</span>
        </div>
        <div class="info-item" v-if="exporterInfo.exporter">
          <span class="info-label">Container ID:</span>
          <span class="info-value text-xs">{{ exporterInfo.exporter.container_id }}</span>
        </div>
      </div>
      <div v-if="exporterInfo.environment" class="env-section">
        <span class="info-label">Environment Variables:</span>
        <pre class="code-block">{{ JSON.stringify(exporterInfo.environment, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { containerApi } from '../services/api'

const props = defineProps<{
  containerId: string
  exporterPort: number
}>()

const port = ref<number>(props.exporterPort)
const starting = ref(false)
const error = ref('')
const exporterInfo = ref<any>(null)

const handleStartExporter = async () => {
  if (!port.value) {
    error.value = 'Please enter a port number'
    return
  }

  starting.value = true
  error.value = ''
  exporterInfo.value = null

  try {
    const response = await containerApi.upExporter(props.containerId, port.value)
    if (response.error) {
      error.value = response.error
    } else {
      exporterInfo.value = response
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to start exporter'
  } finally {
    starting.value = false
  }
}
</script>

<style scoped>
.exporter-control {
  width: 100%;
}

.control-header {
  margin-bottom: 16px;
}

.control-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.control-form {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.error-message {
  color: var(--error);
  font-size: 14px;
  padding: 12px;
  background-color: rgba(244, 67, 54, 0.1);
  border-radius: 6px;
  border: 1px solid var(--error);
  margin-bottom: 16px;
}

.exporter-info {
  margin-top: 16px;
  padding: 16px;
  background-color: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--border);
}

.success-message {
  margin-bottom: 16px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

.env-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.code-block {
  background-color: var(--bg-secondary);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  color: var(--text-primary);
  border: 1px solid var(--border);
  margin-top: 8px;
}
</style>

