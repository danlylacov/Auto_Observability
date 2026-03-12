<template>
  <div class="container-list">
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

    <div v-if="selectedContainers.size > 0" class="bulk-actions-bar">
      <div class="bulk-actions-info">
        <span class="selected-count">{{ selectedContainers.size }} container(s) selected</span>
        <button @click="clearSelection" class="btn-link">Clear</button>
      </div>
      <div class="bulk-actions-buttons">
        <button 
          @click="handleBulkStart" 
          class="btn btn-sm btn-success"
          :disabled="bulkActionLoading"
        >
          <span v-if="bulkActionLoading" class="loading"></span>
          <span v-else>Start Selected</span>
        </button>
        <button 
          @click="handleBulkStop" 
          class="btn btn-sm btn-danger"
          :disabled="bulkActionLoading"
        >
          <span v-if="bulkActionLoading" class="loading"></span>
          <span v-else>Stop Selected</span>
        </button>
        <button 
          @click="handleBulkRemove" 
          class="btn btn-sm btn-danger"
          :disabled="bulkActionLoading"
        >
          <span v-if="bulkActionLoading" class="loading"></span>
          <span v-else>Remove Selected</span>
        </button>
        <button 
          @click="handleBulkGenerateConfig" 
          class="btn btn-sm btn-primary"
          :disabled="bulkActionLoading"
        >
          <span v-if="bulkActionLoading" class="loading"></span>
          <span v-else>Generate Config</span>
        </button>
        <button 
          @click="handleBulkStartExporter" 
          class="btn btn-sm btn-success"
          :disabled="bulkActionLoading"
        >
          <span v-if="bulkActionLoading" class="loading"></span>
          <span v-else>Start Exporter</span>
        </button>
      </div>
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
              <th>Name</th>
              <th>Status</th>
              <th>Image</th>
              <th>Stack</th>
              <th>Prometheus</th>
              <th class="config-checkbox-column">In Config</th>
              <th>Actions</th>
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
                <td>
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
              <td>
                <span :class="['badge', getStatusBadgeClass(data.info.State?.Status)]">
                  {{ data.info.State?.Status || 'unknown' }}
                </span>
              </td>
              <td class="text-gray">{{ data.info.Config?.Image || 'Unknown' }}</td>
              <td>
                <span v-if="getStack(data.classification)" class="badge badge-info">
                  {{ getStack(data.classification) }}
                </span>
                <span v-else class="text-gray">-</span>
              </td>
              <td>
                <div v-if="data.prometheus_config" class="prometheus-info">
                  <div class="prometheus-status-row">
                    <span 
                      :class="['badge', data.prometheus_config.status === 'active' ? 'badge-success' : 'badge-warning']"
                      :title="`Config status: ${data.prometheus_config.status}`"
                    >
                      {{ data.prometheus_config.status === 'active' ? '✓ Config' : '⚠ Config' }}
                    </span>
                    <span 
                      v-if="data.prometheus_config.exporter.exists"
                      :class="['badge', data.prometheus_config.exporter.running ? 'badge-success' : 'badge-error']"
                      :title="`Exporter ${data.prometheus_config.exporter.running ? 'running' : 'stopped'}`"
                    >
                      {{ data.prometheus_config.exporter.running ? '✓ Exporter' : '✗ Exporter' }}
                    </span>
                    <span 
                      v-else
                      class="badge badge-secondary"
                      title="Exporter not found"
                    >
                      - Exporter
                    </span>
                  </div>
                  <div v-if="data.prometheus_config.stack" class="prometheus-stack">
                    <span class="text-xs text-gray">{{ data.prometheus_config.stack }}</span>
                  </div>
                </div>
                <span v-else class="text-gray">-</span>
              </td>
              <td class="config-checkbox-column">
                <span 
                  v-if="data.prometheus_config"
                  class="config-indicator config-indicator-success"
                  title="Container has Prometheus config"
                >
                  ✓
                </span>
                <span 
                  v-else
                  class="config-indicator config-indicator-error"
                  title="No Prometheus config"
                >
                  ✗
                </span>
              </td>
              <td>
                <div class="dropdown-container">
                  <button 
                    @click.stop="toggleDropdown($event, id)" 
                    class="btn btn-sm btn-secondary dropdown-toggle"
                    :disabled="actionLoading === id"
                  >
                    <span v-if="actionLoading === id" class="loading"></span>
                    <span v-else>Actions ▼</span>
                  </button>
                  <Teleport to="body">
                    <transition name="dropdown">
                      <div 
                        v-if="openDropdowns.has(id)" 
                        class="dropdown-menu"
                        :style="dropdownPositions[id] ? {
                          top: dropdownPositions[id].top + 'px',
                          left: dropdownPositions[id].left + 'px'
                        } : {}"
                        @click.stop
                      >
                      <button 
                        v-if="data.info.State?.Status === 'running'"
                        @click="handleStop(id); closeDropdown(id)" 
                        class="dropdown-item"
                        :disabled="actionLoading === id"
                      >
                        Stop
                      </button>
                      <button 
                        v-else
                        @click="handleStart(id); closeDropdown(id)" 
                        class="dropdown-item"
                        :disabled="actionLoading === id"
                      >
                        Start
                      </button>
                      <button 
                        @click="handleRemove(id); closeDropdown(id)" 
                        class="dropdown-item dropdown-item-danger"
                        :disabled="actionLoading === id"
                      >
                        Remove
                      </button>
                      <div class="dropdown-divider"></div>
                      <button 
                        @click="handleGenerateConfig(id); closeDropdown(id)" 
                        class="dropdown-item"
                        :disabled="actionLoading === id"
                      >
                        Generate Config
                      </button>
                      <button 
                        @click="handleStartExporter(id); closeDropdown(id)" 
                        class="dropdown-item"
                        :disabled="actionLoading === id"
                      >
                        Start Exporter
                      </button>
                      <div class="dropdown-divider"></div>
                      <button 
                        @click="viewDetails(id); closeDropdown(id)" 
                        class="dropdown-item"
                      >
                        Details
                      </button>
                      </div>
                    </transition>
                  </Teleport>
                </div>
              </td>
            </tr>
            <!-- Exporter row under container -->
            <tr 
              v-if="hasExporter(data) && expandedContainers.has(id)" 
              :key="`exporter-${id}`"
              class="exporter-row"
            >
              <td class="checkbox-column"></td>
              <td colspan="7">
                <div class="exporter-details">
                  <div class="exporter-info">
                    <span class="exporter-label">Exporter:</span>
                    <span class="exporter-name">{{ data.prometheus_config.exporter.info?.name || 'Unknown Exporter' }}</span>
                    <span class="exporter-status badge badge-success">Running</span>
                    <span class="exporter-image text-gray">{{ data.prometheus_config.exporter.info?.image || 'Unknown' }}</span>
                  </div>
                  <div class="exporter-actions">
                    <button 
                      @click="handleStopExporter(id, data)" 
                      class="btn btn-sm btn-warning"
                      :disabled="actionLoading === data.prometheus_config.exporter.container_id"
                      title="Stop Exporter"
                    >
                      <span v-if="actionLoading === data.prometheus_config.exporter.container_id" class="loading"></span>
                      <span v-else>Stop</span>
                    </button>
                    <button 
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { containerApi, hostsApi, type ContainersResponse, type HostInfo } from '../services/api'
import { showToast } from '../utils/toast'

const router = useRouter()

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

const toggleDropdown = (e: Event, containerId: string) => {
  e.stopPropagation()
  e.preventDefault()
  
  const button = e.currentTarget as HTMLElement
  const rect = button.getBoundingClientRect()
  
  // Use setTimeout to prevent immediate closure by document click handler
  setTimeout(() => {
    if (openDropdowns.value.has(containerId)) {
      openDropdowns.value.delete(containerId)
      delete dropdownPositions.value[containerId]
    } else {
      // Close all other dropdowns first
      openDropdowns.value.clear()
      openDropdowns.value.add(containerId)
      // Store position for fixed positioning
      dropdownPositions.value[containerId] = {
        top: rect.bottom + 4,
        left: rect.right - 160 // Align to right edge, accounting for menu width
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

const loadContainers = async () => {
  loading.value = true
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
    showToast(errorMsg, 'error')
    containers.value = {}
  } finally {
    loading.value = false
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

const handleStopExporter = async (containerId: string, containerData: any) => {
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

const handleRemoveExporter = async (containerId: string, containerData: any) => {
  if (!confirm('Are you sure you want to remove this exporter container?')) {
    return
  }
  
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
    await containerApi.removeContainer(exporterContainerId, hostId, true)
    showToast('Exporter removed successfully', 'success')
    await containerApi.updateContainers()
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to remove exporter:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to remove exporter'
    showToast(errorMsg, 'error')
  } finally {
    actionLoading.value = null
  }
}

const viewDetails = (id: string) => {
  router.push(`/container/${id}`)
}

const viewGenerateExporter = (id: string) => {
  router.push(`/container/${id}/generate-exporter`)
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

onMounted(() => {
  loadHosts()
  loadContainers()
  
  // Close dropdowns when clicking outside
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    if (!target.closest('.dropdown-container') && !target.closest('.dropdown-menu')) {
      openDropdowns.value.clear()
    }
  })
})
</script>

<style scoped>
.container-list {
  padding: 16px 0;
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
  background-color: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
}

.containers-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.containers-table thead {
  background-color: var(--bg-secondary);
}

.containers-table th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border);
}

.containers-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  word-break: break-word;
  overflow: visible;
  text-overflow: ellipsis;
  position: relative;
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
  min-width: 80px;
}

.dropdown-menu {
  position: fixed;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 10000;
  min-width: 160px;
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

.config-checkbox-column {
  width: 80px;
  min-width: 80px;
  max-width: 80px;
  text-align: center;
}

.config-indicator {
  font-size: 18px;
  font-weight: bold;
  display: inline-block;
}

.config-indicator-success {
  color: var(--success-text, #28a745);
}

.config-indicator-error {
  color: var(--danger-text, #dc3545);
}

.bulk-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 16px;
  background-color: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
  flex-wrap: wrap;
  gap: 12px;
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

.prometheus-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.prometheus-status-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.prometheus-stack {
  margin-top: 2px;
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


