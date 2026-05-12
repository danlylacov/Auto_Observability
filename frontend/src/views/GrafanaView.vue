<template>
  <div class="grafana-view">
    <div class="header-section">
      <div>
        <h1 class="page-title">Grafana Dashboards</h1>
      </div>
      <div class="header-actions">
        <button @click="loadAll" class="btn btn-primary" :disabled="isLoadingAny">
          <span v-if="isLoadingAny" class="loading"></span>
          <span v-else>Refresh</span>
        </button>
      </div>
    </div>

    <div class="manager-panel">
      <div>
        <h2 class="panel-title-inline">Grafana Manager</h2>
        <p v-if="managerStatusText" class="manager-status-line">
          Status:
          <span class="badge" :class="managerStatusBadgeClass">{{ managerStatusText }}</span>
        </p>
      </div>
      <div class="manager-controls">
        <button @click="refreshManagerStatus" class="btn btn-secondary" :disabled="loadingManager">
          <span v-if="loadingManager" class="loading"></span>
          <span v-else>Refresh Status</span>
        </button>
        <button
          v-if="isManagerRunning"
          @click="stopManager"
          class="btn btn-danger"
          :disabled="loadingManager"
        >
          <span v-if="loadingManager" class="loading"></span>
          <span v-else>Stop Grafana</span>
        </button>
        <button
          v-else
          @click="startManager"
          class="btn btn-success"
          :disabled="loadingManager"
        >
          <span v-if="loadingManager" class="loading"></span>
          <span v-else>Start Grafana</span>
        </button>
        <button
          @click="restartManager"
          class="btn btn-warning"
          :disabled="loadingManager"
        >
          <span v-if="loadingManager" class="loading"></span>
          <span v-else>Restart Grafana</span>
        </button>
        <a v-if="grafanaUiHref" :href="grafanaUiHref" target="_blank" class="btn btn-primary">Open Grafana</a>
      </div>
    </div>

    <div class="content-layout">
      <div class="left-column">
        <div class="table-panel">
          <div class="panel-header">
            <h2 class="panel-title">Available Containers</h2>
          </div>
          <div v-if="loadingEligible && eligible.length === 0" class="loading-state">
            <div class="loading"></div>
            <p>Loading containers...</p>
          </div>
          <div v-else-if="eligible.length === 0" class="empty-state">
            <p>No containers with Prometheus config found</p>
          </div>
          <div v-else class="table-container">
            <table class="config-table">
              <thead>
                <tr>
                  <th>Container</th>
                  <th>Stack</th>
                  <th>Job</th>
                  <th>Exporter</th>
                  <th>In Main Config</th>
                  <th>Ready</th>
                  <th>Dashboard</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in eligible"
                  :key="row.config_id"
                  :id="'grafana-config-' + row.config_id"
                >
                  <td>{{ row.container_name }}</td>
                  <td><span class="badge badge-info">{{ row.stack }}</span></td>
                  <td class="job-name">{{ row.job_name }}</td>
                  <td>
                    <span :class="['badge', row.exporter_running ? 'badge-success' : 'badge-danger']">
                      {{ row.exporter_running ? "Running" : "Stopped" }}
                    </span>
                  </td>
                  <td>
                    <span :class="['badge', row.in_main_config ? 'badge-success' : 'badge-secondary']">
                      {{ row.in_main_config ? "Yes" : "No" }}
                    </span>
                  </td>
                  <td>
                    <span :class="['badge', row.metrics_ready ? 'badge-success' : 'badge-danger']">
                      {{ row.metrics_ready ? "Ready" : "Not ready" }}
                    </span>
                  </td>
                  <td>
                    <span
                      :class="[
                        'badge',
                        row.has_grafana_dashboard ? 'badge-success' : 'badge-secondary'
                      ]"
                    >
                      {{ row.has_grafana_dashboard ? "Yes" : "No" }}
                    </span>
                  </td>
                  <td>
                    <button
                      class="btn btn-sm btn-success"
                      :disabled="
                        importingByConfig[row.config_id] ||
                          !row.metrics_ready ||
                          row.has_grafana_dashboard
                      "
                      :title="
                        row.has_grafana_dashboard
                          ? 'Dashboard already created for this config'
                          : !row.metrics_ready
                            ? 'Exporter must run and job must be in main Prometheus config'
                            : ''
                      "
                      @click="importForContainer(row)"
                    >
                      <span v-if="importingByConfig[row.config_id]" class="loading"></span>
                      <span v-else>Create dashboard</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="right-column">
        <div class="table-panel">
          <div class="panel-header">
            <h2 class="panel-title">Working Dashboards</h2>
          </div>
          <div v-if="loadingImported && imported.length === 0" class="loading-state">
            <div class="loading"></div>
            <p>Loading dashboards...</p>
          </div>
          <div v-else-if="imported.length === 0" class="empty-state">
            <p>No imported dashboards yet</p>
          </div>
          <div v-else class="table-container">
            <table class="config-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Template</th>
                  <th>UID</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in imported" :key="row.id" :id="'grafana-imported-' + row.id">
                  <td>{{ row.title || "-" }}</td>
                  <td>{{ row.template_key || "-" }}</td>
                  <td class="job-name">{{ row.uid }}</td>
                  <td>
                    <div class="action-buttons">
                      <a v-if="openHref(row.url)" class="btn btn-sm btn-primary" :href="openHref(row.url)" target="_blank">
                        Open
                      </a>
                      <button class="btn btn-sm btn-danger" :disabled="deletingById[row.id]" @click="askDelete(row)">
                        <span v-if="deletingById[row.id]" class="loading"></span>
                        <span v-else>Delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="confirmVisible"
      title="Удалить дашборд"
      :message="confirmMessage"
      confirm-text="Удалить"
      type="danger"
      :loading="deleting"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { grafanaApi, type GrafanaEligibleContainer, type GrafanaImportedItem } from '../services/api'
import { emitContainersRefresh } from '../utils/containersRefresh'
import { showToast } from '../utils/toast'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const grafanaUiHref = (
  typeof import.meta.env.VITE_GRAFANA_EXTERNAL_URL === 'string'
    ? import.meta.env.VITE_GRAFANA_EXTERNAL_URL
    : ''
) as string

const route = useRoute()
let grafanaHighlightTimer: ReturnType<typeof setTimeout> | null = null

const eligible = ref<GrafanaEligibleContainer[]>([])
const imported = ref<GrafanaImportedItem[]>([])

const loadingEligible = ref(false)
const loadingImported = ref(false)
const importingByConfig = ref<Record<number, boolean>>({})
const deletingById = ref<Record<number, boolean>>({})
const isLoadingAny = computed(
  () => loadingEligible.value || loadingImported.value
)

const loadingManager = ref(false)
const managerStatus = ref<any>(null)

const confirmVisible = ref(false)
const confirmMessage = ref('')
const deleting = ref(false)
const pendingDelete = ref<GrafanaImportedItem | null>(null)

async function loadImported () {
  loadingImported.value = true
  try {
    imported.value = await grafanaApi.listImported()
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || 'Не удалось загрузить список', 'error')
  } finally {
    loadingImported.value = false
  }
}

async function loadEligible () {
  loadingEligible.value = true
  try {
    eligible.value = await grafanaApi.listEligibleContainers()
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || 'Failed to load eligible containers', 'error')
  } finally {
    loadingEligible.value = false
  }
}

async function loadAll () {
  await Promise.all([loadEligible(), loadImported()])
  await nextTick()
  scrollGrafanaTablesToQuery()
}

async function refreshManagerStatus () {
  loadingManager.value = true
  try {
    managerStatus.value = await grafanaApi.getManagerStatus()
  } catch (e: any) {
    managerStatus.value = null
    showToast(e.response?.data?.detail || e.message || 'Failed to get Grafana status', 'error')
  } finally {
    loadingManager.value = false
  }
}

async function startManager () {
  try {
    loadingManager.value = true
    const result = await grafanaApi.startManager()
    await refreshManagerStatus()
    showToast(result?.message || 'Grafana started', 'success')
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || 'Failed to start Grafana', 'error')
  } finally {
    loadingManager.value = false
  }
}

async function stopManager () {
  try {
    loadingManager.value = true
    const result = await grafanaApi.stopManager()
    await refreshManagerStatus()
    showToast(result?.message || 'Grafana stopped', 'success')
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || 'Failed to stop Grafana', 'error')
  } finally {
    loadingManager.value = false
  }
}

async function restartManager () {
  try {
    loadingManager.value = true
    const result = await grafanaApi.restartManager()
    await refreshManagerStatus()
    showToast(result?.message || 'Grafana restarted', 'success')
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || 'Failed to restart Grafana', 'error')
  } finally {
    loadingManager.value = false
  }
}

const managerStatusText = computed(() => {
  if (!managerStatus.value) return ''
  if (typeof managerStatus.value === 'string') return managerStatus.value
  if (managerStatus.value.status) {
    if (typeof managerStatus.value.status === 'string') return managerStatus.value.status
    if (managerStatus.value.status.status) return managerStatus.value.status.status
  }
  try {
    return JSON.stringify(managerStatus.value)
  } catch {
    return String(managerStatus.value)
  }
})

const isManagerRunning = computed(() => {
  const text = managerStatusText.value.toLowerCase()
  if (!text) return false
  return text.includes('running') || text.includes('up')
})

const managerStatusBadgeClass = computed(() => {
  const text = managerStatusText.value.toLowerCase()
  if (!text) return 'badge-secondary'
  if (text.includes('running') || text.includes('up')) {
    return 'badge-success'
  }
  if (text.includes('not found') || text.includes('down') || text.includes('stopped') || text.includes('exited')) {
    return 'badge-danger'
  }
  return 'badge-secondary'
})

async function importForContainer (row: GrafanaEligibleContainer) {
  if (!row.metrics_ready) {
    showToast('Container is not ready: exporter must be running and metrics must be in main Prometheus config', 'error')
    return
  }
  if (row.has_grafana_dashboard) {
    showToast('Dashboard for this container is already created', 'info')
    return
  }
  importingByConfig.value[row.config_id] = true
  try {
    await grafanaApi.importDashboard({
      prometheus_datasource_uid: 'prometheus',
      instance_suffix: row.container_name.replace(/[^a-zA-Z0-9_-]/g, '-'),
      overwrite: true
    })
    showToast(`Dashboard created for ${row.container_name}`, 'success')
    await loadImported()
    await loadEligible()
    emitContainersRefresh()
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || 'Failed to create dashboard', 'error')
  } finally {
    importingByConfig.value[row.config_id] = false
  }
}

function openHref (relative: string | null) {
  if (!relative || !grafanaUiHref) return ''
  try {
    return new URL(relative, grafanaUiHref.endsWith('/') ? grafanaUiHref : `${grafanaUiHref}/`).href
  } catch {
    return `${grafanaUiHref.replace(/\/$/, '')}${relative.startsWith('/') ? '' : '/'}${relative}`
  }
}

function askDelete (row: GrafanaImportedItem) {
  pendingDelete.value = row
  confirmMessage.value = `Удалить из Grafana и из списка: ${row.title || row.uid}?`
  confirmVisible.value = true
}

function cancelDelete () {
  confirmVisible.value = false
  pendingDelete.value = null
}

async function confirmDelete () {
  const row = pendingDelete.value
  if (!row) return
  deleting.value = true
  deletingById.value[row.id] = true
  try {
    await grafanaApi.deleteImported(row.id)
    showToast('Дашборд удалён', 'success')
    confirmVisible.value = false
    pendingDelete.value = null
    await loadImported()
    await loadEligible()
    emitContainersRefresh()
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || 'Не удалось удалить', 'error')
  } finally {
    deleting.value = false
    deletingById.value[row.id] = false
  }
}

function scrollGrafanaTablesToQuery () {
  const raw = route.query.config_id
  if (raw === undefined || raw === null) return
  const s = Array.isArray(raw) ? raw[0] : raw
  if (!s) return
  const configId = Number(s)
  if (Number.isNaN(configId)) return

  const imp = imported.value.find((i) => i.prometheus_config_id === configId)
  let el: HTMLElement | null = imp ? document.getElementById(`grafana-imported-${imp.id}`) : null
  if (!el) {
    const inEligible = eligible.value.some((e) => e.config_id === configId)
    if (inEligible) {
      el = document.getElementById(`grafana-config-${configId}`)
    }
  }
  if (!el) return

  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.classList.add('grafana-row-highlight')
  if (grafanaHighlightTimer) clearTimeout(grafanaHighlightTimer)
  grafanaHighlightTimer = setTimeout(() => {
    el!.classList.remove('grafana-row-highlight')
    grafanaHighlightTimer = null
  }, 4500)
}

onMounted(() => {
  loadAll()
  refreshManagerStatus()
})

watch(
  () => route.query.config_id,
  () => {
    void nextTick().then(() => scrollGrafanaTablesToQuery())
  }
)
</script>

<style scoped>
.grafana-view {
  padding: 20px;
  max-width: 1800px;
  margin: 0 auto;
}
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}
.header-actions {
  display: flex;
  gap: 10px;
}

.manager-panel {
  margin-bottom: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.panel-title-inline {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: var(--text-primary);
}
.manager-status-line {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}
.manager-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.content-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}
@media (max-width: 1200px) {
  .content-layout {
    grid-template-columns: 1fr;
  }
}
.left-column,
.right-column {
  display: flex;
  flex-direction: column;
}
.table-panel {
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 280px);
}
.input {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
}
.panel-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}
.loading-state,
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
.table-container {
  overflow-x: auto;
  flex: 1;
}
.config-table {
  width: 100%;
  border-collapse: collapse;
}
.config-table thead {
  background: var(--bg-secondary);
  position: sticky;
  top: 0;
  z-index: 10;
}
.config-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.config-table td {
  padding: 12px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.config-table tbody tr:hover {
  background: var(--bg-secondary);
}
.config-table tbody tr.grafana-row-highlight {
  outline: 2px solid var(--accent, #00bcd4);
  outline-offset: 2px;
}
.job-name {
  font-family: monospace;
  font-size: 13px;
}
.action-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}
.badge-success {
  background: var(--success-bg, #d4edda);
  color: var(--success-text, #155724);
}
.badge-secondary {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}
.badge-info {
  background: var(--info-bg, #d1ecf1);
  color: var(--info-text, #0c5460);
}
.badge-danger {
  background: var(--danger-bg, #f8d7da);
  color: var(--danger-text, #721c24);
}
.btn {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  text-decoration: none;
}
.btn:hover:not(:disabled) {
  background: var(--bg-secondary);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: var(--primary-color, #007bff);
  color: white;
  border-color: var(--primary-color, #007bff);
}
.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
}
.btn-success {
  background: var(--success-bg, #28a745);
  color: white;
  border-color: var(--success-bg, #28a745);
}
.btn-danger {
  background: var(--danger-bg, #dc3545);
  color: white;
  border-color: var(--danger-bg, #dc3545);
}
.btn-warning {
  background: var(--warning-bg, #ffc107);
  color: #212529;
  border-color: #ffc107;
}
.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}
.loading {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--border);
  border-top-color: var(--text-primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
