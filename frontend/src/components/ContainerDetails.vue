<template>
  <div class="container-details">
    <div class="details-header">
      <button type="button" @click="$emit('back')" class="btn btn-secondary back-btn">Back</button>
      <div class="header-actions">
        <button
          v-if="status === 'running'"
          type="button"
          @click="handleStop"
          class="btn btn-danger"
          :disabled="loading || pipelineLoading"
        >
          <span v-if="loading" class="loading"></span>
          <span v-else>Stop</span>
        </button>
        <button
          v-else
          type="button"
          @click="handleStart"
          class="btn btn-success"
          :disabled="loading || pipelineLoading"
        >
          <span v-if="loading" class="loading"></span>
          <span v-else>Start</span>
        </button>
        <button type="button" class="btn btn-danger" :disabled="loading || pipelineLoading" @click="handleRemove">
          Remove
        </button>
      </div>
    </div>

    <div v-if="loading && !containerData" class="loading-state">
      <div class="loading"></div>
      <p>Loading…</p>
    </div>

    <div v-else-if="containerData" class="details-content">
      <section class="panel panel-main">
        <div class="panel-main-row">
          <div>
            <h1 class="title">{{ containerName }}</h1>
            <p class="muted mono">{{ containerId }}</p>
          </div>
          <span :class="['pill', statusBadgeClass]">{{ status }}</span>
        </div>

        <dl class="kv-grid">
          <div v-if="stack" class="kv">
            <dt>Stack</dt>
            <dd><span class="badge badge-info">{{ stack }}</span></dd>
          </div>
          <div v-if="prometheusConfig" class="kv kv-wide">
            <dt>Prometheus</dt>
            <dd class="inline-badges">
              <span
                :class="['badge', prometheusConfig.status === 'active' ? 'badge-success' : 'badge-warning']"
                :title="`Config: ${prometheusConfig.status}`"
              >
                {{ prometheusConfig.status === 'active' ? 'Active' : 'Inactive' }}
              </span>
              <span
                v-if="prometheusConfig.exporter.exists"
                :class="['badge', prometheusConfig.exporter.running ? 'badge-success' : 'badge-error']"
                :title="prometheusConfig.exporter.running ? 'Exporter running' : 'Exporter stopped'"
              >
                {{ prometheusConfig.exporter.running ? 'Exporter running' : 'Exporter stopped' }}
              </span>
              <span v-else class="badge badge-secondary" title="No exporter">Exporter missing</span>
            </dd>
          </div>
          <div class="kv">
            <dt>Image</dt>
            <dd class="mono wrap">{{ image }}</dd>
          </div>
          <div v-if="created" class="kv">
            <dt>Created</dt>
            <dd>{{ created }}</dd>
          </div>
          <div v-if="startedAt" class="kv">
            <dt>Started</dt>
            <dd>{{ startedAt }}</dd>
          </div>
        </dl>
      </section>

      <div class="sections">
        <section v-if="networkInfo.length > 0" class="panel">
          <h2 class="section-heading">Networks</h2>
          <ul class="list-plain">
            <li v-for="(net, index) in networkInfo" :key="index" class="list-item">
              <span class="strong">{{ net.name }}</span>
              <span v-if="net.ip" class="mono muted">{{ net.ip }}</span>
              <span v-if="net.gateway" class="muted">Gateway {{ net.gateway }}</span>
              <span v-if="net.macAddress" class="mono muted">{{ net.macAddress }}</span>
            </li>
          </ul>
        </section>

        <section v-if="portsList.length > 0" class="panel">
          <h2 class="section-heading">Ports</h2>
          <ul class="list-plain">
            <li v-for="(port, index) in portsList" :key="index" class="list-item port-line">
              <span class="mono">{{ port.container }}/{{ port.protocol }}</span>
              <template v-if="port.host">
                <span class="muted">host</span>
                <span class="mono">{{ port.host }}</span>
              </template>
              <span v-else class="muted">Not exposed</span>
            </li>
          </ul>
        </section>

        <section v-if="envVars.length > 0" class="panel">
          <h2 class="section-heading">Environment <span class="count">{{ envVars.length }}</span></h2>
          <div class="scroll-block">
            <div v-for="(env, index) in envVars" :key="index" class="mono-row">
              <span class="accent">{{ getEnvKey(env) }}</span>
              <span class="muted">=</span>
              <span class="wrap">{{ getEnvValue(env) }}</span>
            </div>
          </div>
        </section>

        <section v-if="labelsList.length > 0" class="panel">
          <h2 class="section-heading">Labels <span class="count">{{ labelsList.length }}</span></h2>
          <div class="scroll-block">
            <div v-for="(label, index) in labelsList" :key="index" class="mono-row">
              <span class="accent">{{ label.key }}</span>
              <span class="muted">:</span>
              <span class="wrap">{{ label.value }}</span>
            </div>
          </div>
        </section>

        <section class="panel panel-grafana">
          <h2 class="section-heading">Grafana</h2>
          <div v-if="!prometheusConfig" class="muted">Prometheus config is required before Grafana.</div>
          <div v-else class="grafana-summary">
            <p>
              <span class="muted">Dashboard</span>
              <span :class="['badge', prometheusConfig.has_grafana_dashboard ? 'badge-success' : 'badge-secondary']">
                {{ prometheusConfig.has_grafana_dashboard ? 'Yes' : 'No' }}
              </span>
            </p>
            <p v-if="!prometheusConfig.has_grafana_dashboard" class="muted small">
              Use Start all to register the job in Prometheus and import a dashboard when metrics are ready.
            </p>
          </div>
          <div class="actions-footer">
            <button
              type="button"
              class="btn btn-primary"
              :disabled="pipelineLoading || startAllDisabled || !hostId"
              :title="startAllDisabled ? 'Exporter, active config and dashboard are already set up' : ''"
              @click="handleStartAll"
            >
              <span v-if="pipelineLoading" class="loading"></span>
              <span v-else>Start all</span>
            </button>
          </div>
        </section>
      </div>
    </div>

    <div v-else class="error-state">
      <p>Container not found</p>
      <button type="button" @click="$emit('back')" class="btn btn-primary">Back</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { containerApi, type ContainerData } from '../services/api'
import { showToast } from '../utils/toast'
import { runContainerStartAllPipeline } from '../utils/containerStartAllPipeline'

const props = defineProps<{
  containerId: string
}>()

const emit = defineEmits<{
  back: []
}>()

const containerData = ref<ContainerData | null>(null)
const loading = ref(false)
const pipelineLoading = ref(false)
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
  if (status.value === 'running') return 'pill-running'
  return 'pill-stopped'
})

const startAllDisabled = computed(() => {
  const pc = containerData.value?.prometheus_config
  if (!pc) return false
  return (
    pc.exporter?.running === true &&
    pc.status === 'active' &&
    pc.has_grafana_dashboard === true
  )
})

const getEnvKey = (env: string): string => {
  const idx = env.indexOf('=')
  return idx > 0 ? env.substring(0, idx) : env
}

const getEnvValue = (env: string): string => {
  const idx = env.indexOf('=')
  return idx > 0 ? env.substring(idx + 1) : ''
}

const loadContainer = async (opts?: { silent?: boolean }) => {
  if (!opts?.silent) {
    loading.value = true
  }
  try {
    const containers = await containerApi.getContainers()
    containerData.value = containers[props.containerId] || null
    hostId.value = containerData.value?.host_id || null
  } catch (error: any) {
    console.error('Failed to load container:', error)
    if (!opts?.silent) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to load container details'
      showToast(errorMsg, 'error')
    }
  } finally {
    if (!opts?.silent) {
      loading.value = false
    }
  }
}

const handleStartAll = async () => {
  const h = hostId.value
  const d = containerData.value
  if (!h || !d) {
    showToast('Host ID is not available', 'error')
    return
  }
  const portInput = prompt('Exporter port (default: 9100):', '9100')
  if (portInput === null) {
    return
  }
  const trimmed = portInput.trim()
  const exporterPort = trimmed === '' ? 9100 : parseInt(trimmed, 10)
  if (Number.isNaN(exporterPort) || exporterPort < 1024 || exporterPort > 65535) {
    showToast('Invalid port. Use 1024–65535.', 'error')
    return
  }
  const name = d.info.Name?.replace(/^\//, '') || ''
  if (!name) {
    showToast('Container name is missing', 'error')
    return
  }

  pipelineLoading.value = true
  try {
    const result = await runContainerStartAllPipeline({
      containerId: props.containerId,
      hostId: h,
      exporterPort,
      skipUpExporter: d.prometheus_config?.exporter?.running === true,
      reload: loadContainer,
      isExporterRunning: () =>
        containerData.value?.prometheus_config?.exporter?.running === true,
      isGrafanaMetricsReady: () =>
        containerData.value?.prometheus_config?.grafana_metrics_ready === true
    })
    if (result === 'timeout') {
      showToast(
        'Timed out waiting for Prometheus metrics. Check Prometheus and main config.',
        'warning',
        8000
      )
    } else {
      showToast('Start all completed', 'success')
    }
  } catch (error: any) {
    console.error('Start all failed:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Start all failed'
    showToast(errorMsg, 'error')
  } finally {
    pipelineLoading.value = false
  }
}

const handleStart = async () => {
  loading.value = true
  try {
    if (!hostId.value) {
      throw new Error('Host ID is not available for this container')
    }
    await containerApi.startContainer(props.containerId, hostId.value)
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
    await containerApi.stopContainer(props.containerId, hostId.value)
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
  if (!confirm('Remove this container?')) {
    return
  }
  loading.value = true
  try {
    if (!hostId.value) {
      throw new Error('Host ID is not available for this container')
    }
    await containerApi.removeContainer(props.containerId, hostId.value)
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
  padding: 16px 0 32px;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
}

.back-btn {
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.details-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px 18px;
  background: var(--bg-card);
}

.panel-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-main-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0 0 6px;
  line-height: 1.3;
}

.muted {
  color: var(--text-secondary);
  font-size: 13px;
}

.mono {
  font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, monospace;
  font-size: 13px;
}

.wrap {
  word-break: break-word;
}

.pill {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  text-transform: lowercase;
  border: 1px solid var(--border);
  flex-shrink: 0;
}

.pill-running {
  border-color: var(--success);
  color: var(--success);
}

.pill-stopped {
  border-color: var(--error);
  color: var(--error);
}

.kv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px 24px;
  margin: 0;
}

.kv {
  margin: 0;
}

.kv-wide {
  grid-column: 1 / -1;
}

.kv dt {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.kv dd {
  margin: 0;
  font-size: 14px;
}

.inline-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-heading {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.count {
  font-weight: 500;
  color: var(--text-primary);
}

.list-plain {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.list-item {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: baseline;
  font-size: 14px;
}

.port-line {
  border-bottom: 1px solid var(--border-light, #404040);
  padding-bottom: 8px;
}

.port-line:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.strong {
  font-weight: 600;
}

.scroll-block {
  max-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mono-row {
  font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, monospace;
  font-size: 12px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-primary);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: baseline;
}

.accent {
  color: var(--accent);
  flex-shrink: 0;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 48px 16px;
  color: var(--text-secondary);
}

.error-state {
  color: var(--error);
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

.panel-grafana .grafana-summary p {
  margin: 0 0 8px;
}

.small {
  font-size: 12px;
  line-height: 1.4;
}

.actions-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
</style>
