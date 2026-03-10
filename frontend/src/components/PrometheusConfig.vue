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
      <div v-if="error" class="error-message">
        <strong>Error:</strong>
        <p>{{ error }}</p>
        <div v-if="isExporterError" class="error-hint">
          <p><strong>Hint:</strong> Please start the exporter first before generating the config.</p>
        </div>
      </div>
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
import { ref, computed } from 'vue'
import { containerApi } from '../services/api'
import ExporterControl from './ExporterControl.vue'
import { showToast } from '../utils/toast'

const props = defineProps<{
  containerId: string
  stack?: string
  hostId?: string
}>()

const configGenerated = ref(false)
const generating = ref(false)
const error = ref('')
const configInfo = ref<any>(null)

const isExporterError = computed(() => {
  const errorLower = error.value.toLowerCase()
  return errorLower.includes('exporter') && 
         (errorLower.includes('not found') || errorLower.includes('not running'))
})

const handleGenerateConfig = async () => {
  generating.value = true
  error.value = ''
  
  if (!props.hostId) {
    error.value = 'Host ID is required to generate config'
    generating.value = false
    return
  }
  
  try {
    const response = await containerApi.generateConfig(props.containerId, props.hostId)
    if (response.error) {
      error.value = response.error
      showToast(response.error, 'error', 5000)
    } else {
      configGenerated.value = true
      configInfo.value = response.config?.info || response.config_info
      showToast('Prometheus config generated successfully!', 'success')
    }
  } catch (err: any) {
    const errorDetail = err.response?.data?.detail || err.message || 'Failed to generate config'
    error.value = errorDetail
    
    if (errorDetail.toLowerCase().includes('exporter') && 
        (errorDetail.toLowerCase().includes('not found') || errorDetail.toLowerCase().includes('not running'))) {
      showToast('Please start the exporter first before generating config', 'error', 5000)
    } else {
      showToast(errorDetail, 'error', 5000)
    }
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

.error-message strong {
  font-weight: 600;
  display: block;
  margin-bottom: 4px;
}

.error-message p {
  margin: 4px 0;
  line-height: 1.5;
}

.error-hint {
  margin-top: 8px;
  padding: 8px;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  border-left: 3px solid var(--error);
}

.error-hint p {
  margin: 0;
  font-size: 13px;
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

