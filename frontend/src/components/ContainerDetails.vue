<template>
  <div class="container-details">
    <!-- Header Section -->
    <div class="details-header">
      <button @click="$emit('back')" class="btn btn-secondary back-btn">← Back</button>
      <div class="header-actions">
        <button 
          v-if="status === 'running'"
          @click="handleStop" 
          class="btn btn-danger"
          :disabled="loading"
        >
          <span v-if="loading" class="loading"></span>
          <span v-else>Stop Container</span>
        </button>
        <button 
          v-else
          @click="handleStart" 
          class="btn btn-success"
          :disabled="loading"
        >
          <span v-if="loading" class="loading"></span>
          <span v-else>Start Container</span>
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
      <!-- Hero Card -->
      <div class="card hero-card">
        <div class="hero-header">
          <div class="hero-title-section">
            <h1 class="hero-title">{{ containerName }}</h1>
            <span :class="['status-badge', statusBadgeClass]">
              <span class="status-dot"></span>
              {{ status }}
            </span>
          </div>
          <div class="hero-meta">
            <div class="meta-item" v-if="stack">
              <span class="meta-label">Stack</span>
              <span class="meta-value badge badge-info">{{ stack }}</span>
            </div>
            <div class="meta-item" v-if="prometheusConfig">
              <span class="meta-label">Prometheus</span>
              <div class="prometheus-meta-values">
                <span 
                  :class="['badge', prometheusConfig.status === 'active' ? 'badge-success' : 'badge-warning']"
                  :title="`Config status: ${prometheusConfig.status}`"
                >
                  {{ prometheusConfig.status === 'active' ? '✓ Config' : '⚠ Config' }}
                </span>
                <span 
                  v-if="prometheusConfig.exporter.exists"
                  :class="['badge', prometheusConfig.exporter.running ? 'badge-success' : 'badge-error']"
                  :title="`Exporter ${prometheusConfig.exporter.running ? 'running' : 'stopped'}`"
                >
                  {{ prometheusConfig.exporter.running ? '✓ Exporter' : '✗ Exporter' }}
                </span>
                <span 
                  v-else
                  class="badge badge-secondary"
                  title="Exporter not found"
                >
                  - Exporter
                </span>
              </div>
            </div>
            <div class="meta-item">
              <span class="meta-label">Container ID</span>
              <span class="meta-value text-xs">{{ containerId }}</span>
            </div>
          </div>
        </div>
        <div class="hero-info">
          <div class="info-row">
            <div class="info-cell">
              <span class="info-icon">📦</span>
              <div class="info-content">
                <span class="info-label">Image</span>
                <span class="info-value">{{ image }}</span>
              </div>
            </div>
            <div class="info-cell" v-if="created">
              <span class="info-icon">🕒</span>
              <div class="info-content">
                <span class="info-label">Created</span>
                <span class="info-value">{{ created }}</span>
              </div>
            </div>
            <div class="info-cell" v-if="startedAt">
              <span class="info-icon">▶️</span>
              <div class="info-content">
                <span class="info-label">Started At</span>
                <span class="info-value">{{ startedAt }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Content Grid -->
      <div class="content-grid">
        <!-- Network Settings -->
        <div class="card section-card" v-if="networkInfo.length > 0">
          <div class="card-header">
            <h2 class="section-title">
              <span class="section-icon">🌐</span>
              Network Settings
            </h2>
          </div>
          <div class="card-body">
            <div class="network-grid">
              <div v-for="(net, index) in networkInfo" :key="index" class="network-card">
                <div class="network-card-header">
                  <span class="network-name">{{ net.name }}</span>
                  <span v-if="net.ip" class="network-ip">{{ net.ip }}</span>
                </div>
                <div class="network-details">
                  <div class="network-detail-item" v-if="net.gateway">
                    <span class="detail-label">Gateway</span>
                    <span class="detail-value">{{ net.gateway }}</span>
                  </div>
                  <div class="network-detail-item" v-if="net.macAddress">
                    <span class="detail-label">MAC Address</span>
                    <span class="detail-value">{{ net.macAddress }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Ports -->
        <div class="card section-card" v-if="portsList.length > 0">
          <div class="card-header">
            <h2 class="section-title">
              <span class="section-icon">🔌</span>
              Port Mappings
            </h2>
          </div>
          <div class="card-body">
            <div class="ports-grid">
              <div v-for="(port, index) in portsList" :key="index" class="port-card">
                <div class="port-main">
                  <span class="port-number">{{ port.container }}</span>
                  <span class="port-protocol">{{ port.protocol.toUpperCase() }}</span>
                </div>
                <div class="port-mapping" v-if="port.host">
                  <span class="mapping-label">→</span>
                  <span class="mapping-value">{{ port.host }}</span>
                </div>
                <div class="port-mapping" v-else>
                  <span class="mapping-label">Not exposed</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Environment Variables -->
        <div class="card section-card" v-if="envVars.length > 0">
          <div class="card-header">
            <h2 class="section-title">
              <span class="section-icon">⚙️</span>
              Environment Variables
            </h2>
            <span class="section-count">{{ envVars.length }}</span>
          </div>
          <div class="card-body">
            <div class="env-container">
              <div v-for="(env, index) in envVars" :key="index" class="env-row">
                <span class="env-key">{{ getEnvKey(env) }}</span>
                <span class="env-separator">=</span>
                <span class="env-value">{{ getEnvValue(env) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Labels -->
        <div class="card section-card" v-if="labelsList.length > 0">
          <div class="card-header">
            <h2 class="section-title">
              <span class="section-icon">🏷️</span>
              Labels
            </h2>
            <span class="section-count">{{ labelsList.length }}</span>
          </div>
          <div class="card-body">
            <div class="labels-container">
              <div v-for="(label, index) in labelsList" :key="index" class="label-row">
                <span class="label-key">{{ label.key }}</span>
                <span class="label-separator">:</span>
                <span class="label-value">{{ label.value }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="error-state">
      <p>Container not found</p>
      <button @click="$emit('back')" class="btn btn-primary">Go Back</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { containerApi, type ContainerData } from '../services/api'
import { showToast } from '../utils/toast'

const props = defineProps<{
  containerId: string
}>()

const emit = defineEmits<{
  back: []
}>()

const containerData = ref<ContainerData | null>(null)
const loading = ref(false)
const hostId = ref<string | null>(null)

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

const hasPrometheusConfig = computed(() => {
  return containerData.value?.has_prometheus_config === true
})

const prometheusConfig = computed(() => {
  return containerData.value?.prometheus_config || null
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
  if (status.value === 'running') return 'status-running'
  return 'status-stopped'
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
    hostId.value = containerData.value?.host_id || null
  } catch (error: any) {
    console.error('Failed to load container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to load container details'
    showToast(errorMsg, 'error')
  } finally {
    loading.value = false
  }
}

const handleStart = async () => {
  loading.value = true
  try {
    if (!hostId.value) {
      throw new Error('Host ID is not available for this container')
    }
    const result = await containerApi.startContainer(props.containerId, hostId.value)
    console.log('Start result:', result)
    await loadContainer()
  } catch (error: any) {
    console.error('Failed to start container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to start container'
    showToast(errorMsg, 'error')
  } finally {
    loading.value = false
  }
}

const handleStop = async () => {
  loading.value = true
  try {
    if (!hostId.value) {
      throw new Error('Host ID is not available for this container')
    }
    const result = await containerApi.stopContainer(props.containerId, hostId.value)
    console.log('Stop result:', result)
    await loadContainer()
  } catch (error: any) {
    console.error('Failed to stop container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to stop container'
    showToast(errorMsg, 'error')
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
    if (!hostId.value) {
      throw new Error('Host ID is not available for this container')
    }
    const result = await containerApi.removeContainer(props.containerId, hostId.value)
    console.log('Remove result:', result)
    emit('back')
  } catch (error: any) {
    console.error('Failed to remove container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to remove container'
    showToast(errorMsg, 'error')
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
  padding: 24px 0;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  gap: 16px;
  flex-wrap: wrap;
}

.back-btn {
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.details-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Hero Card */
.hero-card {
  background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
  border: 1px solid var(--border);
  padding: 32px;
}

.hero-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 24px;
  flex-wrap: wrap;
}

.hero-title-section {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.2;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  text-transform: capitalize;
}

.status-badge .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-running {
  background-color: rgba(76, 175, 80, 0.15);
  color: var(--success);
  border: 1px solid var(--success);
}

.status-running .status-dot {
  background-color: var(--success);
}

.status-stopped {
  background-color: rgba(244, 67, 54, 0.15);
  color: var(--error);
  border: 1px solid var(--error);
}

.status-stopped .status-dot {
  background-color: var(--error);
}

.hero-meta {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-end;
}

.meta-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.meta-label {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.meta-value {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}

.prometheus-meta-values {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.badge-secondary {
  background-color: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.badge-warning {
  background-color: #f59e0b;
  color: white;
}

.hero-info {
  padding-top: 24px;
  border-top: 1px solid var(--border);
}

.info-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
}

.info-cell {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.info-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.info-content .info-label {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-content .info-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  word-break: break-word;
}

/* Content Grid */
.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
}

.section-card {
  padding: 0;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
  background-color: var(--bg-secondary);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-icon {
  font-size: 20px;
}

.section-count {
  font-size: 12px;
  color: var(--text-secondary);
  background-color: var(--bg-primary);
  padding: 4px 10px;
  border-radius: 12px;
}

.card-body {
  padding: 24px;
}

/* Network Grid */
.network-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.network-card {
  padding: 16px;
  background-color: var(--bg-primary);
  border-radius: 8px;
  border: 1px solid var(--border);
  transition: all 0.2s;
}

.network-card:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 8px rgba(0, 188, 212, 0.1);
}

.network-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.network-name {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 15px;
}

.network-ip {
  font-family: 'Courier New', monospace;
  color: var(--accent);
  font-size: 14px;
  font-weight: 500;
}

.network-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.network-detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.detail-label {
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
  font-weight: 500;
}

/* Ports Grid */
.ports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.port-card {
  padding: 16px;
  background-color: var(--bg-primary);
  border-radius: 8px;
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s;
}

.port-card:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 8px rgba(0, 188, 212, 0.1);
}

.port-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.port-number {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
}

.port-protocol {
  font-size: 11px;
  color: var(--text-secondary);
  background-color: var(--bg-secondary);
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.port-mapping {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.mapping-label {
  color: var(--text-secondary);
}

.mapping-value {
  color: var(--accent);
  font-family: 'Courier New', monospace;
  font-weight: 500;
}

/* Environment Variables */
.env-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.env-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  background-color: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--border);
  font-size: 13px;
  font-family: 'Courier New', monospace;
  transition: all 0.2s;
}

.env-row:hover {
  border-color: var(--accent);
  background-color: var(--bg-secondary);
}

.env-key {
  color: var(--accent);
  font-weight: 500;
  flex-shrink: 0;
}

.env-separator {
  color: var(--text-secondary);
  flex-shrink: 0;
}

.env-value {
  color: var(--text-primary);
  word-break: break-all;
  flex: 1;
}

/* Labels */
.labels-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.label-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  background-color: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--border);
  font-size: 13px;
  transition: all 0.2s;
}

.label-row:hover {
  border-color: var(--accent);
  background-color: var(--bg-secondary);
}

.label-key {
  color: var(--accent);
  font-weight: 500;
  flex-shrink: 0;
}

.label-separator {
  color: var(--text-secondary);
  flex-shrink: 0;
}

.label-value {
  color: var(--text-primary);
  word-break: break-all;
  flex: 1;
}

/* Loading & Error States */
.loading-state,
.error-state {
  text-align: center;
  padding: 80px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  color: var(--text-secondary);
}

.error-state {
  color: var(--error);
}

.error-state p {
  font-size: 18px;
  margin: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .hero-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-meta {
    align-items: flex-start;
  }

  .meta-item {
    align-items: flex-start;
  }

  .info-row {
    grid-template-columns: 1fr;
  }

  .ports-grid {
    grid-template-columns: 1fr;
  }
}
</style>
