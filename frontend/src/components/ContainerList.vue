<template>
  <div class="container-list containers-list-root">
    <div class="toolbar">
      <div class="search-box">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Search containers..." 
          class="input"
        />
      </div>
      <div class="filters">
        <select v-model="statusFilter" class="input" style="width: auto;">
          <option value="all">All</option>
          <option value="running">Running</option>
          <option value="exited">Stopped</option>
        </select>
      </div>
      <div class="filters">
        <select v-model="selectedHostId" class="input" style="width: auto;">
          <option :value="null">All hosts</option>
          <option 
            v-for="host in hosts" 
            :key="host.id" 
            :value="host.id"
          >
            {{ host.name || host.id }}
          </option>
        </select>
      </div>
      <button @click="handleRefresh" class="btn btn-primary" :disabled="loading">
        <span v-if="loading" class="loading"></span>
        <span v-else>Refresh</span>
      </button>
    </div>

    <div class="bulk-strip">
      <template v-if="selectedContainers.size > 0">
        <div class="bulk-actions-info">
          <span class="selected-count">{{ selectedContainers.size }} selected</span>
          <button type="button" @click="clearSelection" class="btn-link">Clear</button>
        </div>
        <div class="bulk-actions-buttons">
          <button
            v-if="canMutateContainers"
            type="button"
            @click="handleBulkStart"
            class="btn btn-sm btn-success"
            :disabled="bulkActionLoading"
          >
            <span v-if="bulkActionLoading" class="loading"></span>
            <span v-else>Start</span>
          </button>
          <button
            v-if="canMutateContainers"
            type="button"
            @click="handleBulkStop"
            class="btn btn-sm btn-danger"
            :disabled="bulkActionLoading"
          >
            <span v-if="bulkActionLoading" class="loading"></span>
            <span v-else>Stop</span>
          </button>
          <button
            v-if="canMutateContainers"
            type="button"
            @click="handleBulkRemove"
            class="btn btn-sm btn-danger"
            :disabled="bulkActionLoading"
          >
            <span v-if="bulkActionLoading" class="loading"></span>
            <span v-else>Remove</span>
          </button>
          <button
            v-if="canMutatePrometheusGrafanaConfig"
            type="button"
            @click="handleBulkGenerateConfig"
            class="btn btn-sm btn-primary"
            :disabled="bulkActionLoading"
          >
            <span v-if="bulkActionLoading" class="loading"></span>
            <span v-else>Generate config</span>
          </button>
          <button
            v-if="canMutatePrometheusGrafanaConfig"
            type="button"
            @click="handleBulkStartExporter"
            class="btn btn-sm btn-success"
            :disabled="bulkActionLoading"
          >
            <span v-if="bulkActionLoading" class="loading"></span>
            <span v-else>Start exporter</span>
          </button>
        </div>
      </template>
      <span v-else class="bulk-placeholder">Select rows with checkboxes for bulk actions</span>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading"></div>
      <p>Loading containers...</p>
    </div>

    <div v-else-if="groupedContainers.length === 0" class="empty-state">
      <p>No containers found</p>
      <p style="font-size: 12px; margin-top: 8px; color: var(--text-secondary);">
        Total containers: {{ Object.keys(containers).length }}, 
        Filtered: {{ filteredContainers.length }}, 
        Groups: {{ groupedContainers.length }}
      </p>
    </div>

    <div v-else class="table-container">
      <div
        v-for="group in groupedContainers"
        :key="group.hostKey"
        class="host-group"
      >
        <div class="host-header">
          <h3 class="host-title">{{ group.hostName }}</h3>
        </div>
        <table class="containers-table">
          <thead>
            <tr>
              <th class="checkbox-column">
                <input 
                  type="checkbox" 
                  :checked="isAllSelectedInGroup(group.items)"
                  @change="toggleSelectAllInGroup(group.items, $event)"
                  class="checkbox"
                />
              </th>
              <th class="col-name">Name</th>
              <th class="col-center">Status</th>
              <th class="col-image">Image</th>
              <th class="col-center">Stack</th>
              <th class="col-center">Config</th>
              <th class="col-center">Exporter</th>
              <th class="col-center">Grafana</th>
              <th class="col-center">Running</th>
              <th class="col-center col-actions">Actions</th>
              <th class="col-center col-links">Links</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="[id, data] in group.items" :key="id">
              <tr>
                <td class="checkbox-column">
                  <input 
                    type="checkbox" 
                    :checked="selectedContainers.has(id)"
                    @change="toggleSelection(id, $event)"
                    class="checkbox"
                  />
                </td>
                <td class="col-name">
                  <div class="container-name-cell">
                    <span 
                      v-if="hasExporter(data)" 
                      class="container-expand-icon"
                      @click="toggleContainerExpansion(id)"
                    >
                      {{ expandedContainers.has(id) ? '▼' : '▶' }}
                    </span>
                    <a @click="viewDetails(id)" class="container-name-link">
                      {{ data.info.Name?.replace(/^\//, '') || 'Unknown' }}
                    </a>
                  </div>
                </td>
              <td class="col-center">
                <span :class="['badge', getStatusBadgeClass(data.info.State?.Status)]">
                  {{ data.info.State?.Status || 'unknown' }}
                </span>
              </td>
              <td class="text-gray col-image cell-image">{{ data.info.Config?.Image || 'Unknown' }}</td>
              <td class="col-center">
                <span v-if="getStack(data.classification)" class="badge badge-info">
                  {{ getStack(data.classification) }}
                </span>
                <span v-else class="text-gray">-</span>
              </td>
              <td class="col-center">
                <span v-if="data.prometheus_config" class="badge badge-success">Yes</span>
                <span v-else class="badge badge-secondary">No</span>
              </td>
              <td class="col-center">
                <span
                  v-if="data.prometheus_config?.exporter?.exists"
                  :class="['badge', data.prometheus_config.exporter.running ? 'badge-success' : 'badge-error']"
                >
                  {{ data.prometheus_config.exporter.running ? 'Running' : 'Stopped' }}
                </span>
                <span v-else-if="data.prometheus_config" class="badge badge-secondary">Missing</span>
                <span v-else class="text-gray">-</span>
              </td>
              <td class="col-center">
                <span
                  v-if="data.prometheus_config"
                  :class="[
                    'badge',
                    data.prometheus_config.has_grafana_dashboard ? 'badge-success' : 'badge-secondary'
                  ]"
                >
                  {{ data.prometheus_config.has_grafana_dashboard ? 'Yes' : 'No' }}
                </span>
                <span v-else class="text-gray">-</span>
              </td>
              <td class="col-center">
                <span
                  v-if="data.prometheus_config"
                  :class="[
                    'badge',
                    isExporterAndGrafanaRunning(data) ? 'badge-success' : 'badge-secondary'
                  ]"
                  title="Exporter running and Grafana dashboard present"
                >
                  {{ isExporterAndGrafanaRunning(data) ? 'Yes' : 'No' }}
                </span>
                <span v-else class="text-gray">-</span>
              </td>
              <td class="col-center col-actions">
                <div class="dropdown-container">
                  <button
                    type="button"
                    class="btn btn-sm btn-secondary dropdown-toggle"
                    :disabled="actionLoading === id"
                    @click.stop="toggleDropdown($event, id)"
                  >
                    <span v-if="actionLoading === id" class="loading"></span>
                    <span v-else>Actions</span>
                  </button>
                  <Teleport to="body">
                    <transition name="dropdown">
                      <div
                        v-if="openDropdowns.has(id)"
                        class="dropdown-menu"
                        :style="
                          dropdownPositions[id]
                            ? {
                                top: dropdownPositions[id].top + 'px',
                                left: dropdownPositions[id].left + 'px'
                              }
                            : {}
                        "
                        @click.stop
                      >
                        <button
                          v-if="canMutateContainers && data.info.State?.Status === 'running'"
                          type="button"
                          class="dropdown-item"
                          :disabled="actionLoading === id"
                          @click="handleStop(id); closeDropdown(id)"
                        >
                          Stop
                        </button>
                        <button
                          v-else-if="canMutateContainers"
                          type="button"
                          class="dropdown-item"
                          :disabled="actionLoading === id"
                          @click="handleStart(id); closeDropdown(id)"
                        >
                          Start
                        </button>
                        <button
                          v-if="canMutateContainers"
                          type="button"
                          class="dropdown-item dropdown-item-danger"
                          :disabled="actionLoading === id"
                          @click="handleRemove(id); closeDropdown(id)"
                        >
                          Remove
                        </button>
                        <div
                          v-if="canMutateContainers && canMutatePrometheusGrafanaConfig"
                          class="dropdown-divider"
                        ></div>
                        <button
                          v-if="canMutatePrometheusGrafanaConfig"
                          type="button"
                          class="dropdown-item"
                          :disabled="actionLoading === id || isGenerateConfigDisabled(data)"
                          @click="handleGenerateConfig(id); closeDropdown(id)"
                        >
                          Generate config
                        </button>
                        <button
                          v-if="canMutatePrometheusGrafanaConfig"
                          type="button"
                          class="dropdown-item"
                          :disabled="actionLoading === id || isStartExporterDisabled(data)"
                          @click="handleStartExporter(id); closeDropdown(id)"
                        >
                          Start exporter
                        </button>
                        <button
                          v-if="canMutatePrometheusGrafanaConfig"
                          type="button"
                          class="dropdown-item"
                          :disabled="actionLoading === id || isStartAllDisabled(data)"
                          :title="startAllButtonTitle(data) || undefined"
                          @click="handleStartAll(id, data); closeDropdown(id)"
                        >
                          Start all
                        </button>
                        <button
                          v-if="canMutatePrometheusGrafanaConfig"
                          type="button"
                          class="dropdown-item"
                          :title="grafanaButtonTitle(data) || undefined"
                          :disabled="actionLoading === id || isCreateGrafanaDisabled(data)"
                          @click="handleCreateGrafanaDashboard(id, data); closeDropdown(id)"
                        >
                          Create Grafana dashboard
                        </button>
                        <div
                          v-if="canMutateContainers || canMutatePrometheusGrafanaConfig"
                          class="dropdown-divider"
                        ></div>
                        <button type="button" class="dropdown-item" @click="viewDetails(id); closeDropdown(id)">
                          Details
                        </button>
                      </div>
                    </transition>
                  </Teleport>
                </div>
              </td>
              <td class="col-center col-links">
                <details
                  v-if="containerExternalLinks(data).length > 0"
                  class="links-details"
                  @click.stop
                >
                  <summary class="links-summary">Links</summary>
                  <div class="links-menu">
                    <a
                      v-for="link in containerExternalLinks(data)"
                      :key="link.label"
                      :href="link.href"
                      class="links-menu-item"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {{ link.label }}
                    </a>
                  </div>
                </details>
                <span v-else class="text-gray">—</span>
              </td>
            </tr>
            <!-- Exporter row under container -->
            <tr 
              v-if="hasExporter(data) && expandedContainers.has(id)" 
              :key="`exporter-${id}`"
              class="exporter-row"
            >
              <td class="checkbox-column"></td>
              <td colspan="10">
                <div class="exporter-details">
                  <div class="exporter-info">
                    <span class="exporter-label">Exporter:</span>
                    <span class="exporter-name">{{ data.prometheus_config.exporter.info?.name || 'Unknown Exporter' }}</span>
                    <span class="exporter-status badge badge-success">Running</span>
                    <span class="exporter-image text-gray">{{ data.prometheus_config.exporter.info?.image || 'Unknown' }}</span>
                  </div>
                  <div class="exporter-actions">
                    <button
                      v-if="canMutatePrometheusGrafanaConfig"
                      @click="handleStopExporter(id, data)"
                      class="btn btn-sm btn-warning"
                      :disabled="actionLoading === data.prometheus_config.exporter.container_id"
                      title="Stop Exporter"
                    >
                      <span v-if="actionLoading === data.prometheus_config.exporter.container_id" class="loading"></span>
                      <span v-else>Stop</span>
                    </button>
                    <button
                      v-if="canMutatePrometheusGrafanaConfig"
                      @click="handleRemoveExporter(id, data)"
                      class="btn btn-sm btn-danger"
                      :disabled="actionLoading === data.prometheus_config.exporter.container_id"
                      title="Remove Exporter"
                    >
                      <span v-if="actionLoading === data.prometheus_config.exporter.container_id" class="loading"></span>
                      <span v-else>Remove</span>
                    </button>
                    <button 
                      @click="viewDetails(id)" 
                      class="btn btn-sm btn-primary"
                      title="View Details"
                    >
                      Details
                    </button>
                  </div>
                </div>
              </td>
            </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
    <ConfirmDialog
      v-if="exporterRemovePending"
      :visible="showExporterRemoveDialog"
      title="Удалить экспортер"
      :message="exporterRemoveDialogMessage"
      :details="exporterRemoveDialogDetails"
      :confirm-text="exporterRemoveDialogConfirmText"
      cancel-text="Отмена"
      type="danger"
      :loading="exporterRemoveDialogLoading"
      @confirm="confirmExporterRemove"
      @cancel="cancelExporterRemove"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  containerApi,
  grafanaApi,
  hostsApi,
  type ContainerData,
  type ContainersResponse,
  type HostInfo
} from '../services/api'
import { showToast } from '../utils/toast'
import { usePermissions } from '../composables/usePermissions'
import ConfirmDialog from './ConfirmDialog.vue'
import { CONTAINERS_REFRESH_EVENT, emitContainersRefresh } from '../utils/containersRefresh'
import { runContainerStartAllPipeline, type ReloadFn } from '../utils/containerStartAllPipeline'

const router = useRouter()
const { canMutateContainers, canMutatePrometheusGrafanaConfig } = usePermissions()

const containers = ref<ContainersResponse>({})
const hosts = ref<HostInfo[]>([])
const loading = ref(false)
const actionLoading = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref('all')
const selectedHostId = ref<string | null>(null)
const selectedContainers = ref<Set<string>>(new Set())
const bulkActionLoading = ref(false)
const openDropdowns = ref<Set<string>>(new Set())
const dropdownPositions = ref<Record<string, { top: number; left: number }>>({})

const showExporterRemoveDialog = ref(false)
const exporterRemoveDialogLoading = ref(false)
const exporterRemovePending = ref<{
  hostId: string
  exporterContainerId: string
  appContainerLabel: string
  grafanaImportedId: number | null
  dashboardLabel: string | null
  hadGrafanaFlag: boolean
} | null>(null)

const exporterRemoveDialogMessage = computed(() => {
  const p = exporterRemovePending.value
  if (!p) return ''
  return `Контейнер экспортера «${p.appContainerLabel}» будет удалён с хоста.`
})

const exporterRemoveDialogDetails = computed(() => {
  const p = exporterRemovePending.value
  if (!p) return undefined
  if (p.grafanaImportedId != null) {
    const lab = p.dashboardLabel ? ` «${p.dashboardLabel}»` : ''
    return `Будет удалён дашборд Grafana${lab} и соответствующая запись импорта.`
  }
  if (p.hadGrafanaFlag) {
    return 'У контейнера отмечен дашборд Grafana, но запись в списке импорта не найдена. При необходимости удалите дашборд вручную в Grafana.'
  }
  return 'Связанного дашборда в списке импорта Grafana не найдено.'
})

const exporterRemoveDialogConfirmText = computed(() =>
  exporterRemovePending.value?.grafanaImportedId != null
    ? 'Удалить экспортер и дашборд'
    : 'Удалить экспортер'
)

/** Absolute Grafana dashboard URL by Prometheus config id (from imported list). */
const importedDashboardUrlByConfigId = ref<Map<number, string>>(new Map())

const prometheusQueryHref = computed(() => {
  const raw = (import.meta.env.VITE_PROMETHEUS_URL as string) || 'http://localhost:9090'
  try {
    const origin = new URL(raw).origin
    return new URL('/query', origin).href
  } catch {
    return 'http://localhost:9090/query'
  }
})

const grafanaExternalBase = computed(() => {
  const g = (import.meta.env.VITE_GRAFANA_EXTERNAL_URL as string) || ''
  return g.replace(/\/$/, '')
})

const toAbsoluteGrafanaUrl = (relativeOrAbsolute: string | null): string => {
  if (!relativeOrAbsolute) return ''
  if (/^https?:\/\//i.test(relativeOrAbsolute)) {
    return relativeOrAbsolute
  }
  const base = grafanaExternalBase.value
  if (!base) return ''
  try {
    return new URL(relativeOrAbsolute, base.endsWith('/') ? base : `${base}/`).href
  } catch {
    return `${base}${relativeOrAbsolute.startsWith('/') ? '' : '/'}${relativeOrAbsolute}`
  }
}

const loadImportedLinksIndex = async () => {
  try {
    const items = await grafanaApi.listImported()
    const m = new Map<number, string>()
    for (const row of items) {
      const pid = row.prometheus_config_id
      if (pid == null || !row.url) continue
      const abs = toAbsoluteGrafanaUrl(row.url)
      if (abs) {
        m.set(pid, abs)
      }
    }
    importedDashboardUrlByConfigId.value = m
  } catch (e) {
    console.error('Failed to load Grafana imported dashboards for links:', e)
  }
}

const containerExternalLinks = (data: ContainerData) => {
  const pc = data.prometheus_config
  if (!pc) return []
  const out: { label: string; href: string }[] = []
  const pq = prometheusQueryHref.value
  if (pq) {
    out.push({ label: 'Prometheus', href: pq })
  }
  if (pc.has_grafana_dashboard) {
    const dash = importedDashboardUrlByConfigId.value.get(pc.config_id)
    if (dash) {
      out.push({ label: 'Grafana', href: dash })
    }
  }
  return out
}

const toggleDropdown = (e: Event, containerId: string) => {
  e.stopPropagation()
  e.preventDefault()
  const button = e.currentTarget as HTMLElement
  const rect = button.getBoundingClientRect()
  setTimeout(() => {
    if (openDropdowns.value.has(containerId)) {
      openDropdowns.value.delete(containerId)
      delete dropdownPositions.value[containerId]
    } else {
      openDropdowns.value.clear()
      openDropdowns.value.add(containerId)
      dropdownPositions.value[containerId] = {
        top: rect.bottom + 4,
        left: rect.right - 200
      }
    }
  }, 0)
}

const closeDropdown = (containerId: string) => {
  openDropdowns.value.delete(containerId)
}

const isExporterContainer = (data: any): boolean => {
  // Check if container is an exporter by name pattern or labels
  const name = data.info?.Name || ''
  const labels = data.info?.Config?.Labels || {}
  
  // Exporter containers typically have names ending with -exporter
  if (name.includes('-exporter') || name.includes('_exporter')) {
    return true
  }
  
  // Check for exporter-related labels
  if (labels['com.docker.compose.service']?.includes('exporter') ||
      labels['exporter'] === 'true' ||
      labels['prometheus.exporter'] === 'true') {
    return true
  }
  
  return false
}

const filteredContainers = computed(() => {
  let filtered = Object.entries(containers.value)
  
  // Filter out exporter containers
  filtered = filtered.filter(([_, data]) => !isExporterContainer(data))

  if (selectedHostId.value) {
    filtered = filtered.filter(([_, data]) => data.host_id === selectedHostId.value)
  }

  if (statusFilter.value !== 'all') {
    filtered = filtered.filter(([_, data]) => {
      const status = data.info.State?.Status?.toLowerCase() || ''
      if (statusFilter.value === 'running') {
        return status === 'running'
      }
      return status !== 'running'
    })
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(([_, data]) => {
      const name = data.info.Name?.toLowerCase() || ''
      const image = data.info.Config?.Image?.toLowerCase() || ''
      return name.includes(query) || image.includes(query)
    })
  }

  return filtered
})

const expandedContainers = ref<Set<string>>(new Set())

const groupedContainers = computed(() => {
  const groups: Record<string, { hostName: string; items: [string, any][] }> = {}

  filteredContainers.value.forEach(([id, data]) => {
    const hostName = data.host_name || 'Unknown host'
    const hostKey = data.host_id || hostName
    if (!groups[hostKey]) {
      groups[hostKey] = {
        hostName,
        items: []
      }
    }
    
    groups[hostKey].items.push([id, data])
  })

  return Object.entries(groups).map(([hostKey, value]) => ({
    hostKey,
    hostName: value.hostName,
    items: value.items
  }))
})

const hasExporter = (data: any): boolean => {
  return !!(data.prometheus_config?.exporter?.running && data.prometheus_config?.exporter?.info)
}

const toggleContainerExpansion = (containerId: string) => {
  const newSet = new Set(expandedContainers.value)
  if (newSet.has(containerId)) {
    newSet.delete(containerId)
  } else {
    newSet.add(containerId)
  }
  expandedContainers.value = newSet
}

const getStack = (classification: any): string | undefined => {
  if (classification?.result && classification.result.length > 0) {
    return classification.result[0][0]
  }
  return undefined
}

const getStatusBadgeClass = (status: string | undefined): string => {
  if (status === 'running') return 'badge-success'
  return 'badge-error'
}

const loadContainers = async (opts?: { silent?: boolean }) => {
  if (!opts?.silent) {
    loading.value = true
  }
  try {
    const data = await containerApi.getContainers(selectedHostId.value || undefined)
    containers.value = data
    console.log('Loaded containers:', Object.keys(data).length, 'containers')
    if (Object.keys(data).length > 0) {
      const firstKey = Object.keys(data)[0]
      console.log('First container sample:', {
        id: firstKey,
        host_id: data[firstKey]?.host_id,
        host_name: data[firstKey]?.host_name,
        name: data[firstKey]?.info?.Name
      })
    }
    // Use nextTick to ensure computed properties are updated
    await new Promise(resolve => setTimeout(resolve, 0))
    console.log('Filtered containers:', filteredContainers.value.length)
    console.log('Grouped containers:', groupedContainers.value.length, 'groups')
    if (groupedContainers.value.length > 0) {
      console.log('First group:', groupedContainers.value[0])
    }
  } catch (error: any) {
    console.error('Failed to load containers:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to load containers'
    if (!opts?.silent) {
      showToast(errorMsg, 'error')
    }
    containers.value = {}
  } finally {
    if (!opts?.silent) {
      loading.value = false
    }
  }
}

const loadHosts = async () => {
  try {
    hosts.value = await hostsApi.getHosts()
  } catch (error: any) {
    console.error('Failed to load hosts:', error)
  }
}

const handleRefresh = async () => {
  loading.value = true
  try {
    await containerApi.updateContainers()
    await loadContainers()
    await loadImportedLinksIndex()
  } catch (error: any) {
    console.error('Failed to refresh containers:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to refresh containers'
    showToast(errorMsg, 'error')
  } finally {
    loading.value = false
  }
}

const handleStart = async (id: string) => {
  actionLoading.value = id
  try {
    const container = containers.value[id]
    const hostId = container?.host_id
    if (!hostId) {
      throw new Error('Host ID is not available for this container')
    }
    const result = await containerApi.startContainer(id, hostId)
    console.log('Start result:', result)
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to start container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to start container'
    showToast(errorMsg, 'error')
  } finally {
    actionLoading.value = null
  }
}

const handleStop = async (id: string) => {
  actionLoading.value = id
  try {
    const container = containers.value[id]
    const hostId = container?.host_id
    if (!hostId) {
      throw new Error('Host ID is not available for this container')
    }
    const result = await containerApi.stopContainer(id, hostId)
    console.log('Stop result:', result)
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to stop container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to stop container'
    showToast(errorMsg, 'error')
  } finally {
    actionLoading.value = null
  }
}

const handleRemove = async (id: string) => {
  if (!confirm('Are you sure you want to remove this container?')) {
    return
  }
  actionLoading.value = id
  try {
    const container = containers.value[id]
    const hostId = container?.host_id
    if (!hostId) {
      throw new Error('Host ID is not available for this container')
    }
    const result = await containerApi.removeContainer(id, hostId)
    console.log('Remove result:', result)
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to remove container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to remove container'
    showToast(errorMsg, 'error')
  } finally {
    actionLoading.value = null
  }
}

const handleStopExporter = async (_containerId: string, containerData: any) => {
  const exporterContainerId = containerData.prometheus_config?.exporter?.container_id || 
                              containerData.prometheus_config?.exporter?.info?.Id
  if (!exporterContainerId) {
    showToast('Exporter container ID not found', 'error')
    return
  }
  
  actionLoading.value = exporterContainerId
  try {
    const hostId = containerData.host_id
    if (!hostId) {
      throw new Error('Host ID is not available')
    }
    await containerApi.stopContainer(exporterContainerId, hostId)
    showToast('Exporter stopped successfully', 'success')
    await containerApi.updateContainers()
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to stop exporter:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to stop exporter'
    showToast(errorMsg, 'error')
  } finally {
    actionLoading.value = null
  }
}

const handleRemoveExporter = async (_containerId: string, containerData: ContainerData) => {
  const pc = containerData.prometheus_config
  const expInfo = pc?.exporter?.info as { Id?: string } | null | undefined
  const exporterContainerId = pc?.exporter?.container_id || expInfo?.Id
  if (!exporterContainerId) {
    showToast('Exporter container ID not found', 'error')
    return
  }
  const hostId = containerData.host_id
  if (!hostId) {
    showToast('Host ID is not available', 'error')
    return
  }

  let grafanaImportedId: number | null = null
  let dashboardLabel: string | null = null
  if (pc?.config_id != null) {
    try {
      const items = await grafanaApi.listImported()
      const row = items.find((i) => i.prometheus_config_id === pc.config_id)
      if (row) {
        grafanaImportedId = row.id
        dashboardLabel = row.title || row.uid || null
      }
    } catch {
      /* dialog still opens with fallback text */
    }
  }

  const appName = containerData.info?.Name?.replace(/^\//, '') || _containerId
  exporterRemovePending.value = {
    hostId,
    exporterContainerId,
    appContainerLabel: appName,
    grafanaImportedId,
    dashboardLabel,
    hadGrafanaFlag: pc?.has_grafana_dashboard === true
  }
  showExporterRemoveDialog.value = true
}

const cancelExporterRemove = () => {
  if (exporterRemoveDialogLoading.value) return
  showExporterRemoveDialog.value = false
  exporterRemovePending.value = null
}

const confirmExporterRemove = async () => {
  const p = exporterRemovePending.value
  if (!p) return
  exporterRemoveDialogLoading.value = true
  actionLoading.value = p.exporterContainerId
  try {
    if (p.grafanaImportedId != null) {
      await grafanaApi.deleteImported(p.grafanaImportedId)
    }
    await containerApi.removeContainer(p.exporterContainerId, p.hostId, true)
    showToast('Exporter removed successfully', 'success')
    await containerApi.updateContainers()
    await loadContainers()
    await loadImportedLinksIndex()
    emitContainersRefresh()
    showExporterRemoveDialog.value = false
    exporterRemovePending.value = null
  } catch (error: any) {
    console.error('Failed to remove exporter:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to remove exporter'
    showToast(errorMsg, 'error')
  } finally {
    exporterRemoveDialogLoading.value = false
    actionLoading.value = null
  }
}

const viewDetails = (id: string) => {
  router.push(`/container/${id}`)
}

const handleGenerateConfig = async (id: string) => {
  actionLoading.value = id
  try {
    const container = containers.value[id]
    const hostId = container?.host_id
    if (!hostId) {
      throw new Error('Host ID is not available for this container')
    }
    await containerApi.generateConfig(id, hostId)
    showToast('Prometheus config generated successfully', 'success')
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to generate config:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to generate config'
    showToast(errorMsg, 'error')
  } finally {
    actionLoading.value = null
  }
}

const handleStartExporter = async (id: string) => {
  const port = prompt('Enter exporter port (default: 9100):', '9100')
  if (!port) return
  
  const exporterPort = parseInt(port)
  if (isNaN(exporterPort) || exporterPort < 1024 || exporterPort > 65535) {
    showToast('Invalid port number. Must be between 1024 and 65535.', 'error')
    return
  }

  actionLoading.value = id
  try {
    await containerApi.upExporter(id, exporterPort)
    showToast('Exporter started successfully', 'success')
    await containerApi.updateContainers()
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to start exporter:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to start exporter'
    showToast(errorMsg, 'error')
  } finally {
    actionLoading.value = null
  }
}

const isStartAllDisabled = (data: ContainerData): boolean => {
  const pc = data.prometheus_config
  if (!pc) return false
  return (
    pc.exporter?.running === true &&
    pc.status === 'active' &&
    pc.has_grafana_dashboard === true
  )
}

const startAllButtonTitle = (data: ContainerData): string => {
  if (isStartAllDisabled(data)) {
    return 'Exporter, active config and Grafana dashboard are already set up'
  }
  return ''
}

const handleStartAll = async (id: string, data: ContainerData) => {
  const hostId = data.host_id
  if (!hostId) {
    showToast('Host ID is not available', 'error')
    return
  }
  const portInput = prompt('Exporter port for Start all (default: 9100):', '9100')
  if (portInput === null) {
    return
  }
  const trimmed = portInput.trim()
  const exporterPort = trimmed === '' ? 9100 : parseInt(trimmed, 10)
  if (Number.isNaN(exporterPort) || exporterPort < 1024 || exporterPort > 65535) {
    showToast('Invalid port. Use 1024–65535.', 'error')
    return
  }
  const name = data.info.Name?.replace(/^\//, '') || ''
  if (!name) {
    showToast('Container name is missing', 'error')
    return
  }

  const reload: ReloadFn = async (_opts?: { silent?: boolean }) => {
    await loadContainers()
    await loadImportedLinksIndex()
  }

  actionLoading.value = id
  try {
    const result = await runContainerStartAllPipeline({
      containerId: id,
      hostId,
      exporterPort,
      skipUpExporter: data.prometheus_config?.exporter?.running === true,
      reload,
      isExporterRunning: () =>
        containers.value[id]?.prometheus_config?.exporter?.running === true,
      isGrafanaMetricsReady: () =>
        containers.value[id]?.prometheus_config?.grafana_metrics_ready === true,
      instanceSuffix: name.replace(/[^a-zA-Z0-9_-]/g, '-')
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
    emitContainersRefresh()
  } catch (error: any) {
    console.error('Start all failed:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Start all failed'
    showToast(errorMsg, 'error')
  } finally {
    actionLoading.value = null
  }
}

const canCreateGrafanaDashboard = (data: ContainerData): boolean => {
  const pc = data.prometheus_config
  if (!pc) return false
  return pc.grafana_metrics_ready === true
}

const isExporterAndGrafanaRunning = (data: ContainerData): boolean => {
  const pc = data.prometheus_config
  if (!pc) return false
  return pc.exporter.running === true && pc.has_grafana_dashboard === true
}

const isGenerateConfigDisabled = (data: ContainerData): boolean => {
  return data.prometheus_config?.status === 'active'
}

const isStartExporterDisabled = (data: ContainerData): boolean => {
  return data.prometheus_config?.exporter?.running === true
}

const isCreateGrafanaDisabled = (data: ContainerData): boolean => {
  if (data.prometheus_config?.has_grafana_dashboard) {
    return true
  }
  return !canCreateGrafanaDashboard(data)
}

const grafanaButtonTitle = (data: ContainerData): string => {
  if (data.prometheus_config?.has_grafana_dashboard) {
    return 'Dashboard already linked'
  }
  if (!canCreateGrafanaDashboard(data)) {
    return 'Wait for metrics (exporter + main Prometheus config)'
  }
  return ''
}

const handleCreateGrafanaDashboard = async (containerId: string, data: ContainerData) => {
  const pc = data.prometheus_config
  if (!pc) {
    showToast('No Prometheus config for this container', 'error')
    return
  }
  if (!canCreateGrafanaDashboard(data)) {
    showToast(
      'Prometheus metrics must be ready: exporter running and job in main Prometheus config',
      'error'
    )
    return
  }
  const name = data.info.Name?.replace(/^\//, '') || ''
  if (!name) {
    showToast('Container name is missing', 'error')
    return
  }
  actionLoading.value = containerId
  try {
    await grafanaApi.importDashboard({
      prometheus_datasource_uid: 'prometheus',
      instance_suffix: name.replace(/[^a-zA-Z0-9_-]/g, '-'),
      overwrite: true
    })
    showToast('Grafana dashboard created', 'success')
    await loadContainers()
    await loadImportedLinksIndex()
    emitContainersRefresh()
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to create Grafana dashboard'
    showToast(errorMsg, 'error')
  } finally {
    actionLoading.value = null
  }
}

const toggleSelection = (id: string, event: Event) => {
  const checked = (event.target as HTMLInputElement).checked
  if (checked) {
    selectedContainers.value.add(id)
  } else {
    selectedContainers.value.delete(id)
  }
}

const clearSelection = () => {
  selectedContainers.value.clear()
}

const isAllSelectedInGroup = (items: [string, any][]) => {
  if (items.length === 0) return false
  return items.every(([id]) => selectedContainers.value.has(id))
}

const toggleSelectAllInGroup = (items: [string, any][], event: Event) => {
  const checked = (event.target as HTMLInputElement).checked
  items.forEach(([id]) => {
    if (checked) {
      selectedContainers.value.add(id)
    } else {
      selectedContainers.value.delete(id)
    }
  })
}

const handleBulkStart = async () => {
  if (selectedContainers.value.size === 0) return
  
  if (!confirm(`Start ${selectedContainers.value.size} container(s)?`)) {
    return
  }

  bulkActionLoading.value = true
  const results = { success: 0, failed: 0, errors: [] as string[] }

  for (const id of selectedContainers.value) {
    try {
      const container = containers.value[id]
      const hostId = container?.host_id
      if (!hostId) {
        results.failed++
        results.errors.push(`${id}: Host ID not available`)
        continue
      }
      await containerApi.startContainer(id, hostId)
      results.success++
    } catch (error: any) {
      results.failed++
      results.errors.push(`${id}: ${error.response?.data?.detail || error.message || 'Failed'}`)
    }
  }

  bulkActionLoading.value = false
  await loadContainers()
  clearSelection()
  
  const message = `Started: ${results.success}, Failed: ${results.failed}${results.errors.length > 0 ? '\n\nErrors:\n' + results.errors.slice(0, 5).join('\n') : ''}`
  showToast(message, results.failed > 0 ? 'warning' : 'success', 7000)
}

const handleBulkStop = async () => {
  if (selectedContainers.value.size === 0) return
  
  if (!confirm(`Stop ${selectedContainers.value.size} container(s)?`)) {
    return
  }

  bulkActionLoading.value = true
  const results = { success: 0, failed: 0, errors: [] as string[] }

  for (const id of selectedContainers.value) {
    try {
      const container = containers.value[id]
      const hostId = container?.host_id
      if (!hostId) {
        results.failed++
        results.errors.push(`${id}: Host ID not available`)
        continue
      }
      await containerApi.stopContainer(id, hostId)
      results.success++
    } catch (error: any) {
      results.failed++
      results.errors.push(`${id}: ${error.response?.data?.detail || error.message || 'Failed'}`)
    }
  }

  bulkActionLoading.value = false
  await loadContainers()
  clearSelection()
  
  const message = `Stopped: ${results.success}, Failed: ${results.failed}${results.errors.length > 0 ? '\n\nErrors:\n' + results.errors.slice(0, 5).join('\n') : ''}`
  showToast(message, results.failed > 0 ? 'warning' : 'success', 7000)
}

const handleBulkRemove = async () => {
  if (selectedContainers.value.size === 0) return
  
  if (!confirm(`Remove ${selectedContainers.value.size} container(s)? This action cannot be undone.`)) {
    return
  }

  bulkActionLoading.value = true
  const results = { success: 0, failed: 0, errors: [] as string[] }

  for (const id of selectedContainers.value) {
    try {
      const container = containers.value[id]
      const hostId = container?.host_id
      if (!hostId) {
        results.failed++
        results.errors.push(`${id}: Host ID not available`)
        continue
      }
      await containerApi.removeContainer(id, hostId)
      results.success++
    } catch (error: any) {
      results.failed++
      results.errors.push(`${id}: ${error.response?.data?.detail || error.message || 'Failed'}`)
    }
  }

  bulkActionLoading.value = false
  await loadContainers()
  clearSelection()
  
  const message = `Removed: ${results.success}, Failed: ${results.failed}${results.errors.length > 0 ? '\n\nErrors:\n' + results.errors.slice(0, 5).join('\n') : ''}`
  showToast(message, results.failed > 0 ? 'warning' : 'success', 7000)
}

const handleBulkGenerateConfig = async () => {
  if (selectedContainers.value.size === 0) return
  
  if (!confirm(`Generate Prometheus config for ${selectedContainers.value.size} container(s)?\n\nNote: Exporters must be running for each container.`)) {
    return
  }

  bulkActionLoading.value = true
  const results = { success: 0, failed: 0, errors: [] as string[], exporterErrors: [] as string[] }

  for (const id of selectedContainers.value) {
    try {
      const container = containers.value[id]
      const hostId = container?.host_id
      if (!hostId) {
        results.failed++
        results.errors.push(`${id}: Host ID not available`)
        continue
      }
      await containerApi.generateConfig(id, hostId)
      results.success++
    } catch (error: any) {
      results.failed++
      const errorDetail = error.response?.data?.detail || error.message || 'Failed'
      const errorMsg = `${id}: ${errorDetail}`
      results.errors.push(errorMsg)
      
      // Track exporter-specific errors separately
      if (errorDetail.toLowerCase().includes('exporter') && 
          (errorDetail.toLowerCase().includes('not found') || errorDetail.toLowerCase().includes('not running'))) {
        const containerName = containers.value[id]?.info?.Name?.replace(/^\//, '') || id.substring(0, 12)
        results.exporterErrors.push(containerName)
      }
    }
  }

  bulkActionLoading.value = false
  await loadContainers()
  clearSelection()
  
  let message = `Config generated: ${results.success}, Failed: ${results.failed}`
  
  if (results.exporterErrors.length > 0) {
    message += `\n\n${results.exporterErrors.length} container(s) need exporter started:\n${results.exporterErrors.slice(0, 5).join(', ')}${results.exporterErrors.length > 5 ? '...' : ''}`
  }
  
  if (results.errors.length > 0 && results.exporterErrors.length === 0) {
    message += `\n\nErrors:\n${results.errors.slice(0, 5).join('\n')}`
  }
  
  showToast(message, results.failed > 0 ? 'warning' : 'success', 8000)
}

const handleBulkStartExporter = async () => {
  if (selectedContainers.value.size === 0) return
  
  const port = prompt(`Enter exporter port (default: 9100):`, '9100')
  if (!port) return
  
  const exporterPort = parseInt(port)
  if (isNaN(exporterPort) || exporterPort < 1024 || exporterPort > 65535) {
    showToast('Invalid port number. Must be between 1024 and 65535.', 'error')
    return
  }

  if (!confirm(`Start exporter for ${selectedContainers.value.size} container(s) on port ${exporterPort}?`)) {
    return
  }

  bulkActionLoading.value = true
  const results = { success: 0, failed: 0, errors: [] as string[] }

  for (const id of selectedContainers.value) {
    try {
      await containerApi.upExporter(id, exporterPort)
      results.success++
    } catch (error: any) {
      results.failed++
      results.errors.push(`${id}: ${error.response?.data?.detail || error.message || 'Failed'}`)
    }
  }

  bulkActionLoading.value = false
  await containerApi.updateContainers()
  await loadContainers()
  clearSelection()
  
  const message = `Exporter started: ${results.success}, Failed: ${results.failed}${results.errors.length > 0 ? '\n\nErrors:\n' + results.errors.slice(0, 5).join('\n') : ''}`
  showToast(message, results.failed > 0 ? 'warning' : 'success', 7000)
}

watch(selectedHostId, () => {
  clearSelection()
  loadContainers()
})

const onContainersRefreshEvent = () => {
  void loadContainers().then(() => loadImportedLinksIndex())
}

onMounted(() => {
  void (async () => {
    await loadHosts()
    await loadContainers()
    await loadImportedLinksIndex()
  })()
  window.addEventListener(CONTAINERS_REFRESH_EVENT, onContainersRefreshEvent)
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    if (!target.closest('.dropdown-container') && !target.closest('.dropdown-menu')) {
      openDropdowns.value.clear()
    }
  })
})

onUnmounted(() => {
  window.removeEventListener(CONTAINERS_REFRESH_EVENT, onContainersRefreshEvent)
})
</script>

<style scoped>
.container-list.containers-list-root {
  padding: 16px 0;
  width: 100%;
  max-width: none;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.search-box {
  flex: 1;
  min-width: 200px;
}

.filters {
  display: flex;
  gap: 8px;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.table-container {
  overflow-x: auto;
  width: 100%;
  background-color: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
}

.containers-table {
  width: 100%;
  min-width: 1240px;
  border-collapse: collapse;
  table-layout: auto;
}

.containers-table thead {
  background-color: var(--bg-secondary);
}

.containers-table th {
  padding: 8px 10px;
  text-align: center;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border);
  vertical-align: middle;
}

.containers-table th.col-name,
.containers-table th.col-image {
  text-align: left;
}

.containers-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  word-break: break-word;
  overflow: visible;
  text-overflow: ellipsis;
  position: relative;
  vertical-align: middle;
}

.containers-table td.col-center {
  text-align: center;
}

.containers-table td.col-name {
  text-align: left;
}

.containers-table td.col-image {
  text-align: left;
  max-width: 280px;
}

.containers-table td.cell-image {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.containers-table tbody tr:hover {
  background-color: var(--bg-secondary);
}

.containers-table tbody tr:last-child td {
  border-bottom: none;
}

.container-name-link {
  color: var(--accent);
  cursor: pointer;
  text-decoration: none;
  font-weight: 500;
}

.container-name-link:hover {
  text-decoration: underline;
}

.dropdown-container {
  position: static;
  display: inline-block;
}

.dropdown-toggle {
  min-width: 88px;
}

.dropdown-menu {
  position: fixed;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 10000;
  min-width: 200px;
  padding: 4px 0;
  margin-top: 4px;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 8px 16px;
  text-align: left;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.dropdown-item:hover:not(:disabled) {
  background: var(--bg-secondary);
}

.dropdown-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dropdown-item-danger {
  color: var(--danger-text, #dc3545);
}

.dropdown-item-danger:hover:not(:disabled) {
  background: var(--danger-bg, rgba(220, 53, 69, 0.1));
}

.dropdown-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.col-links {
  width: 88px;
  min-width: 88px;
}

.links-details {
  position: relative;
  text-align: left;
}

.links-summary {
  list-style: none;
  cursor: pointer;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  user-select: none;
}

.links-summary::-webkit-details-marker {
  display: none;
}

.links-details[open] .links-summary {
  border-color: var(--accent);
}

.links-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  min-width: 140px;
  padding: 4px 0;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  z-index: 20;
}

.links-menu-item {
  display: block;
  padding: 8px 14px;
  font-size: 13px;
  color: var(--accent);
  text-decoration: none;
}

.links-menu-item:hover {
  background: var(--bg-secondary);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-sm .loading {
  width: 14px;
  height: 14px;
  border-width: 2px;
}


.host-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background-color: var(--bg-secondary);
  border-bottom: 2px solid var(--border);
}

.host-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.container-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.container-expand-icon {
  font-size: 12px;
  color: var(--text-secondary);
  width: 16px;
  display: inline-block;
  cursor: pointer;
  user-select: none;
  transition: color 0.2s;
}

.container-expand-icon:hover {
  color: var(--text-primary);
}

.exporter-row {
  background-color: var(--exporter-bg, rgba(59, 130, 246, 0.05));
}

.exporter-row:hover {
  background-color: var(--exporter-hover, rgba(59, 130, 246, 0.1));
}

.exporter-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.exporter-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.exporter-label {
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 13px;
}

.exporter-name {
  font-weight: 500;
  color: var(--text-primary);
}

.exporter-status {
  font-size: 12px;
}

.exporter-image {
  font-size: 12px;
  font-family: monospace;
}

.exporter-actions {
  display: flex;
  gap: 6px;
}

.checkbox-column {
  width: 40px;
  min-width: 40px;
  max-width: 40px;
  text-align: center;
}

.checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--accent);
}

.bulk-strip {
  min-height: 52px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 16px;
  background-color: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
}

.bulk-placeholder {
  font-size: 13px;
  color: var(--text-secondary);
  width: 100%;
  text-align: center;
}

.bulk-actions-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selected-count {
  font-weight: 500;
  color: var(--text-primary);
}

.btn-link {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  text-decoration: underline;
  font-size: 14px;
  padding: 0;
}

.btn-link:hover {
  color: var(--accent);
  opacity: 0.8;
}

.bulk-actions-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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

.text-xs {
  font-size: 11px;
}
</style>


