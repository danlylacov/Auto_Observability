import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081'

console.log('API URL configured:', API_URL)

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000 // 30 секунд
})

// Добавляем interceptor для логирования запросов
api.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to: ${config.url}`)
    return config
  },
  (error) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// Добавляем interceptor для логирования ответов
api.interceptors.response.use(
  (response) => {
    console.log(`Response from ${response.config.url}:`, response.status)
    return response
  },
  (error) => {
    console.error(`Error from ${error.config?.url}:`, {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      data: error.response?.data
    })
    return Promise.reject(error)
  }
)

export interface ContainerInfo {
  Id: string
  Name: string
  State: {
    Status: string
  }
  Config: {
    Image: string
    Env: string[]
    Labels: Record<string, string>
  }
  NetworkSettings: any
}

export interface PrometheusConfigData {
  config_id: number
  status: string
  stack: string
  exporter_image: string
  exporter_port: number
  job_name: string
  created_at: string | null
  exporter: {
    exists: boolean
    running: boolean
    container_id: string | null
    info: {
      container_id: string
      name: string
      status: string
      image: string
    } | null
  }
}

export interface ContainerData {
  info: ContainerInfo
  classification: {
    result: [string, number][]
  }
  host_id?: string
  host_name?: string
  has_prometheus_config?: boolean
  prometheus_config?: PrometheusConfigData | null
}

export interface ContainersResponse {
  [containerId: string]: ContainerData
}

export interface HostInfo {
  id: string
  name: string
  host: string
  port: number
  status?: number | string
}

export const hostsApi = {
  async getHosts(): Promise<HostInfo[]> {
    const response = await api.get<{ hosts: Record<string, any> | HostInfo[] }>('/api/v1/hosts/get')
    const raw = response.data.hosts

    if (Array.isArray(raw)) {
      // Если backend вернул список объектов HostDTO
      return raw as HostInfo[]
    }

    // Если backend вернул словарь id -> данные из Redis
    return Object.entries(raw || {}).map(([id, data]: [string, any]) => ({
      id,
      name: data.name,
      host: data.host,
      port: data.port,
      status: data.status
    }))
  },

  async addHost(payload: { name: string; host: string; port: number }): Promise<any> {
    const params = new URLSearchParams()
    params.append('name', payload.name)
    params.append('host', payload.host)
    params.append('port', String(payload.port))
    const response = await api.post('/api/v1/hosts/add', null, { params })
    return response.data
  },

  async updateHost(payload: { id: string; name?: string; host?: string; port?: number | null }): Promise<any> {
    const params: Record<string, any> = { id: payload.id }
    if (payload.name !== undefined) params.name = payload.name
    if (payload.host !== undefined) params.host = payload.host
    if (payload.port !== undefined && payload.port !== null) params.port = payload.port
    const response = await api.put('/api/v1/hosts/update', null, { params })
    return response.data
  },

  async deleteHost(id: string): Promise<any> {
    const response = await api.delete('/api/v1/hosts/delete', { params: { id } })
    return response.data
  },

  async refreshHosts(): Promise<any> {
    const response = await api.get('/api/v1/hosts/update_hosts')
    return response.data
  }
}

export const configApi = {
  async getSignature(): Promise<string> {
    const response = await api.get<{ signature: string } | any>('/api/v1/prometheus/get_signature')
    // backend может вернуть просто строку или объект; обрабатываем оба варианта
    if (typeof response.data === 'string') {
      return response.data
    }
    if (typeof response.data?.signature === 'string') {
      return response.data.signature
    }
    // Если это объект с ключом "signature.yml", извлекаем значение
    if (response.data && typeof response.data === 'object' && 'signature.yml' in response.data) {
      return response.data['signature.yml']
    }
    // Если это объект, пытаемся преобразовать в YAML
    if (response.data && typeof response.data === 'object') {
      // Если объект содержит только один ключ и значение - строка, возвращаем значение
      const keys = Object.keys(response.data)
      if (keys.length === 1 && typeof response.data[keys[0]] === 'string') {
        return response.data[keys[0]]
      }
    }
    return JSON.stringify(response.data, null, 2)
  },

  async updateSignature(newSignature: string): Promise<any> {
    const response = await api.patch('/api/v1/prometheus/update_signature', null, {
      params: { new_signature: newSignature }
    })
    return response.data
  }
}

export const containerApi = {
  async getContainers(hostId?: string): Promise<ContainersResponse> {
    const params = hostId ? { host_id: hostId } : undefined
    const response = await api.get<ContainersResponse>('/api/v1/containers/containers', { params })
    return response.data
  },

  async updateContainers(): Promise<{ message: string }> {
    const response = await api.patch<{ message: string }>('/api/v1/containers/update_containers')
    return response.data
  },

  async startContainer(id: string, hostId: string): Promise<any> {
    const response = await api.post(
      `/api/v1/containers/container/start`,
      null,
      { params: { id, host_id: hostId } }
    )
    return response.data
  },

  async stopContainer(id: string, hostId: string): Promise<any> {
    const response = await api.post(
      `/api/v1/containers/container/stop`,
      null,
      { params: { id, host_id: hostId } }
    )
    return response.data
  },

  async removeContainer(id: string, hostId: string, force: boolean = false): Promise<any> {
    const response = await api.delete(
      `/api/v1/containers/container/remove`,
      { params: { id, host_id: hostId, force } }
    )
    return response.data
  },

  async generateConfig(containerId: string, hostId: string): Promise<any> {
    const response = await api.post(`/api/v1/prometheus/generate_config?container_id=${containerId}&host_id=${hostId}`)
    return response.data
  },

  async upExporter(containerId: string, port: number): Promise<any> {
    const response = await api.post(`/api/v1/prometheus/up_exporter?container_id=${containerId}&port=${port}`)
    return response.data
  }
}

export interface PrometheusConfigInfo {
  config_id: number
  container_id: string
  container_name: string
  stack: string
  exporter_image: string
  exporter_port: number
  target_address: string
  job_name: string
  minio_bucket: string
  minio_file_path: string
  host_name: string
  created_at: string | null
  updated_at: string | null
  exporter: {
    running: boolean
    container_id: string | null
    info: any | null
  }
  config_metadata: any
}

export interface PrometheusConfigsResponse {
  total: number
  configs: PrometheusConfigInfo[]
}

export interface PrometheusConfigFiles {
  [fileName: string]: any
}

export interface MainPrometheusConfig {
  main_config: {
    global?: {
      scrape_interval?: string
    }
    scrape_configs: Array<{
      job_name: string
      scrape_interval?: string
      scrape_timeout?: string
      file_sd_configs?: Array<{
        files: string[]
      }>
      [key: string]: any
    }>
  } | null
  targets: {
    [fileName: string]: any
  }
}

export interface AddServiceRequest {
  scrape_config: {
    scrape_configs: Array<{
      job_name: string
      scrape_interval?: string
      scrape_timeout?: string
      file_sd_configs?: Array<{
        files: string[]
      }>
      [key: string]: any
    }>
  }
  target: Array<{
    targets: string[]
    labels?: Record<string, any>
  }> | {
    targets: string[]
    labels?: Record<string, any>
  }
  target_name: string
}

export interface RemoveServiceRequest {
  job_name: string
  target_name: string
}

export const prometheusApi = {
  async getAllConfigs(): Promise<PrometheusConfigsResponse> {
    const response = await api.get<PrometheusConfigsResponse>('/api/v1/prometheus/get_all_configs')
    return response.data
  },

  async getConfigFiles(configId: number): Promise<PrometheusConfigFiles> {
    const response = await api.get<PrometheusConfigFiles>(`/api/v1/prometheus/get_config_files/${configId}`)
    return response.data
  },

  async getMainConfig(): Promise<MainPrometheusConfig> {
    const response = await api.get<MainPrometheusConfig>('/api/v1/prometheus/main_config/get')
    return response.data
  },

  async addServiceToMainConfig(request: AddServiceRequest): Promise<any> {
    const response = await api.post('/api/v1/prometheus/main_config/add', request)
    return response.data
  },

  async removeServiceFromMainConfig(request: RemoveServiceRequest): Promise<any> {
    const response = await api.delete('/api/v1/prometheus/main_config/remove', { data: request })
    return response.data
  },

  async startManager(): Promise<any> {
    const response = await api.post('/api/v1/prometheus/manager/start')
    return response.data
  },

  async stopManager(): Promise<any> {
    const response = await api.post('/api/v1/prometheus/manager/stop')
    return response.data
  },

  async getManagerStatus(): Promise<any> {
    const response = await api.get('/api/v1/prometheus/manager/status')
    return response.data
  },

  async getManagerSettings(): Promise<any> {
    const response = await api.get('/api/v1/prometheus/manager/settings')
    return response.data
  },

  async updateManagerSettings(settings: Record<string, any>): Promise<any> {
    const response = await api.post('/api/v1/prometheus/manager/settings', settings)
    return response.data
  },

  async updateManagerConfig(): Promise<any> {
    const response = await api.post('/api/v1/prometheus/manager/config/update')
    return response.data
  }
}

