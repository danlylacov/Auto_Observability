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
}

export interface ContainersResponse {
  [containerId: string]: ContainerData
}

export const containerApi = {
  async getContainers(): Promise<ContainersResponse> {
    const response = await api.get<ContainersResponse>('/api/v1/containers/containers')
    return response.data
  },

  async updateContainers(): Promise<{ message: string }> {
    const response = await api.patch<{ message: string }>('/api/v1/containers/update_containers')
    return response.data
  },

  async startContainer(id: string): Promise<any> {
    const response = await api.post(`/api/v1/containers/container/start?id=${id}`)
    return response.data
  },

  async stopContainer(id: string): Promise<any> {
    const response = await api.post(`/api/v1/containers/container/stop?id=${id}`)
    return response.data
  },

  async removeContainer(id: string, force: boolean = false): Promise<any> {
    const response = await api.delete(`/api/v1/containers/container/remove?id=${id}&force=${force}`)
    return response.data
  },

  async generateConfig(containerId: string): Promise<any> {
    const response = await api.post(`/api/v1/prometheus/generate_config?container_id=${containerId}`)
    return response.data
  },

  async upExporter(containerId: string, port: number): Promise<any> {
    const response = await api.post(`/api/v1/prometheus/up_exporter?container_id=${containerId}&port=${port}`)
    return response.data
  }
}

