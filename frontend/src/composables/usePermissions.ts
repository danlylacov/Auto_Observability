import { computed } from 'vue'
import { role } from '../auth/session'

/** Aligns with api_agregator role checks (UI hints; server enforces). */
export function usePermissions() {
  const r = computed(() => role.value)

  const canView = computed(() =>
    ['maintainer', 'admin', 'dev', 'user'].includes(r.value)
  )

  const canMutateHosts = computed(() =>
    ['maintainer', 'admin', 'dev'].includes(r.value)
  )

  const canMutateContainers = computed(() =>
    ['maintainer', 'admin'].includes(r.value)
  )

  const canMutatePrometheusGrafanaConfig = computed(() =>
    ['maintainer', 'admin'].includes(r.value)
  )

  return {
    role: r,
    canView,
    canMutateHosts,
    canMutateContainers,
    canMutatePrometheusGrafanaConfig
  }
}
