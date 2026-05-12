import {
  containerApi,
  grafanaApi,
  prometheusApi,
  type AddServiceRequest,
  type PrometheusConfigInfo
} from '../services/api'

export function buildAddServiceRequestFromPrometheusConfig(
  config: PrometheusConfigInfo
): AddServiceRequest {
  const metadata = config.config_metadata || {}
  const info = metadata.info || {}
  const jobName = info.job_name || config.job_name
  const targetAddress = info.target_address || config.target_address
  const exporterPort = info.exporter_port ?? config.exporter_port
  if (!jobName) {
    throw new Error('Job name is missing')
  }
  if (!targetAddress) {
    throw new Error('Target address is missing')
  }
  if (exporterPort == null) {
    throw new Error('Exporter port is missing')
  }
  return {
    scrape_config: {
      scrape_configs: [
        {
          job_name: jobName,
          scrape_interval: '15s',
          scrape_timeout: '10s',
          file_sd_configs: [{ files: [`targets/${jobName}.yml`] }]
        }
      ]
    },
    target: [{ targets: [`${targetAddress}:${exporterPort}`], labels: {} }],
    target_name: `${jobName}.yml`
  }
}

export async function tryAddServiceToMainConfig(config: PrometheusConfigInfo): Promise<void> {
  const body = buildAddServiceRequestFromPrometheusConfig(config)
  try {
    await prometheusApi.addServiceToMainConfig(body)
  } catch (error: any) {
    const detail = String(error.response?.data?.detail || error.message || '').toLowerCase()
    if (detail.includes('already') || detail.includes('duplicate')) {
      return
    }
    throw error
  }
}

/**
 * Prometheus manager only syncs YAML from MinIO to disk on config/update.
 * The running Prometheus process must be restarted to load new scrape configs and targets.
 */
export async function restartPrometheusManager(): Promise<void> {
  try {
    await prometheusApi.stopManager()
  } catch {
    /* already stopped or unreachable */
  }
  await new Promise((resolve) => setTimeout(resolve, 1000))
  await prometheusApi.startManager()
}

export type ReloadFn = (opts?: { silent?: boolean }) => Promise<void>

export async function waitForGrafanaMetricsReady(
  reload: ReloadFn,
  isReady: () => boolean,
  timeoutMs = 120000,
  intervalMs = 2500
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    await reload({ silent: true })
    if (isReady()) {
      return true
    }
    await new Promise((r) => setTimeout(r, intervalMs))
  }
  return false
}

/**
 * After up_exporter, Docker may need a few seconds before the container is "running"
 * in Redis. Poll update_containers + reload until the app sees exporter.running.
 */
export async function waitForExporterRunning(
  reload: ReloadFn,
  isRunning: () => boolean,
  timeoutMs = 120000,
  intervalMs = 2000
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      await containerApi.updateContainers()
    } catch {
      /* still try reload */
    }
    await reload({ silent: true })
    if (isRunning()) {
      return true
    }
    await new Promise((r) => setTimeout(r, intervalMs))
  }
  return false
}

export async function runContainerStartAllPipeline(params: {
  containerId: string
  hostId: string
  exporterPort: number
  skipUpExporter: boolean
  reload: ReloadFn
  isExporterRunning: () => boolean
  isGrafanaMetricsReady: () => boolean
  instanceSuffix: string
}): Promise<'ok' | 'timeout'> {
  const {
    containerId,
    hostId,
    exporterPort,
    skipUpExporter,
    reload,
    isExporterRunning,
    isGrafanaMetricsReady,
    instanceSuffix
  } = params

  if (!skipUpExporter) {
    await containerApi.upExporter(containerId, exporterPort)
    const exporterOk = await waitForExporterRunning(reload, isExporterRunning)
    if (!exporterOk) {
      throw new Error(
        'Timed out waiting for exporter container to become running. Check Docker and host agent.'
      )
    }
  } else if (!isExporterRunning()) {
    const exporterOk = await waitForExporterRunning(reload, isExporterRunning, 60000, 2000)
    if (!exporterOk) {
      throw new Error('Exporter is not running; start the exporter or run Start all without skip.')
    }
  }

  await containerApi.generateConfig(containerId, hostId)
  await reload()

  const all = await prometheusApi.getAllConfigs()
  const cfg = all.configs.find((c) => c.container_id === containerId)
  if (!cfg) {
    throw new Error('Prometheus config not found after generate')
  }
  await tryAddServiceToMainConfig(cfg)
  await prometheusApi.updateManagerConfig()
  await restartPrometheusManager()
  await reload()

  const ready = await waitForGrafanaMetricsReady(reload, isGrafanaMetricsReady)
  if (!ready) {
    return 'timeout'
  }

  await grafanaApi.importDashboard({
    prometheus_datasource_uid: 'prometheus',
    instance_suffix: instanceSuffix,
    overwrite: true
  })
  await reload()
  return 'ok'
}
