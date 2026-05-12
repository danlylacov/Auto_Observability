/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_PROMETHEUS_URL?: string
  readonly VITE_GRAFANA_EXTERNAL_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
