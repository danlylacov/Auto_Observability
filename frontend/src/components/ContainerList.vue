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
      <button @click="handleRefresh" class="btn btn-primary" :disabled="loading">
        <span v-if="loading" class="loading"></span>
        <span v-else>Refresh</span>
      </button>
    </div>

    <div v-if="loading && !containers.length" class="loading-state">
      <div class="loading"></div>
      <p>Loading containers...</p>
    </div>

    <div v-else-if="filteredContainers.length === 0" class="empty-state">
      <p>No containers found</p>
    </div>

    <div v-else class="table-container">
      <table class="containers-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Image</th>
            <th>Stack</th>
            <th class="id-column">ID</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="[id, data] in filteredContainers" :key="id">
            <td>
              <a @click="viewDetails(id)" class="container-name-link">
                {{ data.info.Name?.replace(/^\//, '') || 'Unknown' }}
              </a>
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
            <td class="text-xs text-gray id-column-cell">{{ id.substring(0, 12) }}</td>
            <td>
              <div class="action-buttons">
                <button 
                  v-if="data.info.State?.Status === 'running'"
                  @click="handleStop(id)" 
                  class="btn btn-sm btn-danger"
                  :disabled="actionLoading === id"
                  title="Stop"
                >
                  <span v-if="actionLoading === id" class="loading"></span>
                  <span v-else>Stop</span>
                </button>
                <button 
                  v-else
                  @click="handleStart(id)" 
                  class="btn btn-sm btn-success"
                  :disabled="actionLoading === id"
                  title="Start"
                >
                  <span v-if="actionLoading === id" class="loading"></span>
                  <span v-else>Start</span>
                </button>
                <button 
                  @click="handleRemove(id)" 
                  class="btn btn-sm btn-danger"
                  :disabled="actionLoading === id"
                  title="Remove"
                >
                  Remove
                </button>
                <button 
                  @click="viewDetails(id)" 
                  class="btn btn-sm btn-primary"
                  title="Details"
                >
                  Details
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { containerApi, type ContainersResponse } from '../services/api'

const router = useRouter()

const containers = ref<ContainersResponse>({})
const loading = ref(false)
const actionLoading = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref('all')

const filteredContainers = computed(() => {
  let filtered = Object.entries(containers.value)

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
    containers.value = await containerApi.getContainers()
  } catch (error: any) {
    console.error('Failed to load containers:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to load containers'
    alert(errorMsg)
  } finally {
    loading.value = false
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
    alert(errorMsg)
  } finally {
    loading.value = false
  }
}

const handleStart = async (id: string) => {
  actionLoading.value = id
  try {
    const result = await containerApi.startContainer(id)
    console.log('Start result:', result)
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to start container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to start container'
    alert(errorMsg)
  } finally {
    actionLoading.value = null
  }
}

const handleStop = async (id: string) => {
  actionLoading.value = id
  try {
    const result = await containerApi.stopContainer(id)
    console.log('Stop result:', result)
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to stop container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to stop container'
    alert(errorMsg)
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
    const result = await containerApi.removeContainer(id)
    console.log('Remove result:', result)
    await loadContainers()
  } catch (error: any) {
    console.error('Failed to remove container:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to remove container'
    alert(errorMsg)
  } finally {
    actionLoading.value = null
  }
}

const viewDetails = (id: string) => {
  router.push(`/container/${id}`)
}

onMounted(() => {
  loadContainers()
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
  max-width: 200px;
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

.action-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
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

.id-column {
  width: 120px;
  min-width: 120px;
  max-width: 120px;
}

.id-column-cell {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'Courier New', monospace;
}
</style>
