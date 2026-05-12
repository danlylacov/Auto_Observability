/** Fired after Prometheus/Grafana mutations so the containers table can refetch. */
export const CONTAINERS_REFRESH_EVENT = 'ao:containers-refresh'

export function emitContainersRefresh(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(CONTAINERS_REFRESH_EVENT))
  }
}
