<template>
  <div class="container hosts-view">
    <div class="toolbar">
      <h2 class="title">Hosts</h2>
      <div class="actions">
        <button class="btn btn-secondary" @click="loadHosts" :disabled="loading">
          <span v-if="loading" class="loading"></span>
          <span v-else>Refresh</span>
        </button>
        <button v-if="canMutateHosts" class="btn btn-primary" @click="openCreateForm">
          Add host
        </button>
      </div>
    </div>

    <div class="hosts-bulk-strip">
      <template v-if="selectedHostIds.size > 0 && canMutateHosts">
        <div class="bulk-info">
          <span>{{ selectedHostIds.size }} selected</span>
          <button type="button" class="btn-link" @click="clearHostSelection">Clear</button>
        </div>
        <button
          type="button"
          class="btn btn-sm btn-danger"
          :disabled="bulkHostsLoading"
          @click="bulkDeleteHosts"
        >
          <span v-if="bulkHostsLoading" class="loading"></span>
          <span v-else>Delete selected</span>
        </button>
      </template>
      <span v-else class="bulk-placeholder">Select hosts with checkboxes to delete in bulk</span>
    </div>

    <div v-if="loading && hosts.length === 0" class="loading-state">
      <div class="loading"></div>
      <p>Loading hosts...</p>
    </div>

    <div v-else>
      <table class="hosts-table" v-if="hosts.length > 0">
        <thead>
          <tr>
            <th class="checkbox-column">
              <input
                type="checkbox"
                class="checkbox"
                :checked="allHostsSelected"
                @change="toggleSelectAllHosts"
              />
            </th>
            <th>Name</th>
            <th>Host</th>
            <th>Port</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="host in hosts" :key="host.id">
            <td class="checkbox-column">
              <input
                type="checkbox"
                class="checkbox"
                :checked="selectedHostIds.has(host.id)"
                @change="toggleHostSelection(host.id, $event)"
              />
            </td>
            <td>{{ host.name || '-' }}</td>
            <td>{{ host.host }}</td>
            <td>{{ host.port }}</td>
            <td>
              <span
                v-if="host.status"
                :class="['badge', host.status === 200 ? 'badge-success' : 'badge-error']"
              >
                {{ host.status === 200 ? 'up' : 'down' }}
              </span>
              <span v-else class="text-gray">unknown</span>
            </td>
            <td>
              <div class="action-buttons">
                <button
                  v-if="canMutateHosts"
                  class="btn btn-sm btn-secondary"
                  @click="editHost(host)"
                >
                  Edit
                </button>
                <button
                  v-if="canMutateHosts"
                  class="btn btn-sm btn-danger"
                  @click="deleteHost(host.id)"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-else class="empty-state">
        <p>No hosts yet. Add first host.</p>
      </div>
    </div>

    <!-- Simple host form -->
    <div v-if="showForm" class="modal-backdrop">
      <div class="modal">
        <h3 class="modal-title">
          {{ editingHost ? 'Edit host' : 'Add host' }}
        </h3>

        <div class="form-group">
          <label for="name">Name</label>
          <input id="name" v-model="form.name" class="input" type="text" />
        </div>

        <div class="form-group">
          <label for="host">Host</label>
          <input id="host" v-model="form.host" class="input" type="text" />
        </div>

        <div class="form-group">
          <label for="port">Port</label>
          <input id="port" v-model.number="form.port" class="input" type="number" />
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeForm">Cancel</button>
          <button class="btn btn-primary" @click="saveHost" :disabled="saving">
            <span v-if="saving" class="loading"></span>
            <span v-else>Save</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { hostsApi, type HostInfo } from '../services/api'
import { showToast } from '../utils/toast'
import { usePermissions } from '../composables/usePermissions'

const { canMutateHosts } = usePermissions()

const hosts = ref<HostInfo[]>([])
const loading = ref(false)
const saving = ref(false)
const selectedHostIds = ref<Set<string>>(new Set())
const bulkHostsLoading = ref(false)

const allHostsSelected = computed(() => {
  if (hosts.value.length === 0) return false
  return hosts.value.every((h) => selectedHostIds.value.has(h.id))
})

const toggleHostSelection = (id: string, event: Event) => {
  const checked = (event.target as HTMLInputElement).checked
  const next = new Set(selectedHostIds.value)
  if (checked) {
    next.add(id)
  } else {
    next.delete(id)
  }
  selectedHostIds.value = next
}

const toggleSelectAllHosts = (event: Event) => {
  const checked = (event.target as HTMLInputElement).checked
  if (checked) {
    selectedHostIds.value = new Set(hosts.value.map((h) => h.id))
  } else {
    selectedHostIds.value = new Set()
  }
}

const clearHostSelection = () => {
  selectedHostIds.value = new Set()
}

const bulkDeleteHosts = async () => {
  if (selectedHostIds.value.size === 0) return
  if (!confirm(`Delete ${selectedHostIds.value.size} host(s)?`)) {
    return
  }
  bulkHostsLoading.value = true
  const ids = [...selectedHostIds.value]
  let failed = 0
  for (const id of ids) {
    try {
      await hostsApi.deleteHost(id)
    } catch (e) {
      failed++
      console.error(e)
    }
  }
  try {
    await hostsApi.refreshHosts()
  } catch {
    /* ignore */
  }
  await loadHosts()
  clearHostSelection()
  bulkHostsLoading.value = false
  if (failed > 0) {
    showToast(`Deleted with ${failed} error(s)`, 'warning')
  } else {
    showToast('Hosts deleted', 'success')
  }
}

const showForm = ref(false)
const editingHost = ref<HostInfo | null>(null)

const form = ref<{
  id?: string
  name: string
  host: string
  port: number | null
}>({
  name: '',
  host: '',
  port: null
})

const loadHosts = async () => {
  loading.value = true
  try {
    const data = await hostsApi.getHosts()
    hosts.value = data
  } catch (error: any) {
    console.error('Failed to load hosts:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to load hosts'
    showToast(msg, 'error')
  } finally {
    loading.value = false
  }
}

const openCreateForm = () => {
  editingHost.value = null
  form.value = {
    name: '',
    host: '',
    port: null
  }
  showForm.value = true
}

const editHost = (host: HostInfo) => {
  editingHost.value = host
  form.value = {
    id: host.id,
    name: host.name || '',
    host: host.host,
    port: host.port
  }
  showForm.value = true
}

const closeForm = () => {
  showForm.value = false
}

const saveHost = async () => {
  if (!form.value.host || !form.value.port) {
    showToast('Host and port are required', 'error')
    return
  }
  saving.value = true
  try {
    if (editingHost.value && form.value.id) {
      await hostsApi.updateHost({
        id: form.value.id,
        name: form.value.name,
        host: form.value.host,
        port: form.value.port
      })
    } else {
      await hostsApi.addHost({
        name: form.value.name,
        host: form.value.host,
        port: form.value.port
      })
    }
    await hostsApi.refreshHosts()
    await loadHosts()
    clearHostSelection()
    showForm.value = false
  } catch (error: any) {
    console.error('Failed to save host:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to save host'
    showToast(msg, 'error')
  } finally {
    saving.value = false
  }
}

const deleteHost = async (id: string) => {
  if (!confirm('Delete this host?')) {
    return
  }
  try {
    await hostsApi.deleteHost(id)
    await hostsApi.refreshHosts()
    await loadHosts()
    const sel = new Set(selectedHostIds.value)
    sel.delete(id)
    selectedHostIds.value = sel
  } catch (error: any) {
    console.error('Failed to delete host:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to delete host'
    showToast(msg, 'error')
  }
}

onMounted(() => {
  loadHosts()
})
</script>

<style scoped>
.hosts-view {
  padding: 16px 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.title {
  font-size: 20px;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 8px;
}

.hosts-bulk-strip {
  min-height: 48px;
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

.bulk-info {
  display: flex;
  align-items: center;
  gap: 12px;
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

.checkbox-column {
  width: 44px;
  min-width: 44px;
  max-width: 44px;
}

.checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--accent);
}

.hosts-table {
  width: 100%;
  border-collapse: collapse;
  background-color: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
  overflow: hidden;
}

.hosts-table th,
.hosts-table td {
  padding: 8px 12px;
  font-size: 14px;
  border-bottom: 1px solid var(--border);
  text-align: center;
  vertical-align: middle;
}

.hosts-table thead {
  background-color: var(--bg-secondary);
}

.hosts-table tbody tr:hover {
  background-color: var(--bg-secondary);
}

.action-buttons {
  display: flex;
  gap: 6px;
  justify-content: center;
  flex-wrap: wrap;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal {
  background: var(--bg-card);
  padding: 20px;
  border-radius: 8px;
  max-width: 400px;
  width: 100%;
  border: 1px solid var(--border);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 13px;
  color: var(--text-secondary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>


