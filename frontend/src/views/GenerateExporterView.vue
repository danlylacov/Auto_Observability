<template>
  <div class="container generate-exporter-view">
    <div class="header-section">
      <button @click="goBack" class="btn btn-secondary">← Back</button>
      <h1 class="page-title">Generate & Start Exporter</h1>
    </div>

    <div v-if="loading && !containerData" class="loading-state">
      <div class="loading"></div>
      <p>Loading container information...</p>
    </div>

    <div v-else-if="containerData" class="content-section">
      <!-- Container Info Card -->
      <div class="card info-card">
        <h2 class="card-title">Container Information</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">Name:</span>
            <span class="info-value">{{ containerName }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">ID:</span>
            <span class="info-value text-xs">{{ containerId }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Status:</span>
            <span :class="['badge', statusBadgeClass]">{{ status }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Image:</span>
            <span class="info-value">{{ image }}</span>
          </div>
          <div class="info-item" v-if="stack">
            <span class="info-label">Stack:</span>
            <span class="info-value badge badge-info">{{ stack }}</span>
          </div>
        </div>
      </div>

      <!-- If config and exporter exist -->
      <div v-if="hasConfig && exporterRunning" class="card config-card">
        <h2 class="card-title">Prometheus Config & Exporter</h2>
        <p class="card-description">
          Configuration and exporter are already set up for this container.
        </p>
        <div class="action-section">
          <button 
            @click="handleRegenerateConfig" 
            class="btn btn-primary"
            :disabled="regeneratingConfig"
          >
            <span v-if="regeneratingConfig" class="loading"></span>
            <span v-else>Regenerate Config</span>
          </button>
          <button 
            @click="handleStopExporter" 
            class="btn btn-danger"
            :disabled="stoppingExporter"
          >
            <span v-if="stoppingExporter" class="loading"></span>
            <span v-else>Stop Exporter</span>
          </button>
        </div>
        <div v-if="actionError" class="error-box">
          {{ actionError }}
        </div>
        <div v-if="actionSuccess" class="success-box">
          {{ actionSuccess }}
        </div>
      </div>

      <!-- If config exists but exporter not running, or no config -->
      <template v-else>
        <!-- Generate Config Section -->
        <div class="card config-card">
          <h2 class="card-title">Step 1: Generate Prometheus Config</h2>
          <p class="card-description">
            Generate the Prometheus configuration file for this container. This will create the necessary exporter configuration.
          </p>
          <div class="action-section">
            <button 
              @click="handleGenerateConfig" 
              class="btn btn-primary"
              :disabled="generatingConfig || configGenerated"
            >
              <span v-if="generatingConfig" class="loading"></span>
              <span v-else-if="configGenerated">✓ Config Generated</span>
              <span v-else>Generate Config</span>
            </button>
          </div>
          <div v-if="configError" class="error-box">
            {{ configError }}
          </div>
          <div v-if="configData" class="success-box">
            <p>✓ Configuration generated successfully!</p>
            <div class="config-info">
              <div class="info-item">
                <span class="info-label">Config ID:</span>
                <span class="info-value text-xs">{{ configData.config_id }}</span>
              </div>
              <div class="info-item" v-if="configData.config?.info">
                <span class="info-label">Exporter Image:</span>
                <span class="info-value">{{ configData.config.info.exporter_image || 'N/A' }}</span>
              </div>
              <div class="info-item" v-if="configData.config?.info">
                <span class="info-label">Exporter Port:</span>
                <span class="info-value">{{ configData.config.info.exporter_port || 'N/A' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Start Exporter Section -->
        <div class="card exporter-card" :class="{ disabled: !configGenerated }">
          <h2 class="card-title">Step 2: Start Exporter</h2>
          <p class="card-description">
            Start the Prometheus exporter container. Make sure the config is generated first.
          </p>
          <div class="form-section">
            <div class="form-group">
              <label class="form-label">Exporter Port:</label>
              <input 
                v-model.number="exporterPort" 
                type="number" 
                class="input"
                :placeholder="`Default: ${defaultExporterPort}`"
                min="1024"
                max="65535"
                :disabled="!configGenerated || startingExporter"
              />
              <p class="form-hint">Port on the host machine to expose the exporter (1024-65535)</p>
            </div>
            <button 
              @click="handleStartExporter" 
              class="btn btn-success"
              :disabled="!configGenerated || !exporterPort || startingExporter"
            >
              <span v-if="startingExporter" class="loading"></span>
              <span v-else-if="exporterStarted">✓ Exporter Started</span>
              <span v-else>Start Exporter</span>
            </button>
          </div>
          <div v-if="exporterError" class="error-box">
            {{ exporterError }}
          </div>
          <div v-if="exporterInfo" class="success-box">
            <p>✓ Exporter started successfully!</p>
            <div class="exporter-details">
              <div class="info-item">
                <span class="info-label">Network:</span>
                <span class="info-value">{{ exporterInfo.network }}</span>
              </div>
              <div class="info-item" v-if="exporterInfo.stack">
                <span class="info-label">Stack:</span>
                <span class="info-value">{{ exporterInfo.stack }}</span>
              </div>
              <div class="info-item" v-if="exporterInfo.exporter?.container_id">
                <span class="info-label">Exporter Container ID:</span>
                <span class="info-value text-xs">{{ exporterInfo.exporter.container_id }}</span>
              </div>
              <div class="info-item" v-if="exporterInfo.environment">
                <span class="info-label">Environment Variables:</span>
                <pre class="code-block">{{ JSON.stringify(exporterInfo.environment, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <div v-else class="error-state">
      <p>Container not found</p>
      <button @click="goBack" class="btn btn-primary">Go Back</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { containerApi, type ContainerData } from '../services/api'

const router = useRouter()
const route = useRoute()

const containerId = computed(() => route.params.id as string)
const containerData = ref<ContainerData | null>(null)
const loading = ref(false)
const hostId = ref<string | null>(null)

const generatingConfig = ref(false)
const configGenerated = ref(false)
const configError = ref('')
const configData = ref<any>(null)

const startingExporter = ref(false)
const exporterStarted = ref(false)
const exporterError = ref('')
const exporterInfo = ref<any>(null)
const exporterPort = ref<number>(9100)
const defaultExporterPort = ref<number>(9100)

const hasConfig = ref(false)
const exporterRunning = ref(false)
const exporterContainerId = ref<string | null>(null)
const regeneratingConfig = ref(false)
const stoppingExporter = ref(false)
const actionError = ref('')
const actionSuccess = ref('')

const containerName = computed(() => {
  return containerData.value?.info.Name?.replace(/^\//, '') || 'Unknown'
})

const status = computed(() => {
  return containerData.value?.info.State?.Status || 'unknown'
})

const image = computed(() => {
  return containerData.value?.info.Config?.Image || 'Unknown'
})

const stack = computed(() => {
  if (containerData.value?.classification?.result && containerData.value.classification.result.length > 0) {
    return containerData.value.classification.result[0][0]
  }
  return undefined
})

const statusBadgeClass = computed(() => {
  if (status.value === 'running') return 'badge-success'
  return 'badge-error'
})

const checkExporterStatus = async () => {
  if (!containerData.value) return
  
  try {
    const containers = await containerApi.getContainers()
    const name = containerData.value.info?.Name?.replace(/^\//, '') || 'Unknown'
    const exporterName = `${name}-exporter`
    
    for (const [id, data] of Object.entries(containers)) {
      const containerName = data.info?.Name?.replace(/^\//, '') || ''
      if (containerName === exporterName) {
        if (data.info?.State?.Status === 'running') {
          exporterRunning.value = true
          exporterContainerId.value = id
          return
        } else {
          exporterContainerId.value = id
        }
      }
    }
    exporterRunning.value = false
    if (!exporterContainerId.value) {
      exporterContainerId.value = null
    }
  } catch (error) {
    console.error('Failed to check exporter status:', error)
  }
}

const loadContainer = async () => {
  loading.value = true
  try {
    const containers = await containerApi.getContainers()
    containerData.value = containers[containerId.value] || null
    hostId.value = containerData.value?.host_id || null
    
    hasConfig.value = containerData.value?.has_prometheus_config === true
    
    if (hasConfig.value) {
      configGenerated.value = true
      await checkExporterStatus()
    } else {
      configGenerated.value = false
      exporterRunning.value = false
    }
    
    // Try to get default exporter port from config if available
    if (configData.value?.config?.info?.exporter_port) {
      defaultExporterPort.value = configData.value.config.info.exporter_port
      exporterPort.value = configData.value.config.info.exporter_port
    }
  } catch (error: any) {
    console.error('Failed to load container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to load container details'
    alert(errorMsg)
  } finally {
    loading.value = false
  }
}

const handleGenerateConfig = async () => {
  if (!hostId.value) {
    configError.value = 'Host ID is not available for this container'
    return
  }

  generatingConfig.value = true
  configError.value = ''
  configData.value = null
  configGenerated.value = false

  try {
    const result = await containerApi.generateConfig(containerId.value, hostId.value)
    configData.value = result
    configGenerated.value = true
    hasConfig.value = true
    
    // Update default port if available
    if (result.config?.info?.exporter_port) {
      defaultExporterPort.value = result.config.info.exporter_port
      exporterPort.value = result.config.info.exporter_port
    }
    
    await loadContainer()
  } catch (error: any) {
    console.error('Failed to generate config:', error)
    configError.value = error.response?.data?.detail || error.message || 'Failed to generate config'
  } finally {
    generatingConfig.value = false
  }
}

const handleStartExporter = async () => {
  if (!exporterPort.value) {
    exporterError.value = 'Please enter a port number'
    return
  }

  startingExporter.value = true
  exporterError.value = ''
  exporterInfo.value = null
  exporterStarted.value = false

  try {
    const result = await containerApi.upExporter(containerId.value, exporterPort.value)
    if (result.error) {
      exporterError.value = result.error
    } else {
      exporterInfo.value = result
      exporterStarted.value = true
      exporterRunning.value = true
      if (result.exporter?.container_id) {
        exporterContainerId.value = result.exporter.container_id
      }
      
      await containerApi.updateContainers()
      await loadContainer()
    }
  } catch (error: any) {
    console.error('Failed to start exporter:', error)
    exporterError.value = error.response?.data?.detail || error.message || 'Failed to start exporter'
  } finally {
    startingExporter.value = false
  }
}

const handleRegenerateConfig = async () => {
  if (!hostId.value) {
    actionError.value = 'Host ID is not available for this container'
    return
  }

  regeneratingConfig.value = true
  actionError.value = ''
  actionSuccess.value = ''

  try {
    const result = await containerApi.generateConfig(containerId.value, hostId.value)
    actionSuccess.value = 'Configuration regenerated successfully!'
    hasConfig.value = true
    
    if (result.config?.info?.exporter_port) {
      defaultExporterPort.value = result.config.info.exporter_port
      exporterPort.value = result.config.info.exporter_port
    }
    
    setTimeout(() => {
      actionSuccess.value = ''
    }, 3000)
  } catch (error: any) {
    console.error('Failed to regenerate config:', error)
    actionError.value = error.response?.data?.detail || error.message || 'Failed to regenerate config'
  } finally {
    regeneratingConfig.value = false
  }
}

const handleStopExporter = async () => {
  if (!exporterContainerId.value || !hostId.value) {
    actionError.value = 'Exporter container ID or Host ID is not available'
    return
  }

  stoppingExporter.value = true
  actionError.value = ''
  actionSuccess.value = ''

  try {
    await containerApi.stopContainer(exporterContainerId.value, hostId.value)
    actionSuccess.value = 'Exporter stopped successfully!'
    exporterRunning.value = false
    
    await containerApi.updateContainers()
    await loadContainer()
    
    setTimeout(() => {
      actionSuccess.value = ''
    }, 3000)
  } catch (error: any) {
    console.error('Failed to stop exporter:', error)
    actionError.value = error.response?.data?.detail || error.message || 'Failed to stop exporter'
  } finally {
    stoppingExporter.value = false
  }
}

const goBack = () => {
  router.push('/containers')
}

onMounted(() => {
  loadContainer()
})
</script>

<style scoped>
.generate-exporter-view {
  padding: 24px 0;
}

.header-section {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.content-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card {
  background-color: var(--bg-card);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid var(--border);
}

.card.disabled {
  opacity: 0.6;
  pointer-events: none;
}

.card-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.card-description {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 16px 0;
  line-height: 1.5;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
  margin-top: 16px;
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
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  word-break: break-word;
}

.info-value.text-xs {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.action-section {
  margin-top: 16px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.form-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

.error-box {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--error);
  background-color: rgba(244, 67, 54, 0.1);
  color: var(--error);
  font-size: 14px;
}

.success-box {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--success);
  background-color: rgba(76, 175, 80, 0.1);
  color: var(--success);
  font-size: 14px;
}

.success-box p {
  margin: 0 0 12px 0;
  font-weight: 500;
}

.config-info,
.exporter-details {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.code-block {
  background-color: var(--bg-primary);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  color: var(--text-primary);
  border: 1px solid var(--border);
  margin-top: 8px;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 60px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: var(--text-secondary);
}

.error-state {
  color: var(--error);
}
</style>

