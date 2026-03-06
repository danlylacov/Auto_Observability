<template>
  <div class="prometheus-view">
    <div class="header-section">
      <h1 class="page-title">Prometheus Configs</h1>
      <div class="header-actions">
        <button @click="loadMainConfig" class="btn btn-primary" :disabled="loadingMainConfig">
          <span v-if="loadingMainConfig" class="loading"></span>
          <span v-else>Refresh Config</span>
        </button>
        <button @click="loadConfigs" class="btn btn-primary" :disabled="loading">
          <span v-if="loading" class="loading"></span>
          <span v-else>Refresh Services</span>
        </button>
      </div>
    </div>

    <div class="content-layout">
      <!-- Left Column: Main Config -->
      <div class="left-column">
        <div class="config-panel">
          <div class="panel-header">
            <h2 class="panel-title">Main Prometheus Config</h2>
            <button @click="loadMainConfig" class="btn btn-sm btn-secondary" :disabled="loadingMainConfig">
              <span v-if="loadingMainConfig" class="loading"></span>
              <span v-else>↻</span>
            </button>
          </div>

          <div v-if="loadingMainConfig && !mainConfig" class="loading-state">
            <div class="loading"></div>
            <p>Loading main config...</p>
          </div>

          <div v-else-if="!mainConfig || !mainConfig.main_config" class="empty-state">
            <p>Main config not initialized</p>
          </div>

          <div v-else class="config-tree">
            <!-- Main Config Section -->
            <div class="tree-section">
              <div class="tree-header" @click="toggleSection('main')">
                <span class="tree-icon">{{ expandedSections.main ? '▼' : '▶' }}</span>
                <span class="tree-title">Main Config (prometheus.yml)</span>
              </div>
              <div v-if="expandedSections.main" class="tree-content">
                <div v-if="mainConfig.main_config.global" class="config-item">
                  <div class="config-key">global:</div>
                  <div class="config-value">
                    <CodeBlock :code="formatYaml(mainConfig.main_config.global)" :read-only="true" />
                  </div>
                </div>
                <div class="config-item">
                  <div class="config-key">scrape_configs:</div>
                  <div class="config-value">
                    <div v-for="(scrapeConfig, index) in mainConfig.main_config.scrape_configs" :key="index" class="scrape-config-item">
                      <div class="scrape-config-header" @click="toggleScrapeConfig(index)">
                        <span class="tree-icon">{{ expandedScrapeConfigs[index] ? '▼' : '▶' }}</span>
                        <span class="scrape-config-name">{{ scrapeConfig.job_name }}</span>
                      </div>
                      <div v-if="expandedScrapeConfigs[index]" class="scrape-config-content">
                        <CodeBlock :code="formatYaml(scrapeConfig)" :read-only="true" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Targets Files Section -->
            <div class="tree-section">
              <div class="tree-header" @click="toggleSection('targets')">
                <span class="tree-icon">{{ expandedSections.targets ? '▼' : '▶' }}</span>
                <span class="tree-title">Targets Files</span>
              </div>
              <div v-if="expandedSections.targets" class="tree-content">
                <div v-if="Object.keys(mainConfig.targets).length === 0" class="empty-state-small">
                  <p>No target files</p>
                </div>
                <div v-for="(targetContent, fileName) in mainConfig.targets" :key="fileName" class="target-file-item">
                  <div class="target-file-header" @click="toggleTargetFile(fileName)">
                    <span class="tree-icon">{{ expandedTargetFiles[fileName] ? '▼' : '▶' }}</span>
                    <span class="target-file-name">{{ fileName }}</span>
                  </div>
                  <div v-if="expandedTargetFiles[fileName]" class="target-file-content">
                    <CodeBlock :code="formatYaml(targetContent)" :read-only="true" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Services Table -->
      <div class="right-column">
        <div class="table-panel">
          <div class="panel-header">
            <h2 class="panel-title">Services</h2>
          </div>

          <div v-if="loading && configs.length === 0" class="loading-state">
            <div class="loading"></div>
            <p>Loading services...</p>
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
                  <th>In Main Config</th>
                  <th>Exporter Status</th>
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
                      v-if="isInMainConfig(config.job_name)" 
                      class="badge badge-success"
                      title="Service is in main config"
                    >
                      ✓
                    </span>
                    <span 
                      v-else 
                      class="badge badge-secondary"
                      title="Service is not in main config"
                    >
                      ✗
                    </span>
                  </td>
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
                  <td>
                    <div class="action-buttons">
                      <button 
                        v-if="!isInMainConfig(config.job_name)"
                        @click="addToMainConfig(config)" 
                        class="btn btn-sm btn-success"
                        :disabled="loadingActions[config.config_id]"
                        title="Add to main config"
                      >
                        <span v-if="loadingActions[config.config_id]" class="loading"></span>
                        <span v-else>Add</span>
                      </button>
                      <button 
                        v-else
                        @click="removeFromMainConfig(config)" 
                        class="btn btn-sm btn-danger"
                        :disabled="loadingActions[config.config_id]"
                        title="Remove from main config"
                      >
                        <span v-if="loadingActions[config.config_id]" class="loading"></span>
                        <span v-else>Remove</span>
                      </button>
                      <button 
                        @click="viewConfigFiles(config.config_id)" 
                        class="btn btn-sm btn-primary"
                        :disabled="loadingFiles === config.config_id"
                        title="View config files"
                      >
                        <span v-if="loadingFiles === config.config_id" class="loading"></span>
                        <span v-else>Files</span>
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
            <CodeBlock :code="formatYaml(content)" :read-only="true" />
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
import CodeBlock from '../components/CodeBlock.vue'
import { showToast } from '../utils/toast'
import { 
  prometheusApi, 
  hostsApi, 
  type PrometheusConfigInfo, 
  type PrometheusConfigFiles, 
  type HostInfo,
  type MainPrometheusConfig,
  type AddServiceRequest
} from '../services/api'

const configs = ref<PrometheusConfigInfo[]>([])
const hosts = ref<HostInfo[]>([])
const mainConfig = ref<MainPrometheusConfig | null>(null)
const loading = ref(false)
const loadingMainConfig = ref(false)
const loadingFiles = ref<number | null>(null)
const loadingActions = ref<Record<number, boolean>>({})
const showModal = ref(false)
const configFiles = ref<PrometheusConfigFiles | null>(null)

// Expanded sections state
const expandedSections = ref({
  main: true,
  targets: true
})

const expandedScrapeConfigs = ref<Record<number, boolean>>({})
const expandedTargetFiles = ref<Record<string, boolean>>({})

// Set of job names in main config
const mainConfigJobNames = ref<Set<string>>(new Set())

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

// Check if service is in main config
const isInMainConfig = (jobName: string): boolean => {
  return mainConfigJobNames.value.has(jobName)
}

// Update main config job names set
const updateMainConfigJobNames = () => {
  if (!mainConfig.value?.main_config?.scrape_configs) {
    mainConfigJobNames.value.clear()
    return
  }
  mainConfigJobNames.value = new Set(
    mainConfig.value.main_config.scrape_configs.map(sc => sc.job_name)
  )
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
    showToast(error.response?.data?.detail || error.message || 'Failed to load configs', 'error')
  } finally {
    loading.value = false
  }
}

const loadMainConfig = async () => {
  loadingMainConfig.value = true
  try {
    const response = await prometheusApi.getMainConfig()
    mainConfig.value = response
    updateMainConfigJobNames()
  } catch (error: any) {
    console.error('Failed to load main config:', error)
    showToast(error.response?.data?.detail || error.message || 'Failed to load main config', 'error')
  } finally {
    loadingMainConfig.value = false
  }
}

const addToMainConfig = async (config: PrometheusConfigInfo) => {
  loadingActions.value[config.config_id] = true
  try {
    const metadata = config.config_metadata || {}
    const info = metadata.info || {}
    
    const jobName = info.job_name || config.job_name
    const targetAddress = info.target_address || config.target_address
    const exporterPort = info.exporter_port || config.exporter_port

    const scrapeConfig: AddServiceRequest = {
      scrape_config: {
        scrape_configs: [{
          job_name: jobName,
          scrape_interval: '15s',
          scrape_timeout: '10s',
          file_sd_configs: [{
            files: [`targets/${jobName}.yml`]
          }]
        }]
      },
      target: [{
        targets: [`${targetAddress}:${exporterPort}`],
        labels: {}
      }],
      target_name: `${jobName}.yml`
    }

    await prometheusApi.addServiceToMainConfig(scrapeConfig)
    await loadMainConfig()
    showToast('Service added to main config successfully', 'success')
  } catch (error: any) {
    console.error('Failed to add service to main config:', error)
    showToast(error.response?.data?.detail || error.message || 'Failed to add service to main config', 'error')
  } finally {
    loadingActions.value[config.config_id] = false
  }
}

const removeFromMainConfig = async (config: PrometheusConfigInfo) => {
  loadingActions.value[config.config_id] = true
  try {
    const metadata = config.config_metadata || {}
    const info = metadata.info || {}
    
    const jobName = info.job_name || config.job_name

    await prometheusApi.removeServiceFromMainConfig({
      job_name: jobName,
      target_name: `${jobName}.yml`
    })
    await loadMainConfig()
    showToast('Service removed from main config successfully', 'success')
  } catch (error: any) {
    console.error('Failed to remove service from main config:', error)
    showToast(error.response?.data?.detail || error.message || 'Failed to remove service from main config', 'error')
  } finally {
    loadingActions.value[config.config_id] = false
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
    showToast(error.response?.data?.detail || error.message || 'Failed to load config files', 'error')
    showModal.value = false
  } finally {
    loadingFiles.value = null
  }
}

const closeModal = () => {
  showModal.value = false
  configFiles.value = null
}

const toggleSection = (section: 'main' | 'targets') => {
  expandedSections.value[section] = !expandedSections.value[section]
}

const toggleScrapeConfig = (index: number) => {
  expandedScrapeConfigs.value[index] = !expandedScrapeConfigs.value[index]
}

const toggleTargetFile = (fileName: string) => {
  expandedTargetFiles.value[fileName] = !expandedTargetFiles.value[fileName]
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
    try {
      const parsed = yaml.load(content)
      return yaml.dump(parsed, { 
        indent: 2,
        lineWidth: -1,
        noRefs: true,
        sortKeys: false
      })
    } catch {
      return content
    }
  }
  
  try {
    return yaml.dump(content, { 
      indent: 2,
      lineWidth: -1,
      noRefs: true,
      sortKeys: false
    })
  } catch (error) {
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
  loadMainConfig()
})
</script>

<style scoped>
.prometheus-view {
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

.header-actions {
  display: flex;
  gap: 10px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
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

.config-panel,
.table-panel {
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 150px);
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

.empty-state-small {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 14px;
}

.config-tree {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.tree-section {
  margin-bottom: 16px;
}

.tree-section:last-child {
  margin-bottom: 0;
}

.tree-header,
.scrape-config-header,
.target-file-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
}

.tree-header:hover,
.scrape-config-header:hover,
.target-file-header:hover {
  background: var(--bg-hover, rgba(0, 0, 0, 0.05));
}

.tree-icon {
  margin-right: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  width: 16px;
  display: inline-block;
}

.tree-title {
  font-weight: 600;
  color: var(--text-primary);
}

.tree-content {
  padding: 12px 0 0 20px;
}

.config-item {
  margin-bottom: 16px;
}

.config-key {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.config-value {
  margin-left: 16px;
}

.scrape-config-item,
.target-file-item {
  margin-bottom: 12px;
}

.scrape-config-name,
.target-file-name {
  font-family: monospace;
  font-size: 13px;
  color: var(--text-primary);
}

.scrape-config-content,
.target-file-content {
  padding: 8px 0 0 24px;
}

.yaml-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
  margin: 0;
}

.yaml-content code {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre;
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

.badge-danger {
  background: var(--danger-bg, #f8d7da);
  color: var(--danger-text, #721c24);
}

.action-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
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

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover, #0056b3);
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

.btn-success:hover:not(:disabled) {
  background: var(--success-hover, #218838);
}

.btn-danger {
  background: var(--danger-bg, #dc3545);
  color: white;
  border-color: var(--danger-bg, #dc3545);
}

.btn-danger:hover:not(:disabled) {
  background: var(--danger-hover, #c82333);
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

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 20px;
  border-top: 1px solid var(--border);
}
</style>
