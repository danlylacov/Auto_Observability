<template>
  <div class="container hosts-view">
    <div class="toolbar">
      <h2 class="title">Hosts</h2>
      <div class="actions">
        <button class="btn btn-secondary" @click="loadHosts" :disabled="loading">
          <span v-if="loading" class="loading"></span>
          <span v-else>Refresh</span>
        </button>
        <button class="btn btn-primary" @click="openCreateForm">
          Add host
        </button>
      </div>
    </div>

    <div v-if="loading && hosts.length === 0" class="loading-state">
      <div class="loading"></div>
      <p>Loading hosts...</p>
    </div>

    <div v-else>
      <table class="hosts-table" v-if="hosts.length > 0">
        <thead>
          <tr>
            <th>Name</th>
            <th>Host</th>
            <th>Port</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="host in hosts" :key="host.id">
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
                <button class="btn btn-sm btn-secondary" @click="editHost(host)">
                  Edit
                </button>
                <button class="btn btn-sm btn-danger" @click="deleteHost(host.id)">
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
import { onMounted, ref } from 'vue'
import { hostsApi, type HostInfo } from '../services/api'
import { showToast } from '../utils/toast'

const hosts = ref<HostInfo[]>([])
const loading = ref(false)
const saving = ref(false)

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


