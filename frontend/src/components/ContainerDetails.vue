<template>
  <div class="container-details">
    <div class="details-header">
      <button @click="$emit('back')" class="btn btn-secondary">← Back</button>
      <div class="header-actions">
        <button 
          v-if="status === 'running'"
          @click="handleStop" 
          class="btn btn-danger"
          :disabled="loading"
        >
          Stop
        </button>
        <button 
          v-else
          @click="handleStart" 
          class="btn btn-success"
          :disabled="loading"
        >
          Start
        </button>
        <button 
          @click="handleRemove" 
          class="btn btn-danger"
          :disabled="loading"
        >
          Remove
        </button>
      </div>
    </div>

    <div v-if="loading && !containerData" class="loading-state">
      <div class="loading"></div>
      <p>Loading container details...</p>
    </div>

    <div v-else-if="containerData" class="details-content">
      <div class="card">
        <h2 class="section-title">Basic Information</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">ID:</span>
            <span class="info-value text-xs">{{ containerId }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Name:</span>
            <span class="info-value">{{ containerName }}</span>
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
            <span class="info-value">{{ stack }}</span>
          </div>
          <div class="info-item" v-if="created">
            <span class="info-label">Created:</span>
            <span class="info-value">{{ created }}</span>
          </div>
          <div class="info-item" v-if="startedAt">
            <span class="info-label">Started At:</span>
            <span class="info-value">{{ startedAt }}</span>
          </div>
        </div>
      </div>

      <div class="card" v-if="networkInfo.length > 0">
        <h2 class="section-title">Network Settings</h2>
        <div class="network-list">
          <div v-for="(net, index) in networkInfo" :key="index" class="network-item">
            <div class="network-header">
              <span class="network-name">{{ net.name }}</span>
              <span v-if="net.ip" class="network-ip">{{ net.ip }}</span>
            </div>
            <div v-if="net.gateway" class="network-detail">
              <span class="detail-label">Gateway:</span>
              <span class="detail-value">{{ net.gateway }}</span>
            </div>
            <div v-if="net.macAddress" class="network-detail">
              <span class="detail-label">MAC Address:</span>
              <span class="detail-value">{{ net.macAddress }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card" v-if="portsList.length > 0">
        <h2 class="section-title">Ports</h2>
        <div class="ports-list">
          <div v-for="(port, index) in portsList" :key="index" class="port-item">
            <div class="port-info">
              <span class="port-label">Container:</span>
              <span class="port-value">{{ port.container }}</span>
            </div>
            <div class="port-info" v-if="port.host">
              <span class="port-label">Host:</span>
              <span class="port-value">{{ port.host }}</span>
            </div>
            <div class="port-info">
              <span class="port-label">Protocol:</span>
              <span class="port-value">{{ port.protocol }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card" v-if="envVars.length > 0">
        <h2 class="section-title">Environment Variables</h2>
        <div class="env-list">
          <div v-for="(env, index) in envVars" :key="index" class="env-item">
            <span class="env-key">{{ getEnvKey(env) }}:</span>
            <span class="env-value">{{ getEnvValue(env) }}</span>
          </div>
        </div>
      </div>

      <div class="card" v-if="labelsList.length > 0">
        <h2 class="section-title">Labels</h2>
        <div class="labels-list">
          <div v-for="(label, index) in labelsList" :key="index" class="label-item">
            <span class="label-key">{{ label.key }}:</span>
            <span class="label-value">{{ label.value }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <h2 class="section-title">Prometheus</h2>
        <PrometheusConfig 
          :container-id="containerId"
          :stack="stack"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { containerApi, type ContainerData } from '../services/api'
import PrometheusConfig from './PrometheusConfig.vue'

const props = defineProps<{
  containerId: string
}>()

const emit = defineEmits<{
  back: []
}>()

const containerData = ref<ContainerData | null>(null)
const loading = ref(false)

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

const created = computed(() => {
  if (containerData.value?.info.Created) {
    return new Date(containerData.value.info.Created).toLocaleString()
  }
  return null
})

const startedAt = computed(() => {
  if (containerData.value?.info.State?.StartedAt) {
    return new Date(containerData.value.info.State.StartedAt).toLocaleString()
  }
  return null
})

const networkInfo = computed(() => {
  const networks = containerData.value?.info.NetworkSettings?.Networks
  if (!networks) return []
  
  return Object.entries(networks).map(([name, data]: [string, any]) => ({
    name,
    ip: data.IPAddress,
    gateway: data.Gateway,
    macAddress: data.MacAddress
  }))
})

const portsList = computed(() => {
  const ports = containerData.value?.info.NetworkSettings?.Ports
  if (!ports) return []
  
  const result: any[] = []
  Object.entries(ports).forEach(([containerPort, hostPorts]: [string, any]) => {
    const [port, protocol] = containerPort.split('/')
    if (hostPorts && hostPorts.length > 0) {
      hostPorts.forEach((hp: any) => {
        result.push({
          container: port,
          host: hp.HostPort,
          protocol: protocol || 'tcp'
        })
      })
    } else {
      result.push({
        container: port,
        host: null,
        protocol: protocol || 'tcp'
      })
    }
  })
  return result
})

const envVars = computed(() => {
  return containerData.value?.info.Config?.Env || []
})

const labelsList = computed(() => {
  const labels = containerData.value?.info.Config?.Labels
  if (!labels) return []
  return Object.entries(labels).map(([key, value]) => ({ key, value }))
})

const statusBadgeClass = computed(() => {
  if (status.value === 'running') return 'badge-success'
  return 'badge-error'
})

const getEnvKey = (env: string): string => {
  const idx = env.indexOf('=')
  return idx > 0 ? env.substring(0, idx) : env
}

const getEnvValue = (env: string): string => {
  const idx = env.indexOf('=')
  return idx > 0 ? env.substring(idx + 1) : ''
}

const loadContainer = async () => {
  loading.value = true
  try {
    const containers = await containerApi.getContainers()
    containerData.value = containers[props.containerId] || null
  } catch (error: any) {
    console.error('Failed to load container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to load container details'
    alert(errorMsg)
  } finally {
    loading.value = false
  }
}

const handleStart = async () => {
  loading.value = true
  try {
    const result = await containerApi.startContainer(props.containerId)
    console.log('Start result:', result)
    await loadContainer()
  } catch (error: any) {
    console.error('Failed to start container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to start container'
    alert(errorMsg)
  } finally {
    loading.value = false
  }
}

const handleStop = async () => {
  loading.value = true
  try {
    const result = await containerApi.stopContainer(props.containerId)
    console.log('Stop result:', result)
    await loadContainer()
  } catch (error: any) {
    console.error('Failed to stop container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to stop container'
    alert(errorMsg)
  } finally {
    loading.value = false
  }
}

const handleRemove = async () => {
  if (!confirm('Are you sure you want to remove this container?')) {
    return
  }
  loading.value = true
  try {
    const result = await containerApi.removeContainer(props.containerId)
    console.log('Remove result:', result)
    emit('back')
  } catch (error: any) {
    console.error('Failed to remove container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to remove container'
    alert(errorMsg)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadContainer()
})
</script>

<style scoped>
.container-details {
  padding: 20px 0;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.details-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 8px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
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
  word-break: break-all;
  overflow-wrap: break-word;
}

.info-value.text-xs {
  font-family: 'Courier New', monospace;
  word-break: break-all;
  overflow-wrap: break-word;
  max-width: 100%;
}

.network-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.network-item {
  padding: 12px;
  background-color: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--border);
}

.network-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.network-name {
  font-weight: 600;
  color: var(--text-primary);
}

.network-ip {
  font-family: 'Courier New', monospace;
  color: var(--accent);
  font-size: 14px;
}

.network-detail {
  display: flex;
  gap: 8px;
  font-size: 13px;
  margin-top: 4px;
}

.detail-label {
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
}

.ports-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.port-item {
  padding: 12px;
  background-color: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--border);
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.port-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.port-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.port-value {
  font-size: 14px;
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
  font-weight: 500;
}

.env-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.env-item {
  padding: 10px 12px;
  background-color: var(--bg-primary);
  border-radius: 6px;
  font-size: 13px;
  border: 1px solid var(--border);
  display: flex;
  gap: 8px;
}

.env-key {
  color: var(--accent);
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

.env-value {
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
  word-break: break-all;
}

.labels-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label-item {
  padding: 10px 12px;
  background-color: var(--bg-primary);
  border-radius: 6px;
  font-size: 13px;
  border: 1px solid var(--border);
  display: flex;
  gap: 8px;
}

.label-key {
  color: var(--accent);
  font-weight: 500;
}

.label-value {
  color: var(--text-primary);
  word-break: break-all;
}

.loading-state {
  text-align: center;
  padding: 60px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: var(--text-secondary);
}
</style>
