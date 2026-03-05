import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

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

export interface ContainerData {
  info: ContainerInfo
  classification: {
    result: [string, number][]
  }
  host_id?: string
  host_name?: string
  has_prometheus_config?: boolean
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

