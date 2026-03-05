<template>
  <div class="prometheus-view">
    <div class="header-section">
      <h1 class="page-title">Prometheus Configs</h1>
      <button @click="loadConfigs" class="btn btn-primary" :disabled="loading">
        <span v-if="loading" class="loading"></span>
        <span v-else>Refresh</span>
      </button>
    </div>

    <div v-if="loading && configs.length === 0" class="loading-state">
      <div class="loading"></div>
      <p>Loading configs...</p>
    </div>

    <div v-else-if="configs.length === 0" class="empty-state">
      <p>No Prometheus configs found</p>
    </div>

    <div v-else class="table-container">
      <table class="config-table">
        <thead>
          <tr>
            <th>Container Name</th>
            <th>Stack</th>
            <th>Job Name</th>
            <th>Host</th>
            <th>Exporter Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="config in configs" :key="config.config_id">
            <td>{{ config.container_name }}</td>
            <td>
              <span class="badge badge-info">{{ config.stack }}</span>
            </td>
            <td class="job-name">{{ config.job_name }}</td>
            <td>{{ getHostName(config.host_name) }}</td>
            <td>
              <span 
                v-if="config.exporter.running" 
                class="badge badge-success"
                title="Exporter is running"
              >
                Running
              </span>
              <span 
                v-else 
                class="badge badge-secondary"
                title="Exporter is not running"
              >
                Stopped
              </span>
            </td>
            <td class="text-xs text-gray">
              {{ formatDate(config.created_at) }}
            </td>
            <td>
              <button 
                @click="viewConfigFiles(config.config_id)" 
                class="btn btn-sm btn-primary"
                :disabled="loadingFiles === config.config_id"
              >
                <span v-if="loadingFiles === config.config_id" class="loading"></span>
                <span v-else>View Files</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal for viewing config files -->
    <div v-if="showModal" class="modal-backdrop" @click.self="closeModal">
      <div class="modal modal-large">
        <div class="modal-header">
          <h3 class="modal-title">Prometheus Config Files</h3>
          <button @click="closeModal" class="btn-close" title="Close">×</button>
        </div>
        
        <div v-if="loadingFiles" class="modal-content">
          <div class="loading"></div>
          <p>Loading files...</p>
        </div>

        <div v-else-if="configFiles && Object.keys(configFiles).length > 0" class="modal-content">
          <div 
            v-for="(content, fileName) in configFiles" 
            :key="fileName"
            class="file-section"
          >
            <h4 class="file-name">{{ fileName }}</h4>
            <pre class="yaml-content"><code>{{ formatYaml(content) }}</code></pre>
          </div>
        </div>

        <div v-else class="modal-content">
          <p class="text-gray">No files found</p>
        </div>

        <div class="modal-actions">
          <button @click="closeModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import yaml from 'js-yaml'
import { prometheusApi, hostsApi, type PrometheusConfigInfo, type PrometheusConfigFiles, type HostInfo } from '../services/api'

const configs = ref<PrometheusConfigInfo[]>([])
const hosts = ref<HostInfo[]>([])
const loading = ref(false)
const loadingFiles = ref<number | null>(null)
const showModal = ref(false)
const configFiles = ref<PrometheusConfigFiles | null>(null)

// Создаем маппинг host_id -> host_name
const hostNameMap = computed(() => {
  const map = new Map<string, string>()
  hosts.value.forEach(host => {
    map.set(host.id, host.name || host.id)
  })
  return map
})

// Функция для получения названия хоста
const getHostName = (hostId: string): string => {
  return hostNameMap.value.get(hostId) || hostId
}

const loadHosts = async () => {
  try {
    hosts.value = await hostsApi.getHosts()
  } catch (error: any) {
    console.error('Failed to load hosts:', error)
  }
}

const loadConfigs = async () => {
  loading.value = true
  try {
    const response = await prometheusApi.getAllConfigs()
    configs.value = response.configs
  } catch (error: any) {
    console.error('Failed to load configs:', error)
    alert(error.response?.data?.detail || error.message || 'Failed to load configs')
  } finally {
    loading.value = false
  }
}

const viewConfigFiles = async (configId: number) => {
  loadingFiles.value = configId
  showModal.value = true
  configFiles.value = null
  
  try {
    const files = await prometheusApi.getConfigFiles(configId)
    configFiles.value = files
  } catch (error: any) {
    console.error('Failed to load config files:', error)
    alert(error.response?.data?.detail || error.message || 'Failed to load config files')
    showModal.value = false
  } finally {
    loadingFiles.value = null
  }
}

const closeModal = () => {
  showModal.value = false
  configFiles.value = null
}

const formatDate = (dateString: string | null) => {
  if (!dateString) return '-'
  try {
    const date = new Date(dateString)
    return date.toLocaleString()
  } catch {
    return dateString
  }
}

const formatYaml = (content: any): string => {
  if (!content) return ''
  if (typeof content === 'string') {
    // Если это уже строка, проверяем, не является ли она YAML
    try {
      // Пытаемся распарсить как YAML и переформатировать
      const parsed = yaml.load(content)
      return yaml.dump(parsed, { 
        indent: 2,
        lineWidth: -1,
        noRefs: true,
        sortKeys: false
      })
    } catch {
      // Если не YAML, возвращаем как есть
      return content
    }
  }
  
  // Конвертируем объект в YAML
  try {
    return yaml.dump(content, { 
      indent: 2,
      lineWidth: -1,
      noRefs: true,
      sortKeys: false
    })
  } catch (error) {
    // Fallback на JSON если не получилось
    try {
      return JSON.stringify(content, null, 2)
    } catch {
      return String(content)
    }
  }
}

onMounted(() => {
  loadHosts()
  loadConfigs()
})
</script>

<style scoped>
.prometheus-view {
  padding: 20px;
  max-width: 1400px;
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

.loading-state,
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.table-container {
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
  overflow: hidden;
}

.config-table {
  width: 100%;
  border-collapse: collapse;
}

.config-table thead {
  background: var(--bg-secondary);
}

.config-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
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

.text-xs {
  font-size: 12px;
}

.text-gray {
  color: var(--text-secondary);
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

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal {
  background: var(--bg-card);
  border-radius: 8px;
  max-width: 900px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.modal-large {
  max-width: 1200px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.btn-close:hover {
  background: var(--bg-secondary);
}

.modal-content {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.file-section {
  margin-bottom: 24px;
}

.file-section:last-child {
  margin-bottom: 0;
}

.file-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.yaml-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 16px;
  overflow-x: auto;
  margin: 0;
}

.yaml-content code {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 20px;
  border-top: 1px solid var(--border);
}
</style>

