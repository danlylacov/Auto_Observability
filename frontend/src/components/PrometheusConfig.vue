<template>
  <div class="prometheus-config">
    <div v-if="!configGenerated" class="config-section">
      <p class="section-description">Generate Prometheus configuration for this container.</p>
      <button 
        @click="handleGenerateConfig" 
        class="btn btn-primary"
        :disabled="generating"
      >
        <span v-if="generating" class="loading"></span>
        <span v-else>Generate Prometheus Config</span>
      </button>
      <p v-if="error" class="error-message">{{ error }}</p>
    </div>

    <div v-else class="config-section">
      <div class="success-message">
        <span class="badge badge-success">Config Generated</span>
      </div>
      
      <div v-if="configInfo" class="config-info">
        <div class="info-item">
          <span class="info-label">Exporter Image:</span>
          <span class="info-value">{{ configInfo.exporter_image }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Exporter Port:</span>
          <span class="info-value">{{ configInfo.exporter_port }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Target Address:</span>
          <span class="info-value">{{ configInfo.target_address }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Job Name:</span>
          <span class="info-value">{{ configInfo.job_name }}</span>
        </div>
      </div>

      <div class="exporter-section">
        <ExporterControl 
          :container-id="containerId"
          :exporter-port="configInfo?.exporter_port || 9090"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { containerApi } from '../services/api'
import ExporterControl from './ExporterControl.vue'

const props = defineProps<{
  containerId: string
  stack?: string
}>()

const configGenerated = ref(false)
const generating = ref(false)
const error = ref('')
const configInfo = ref<any>(null)

const handleGenerateConfig = async () => {
  generating.value = true
  error.value = ''
  try {
    const response = await containerApi.generateConfig(props.containerId)
    if (response.error) {
      error.value = response.error
    } else {
      configGenerated.value = true
      configInfo.value = response.config?.info || response.config_info
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to generate config'
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.prometheus-config {
  width: 100%;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-description {
  color: var(--text-secondary);
  font-size: 14px;
}

.error-message {
  color: var(--error);
  font-size: 14px;
  padding: 12px;
  background-color: rgba(244, 67, 54, 0.1);
  border-radius: 6px;
  border: 1px solid var(--error);
}

.success-message {
  margin-bottom: 8px;
}

.config-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background-color: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--border);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.info-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

.exporter-section {
  margin-top: 16px;
}
</style>

