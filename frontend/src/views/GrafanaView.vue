<template>
  <div class="grafana-view">
    <div class="header-section">
      <div>
        <h1 class="page-title">Grafana Dashboards</h1>
        <p class="page-subtitle">
          Слева — контейнеры, готовые к созданию дашборда. Справа — уже работающие дашборды.
        </p>
      </div>
      <div class="header-actions">
        <a v-if="grafanaUiHref" :href="grafanaUiHref" target="_blank" class="btn btn-secondary">Open Grafana</a>
        <button @click="loadAll" class="btn btn-primary" :disabled="isLoadingAny">
          <span v-if="isLoadingAny" class="loading"></span>
          <span v-else>Refresh</span>
        </button>
      </div>
    </div>

    <div class="settings-panel">
      <div class="settings-grid">
        <div class="form-group">
          <label for="tmpl">Template</label>
          <select id="tmpl" v-model="selectedTemplate" class="input select">
            <option disabled value="">-- choose template --</option>
            <option v-for="key in templateKeys" :key="key" :value="key">
              {{ key }} (id {{ templates[key]?.dashboard_id ?? "-" }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label for="dsuid">Prometheus datasource UID</label>
          <input id="dsuid" v-model.trim="prometheusDsUid" class="input" type="text" placeholder="prometheus" />
        </div>
        <div class="form-group">
          <label for="prefix">Title prefix (optional)</label>
          <input id="prefix" v-model.trim="titlePrefix" class="input" type="text" placeholder="prod" />
        </div>
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
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in eligible" :key="row.config_id">
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
                    <button
                      class="btn btn-sm btn-success"
                      :disabled="importingByConfig[row.config_id] || !row.metrics_ready || !selectedTemplate"
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
                <tr v-for="row in imported" :key="row.id">
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
import { computed, onMounted, ref } from 'vue'
import { grafanaApi, type GrafanaEligibleContainer, type GrafanaImportedItem } from '../services/api'
import { showToast } from '../utils/toast'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const grafanaUiHref = (
  typeof import.meta.env.VITE_GRAFANA_EXTERNAL_URL === 'string'
    ? import.meta.env.VITE_GRAFANA_EXTERNAL_URL
    : ''
) as string

const templates = ref<Record<string, { dashboard_id?: number }>>({})
const templateKeys = computed(() => Object.keys(templates.value).sort())

const eligible = ref<GrafanaEligibleContainer[]>([])
const imported = ref<GrafanaImportedItem[]>([])
const selectedTemplate = ref('')
const prometheusDsUid = ref('prometheus')
const titlePrefix = ref('')

const loadingTemplates = ref(false)
const loadingEligible = ref(false)
const loadingImported = ref(false)
const importingByConfig = ref<Record<number, boolean>>({})
const deletingById = ref<Record<number, boolean>>({})
const isLoadingAny = computed(
  () => loadingTemplates.value || loadingEligible.value || loadingImported.value
)

const confirmVisible = ref(false)
const confirmMessage = ref('')
const deleting = ref(false)
const pendingDelete = ref<GrafanaImportedItem | null>(null)

async function loadTemplates () {
  loadingTemplates.value = true
  try {
    templates.value = await grafanaApi.getTemplates()
    if (!selectedTemplate.value && templateKeys.value.length) {
      selectedTemplate.value = templateKeys.value[0] || ''
    }
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || 'Не удалось загрузить шаблоны', 'error')
  } finally {
    loadingTemplates.value = false
  }
}

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
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/271fd3c1-b718-4e6d-998e-76e80a8d4de6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'a72628'},body:JSON.stringify({sessionId:'a72628',runId:'pre-fix',hypothesisId:'H4',location:'frontend/src/views/GrafanaView.vue:loadAll',message:'loadAll invoked',data:{selectedTemplate:selectedTemplate.value,prometheusDsUid:prometheusDsUid.value},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  await Promise.all([loadTemplates(), loadEligible(), loadImported()])
}

async function importForContainer (row: GrafanaEligibleContainer) {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/271fd3c1-b718-4e6d-998e-76e80a8d4de6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'a72628'},body:JSON.stringify({sessionId:'a72628',runId:'pre-fix',hypothesisId:'H4',location:'frontend/src/views/GrafanaView.vue:importForContainer',message:'user requested dashboard import',data:{config_id:row.config_id,container_name:row.container_name,job_name:row.job_name,metrics_ready:row.metrics_ready,selectedTemplate:selectedTemplate.value,prometheusDsUid:prometheusDsUid.value},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  if (!row.metrics_ready) {
    showToast('Container is not ready: exporter must be running and metrics must be in main Prometheus config', 'error')
    return
  }
  if (!selectedTemplate.value) {
    showToast('Выберите шаблон', 'error')
    return
  }
  importingByConfig.value[row.config_id] = true
  try {
    await grafanaApi.importDashboard({
      template_key: selectedTemplate.value,
      prometheus_datasource_uid: prometheusDsUid.value || undefined,
      title_prefix: titlePrefix.value || undefined,
      instance_suffix: row.container_name.replace(/[^a-zA-Z0-9_-]/g, '-'),
      overwrite: true
    })
    showToast(`Dashboard created for ${row.container_name}`, 'success')
    await loadImported()
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
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || 'Не удалось удалить', 'error')
  } finally {
    deleting.value = false
    deletingById.value[row.id] = false
  }
}

onMounted(() => {
  loadAll()
})
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
  margin-bottom: 20px;
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
.page-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.settings-panel {
  margin-bottom: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-card);
}
.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(200px, 1fr));
  gap: 12px;
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
  max-height: calc(100vh - 220px);
}
.input {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-group label {
  font-size: 12px;
  color: var(--text-secondary);
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
