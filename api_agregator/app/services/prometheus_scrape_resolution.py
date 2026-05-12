"""Resolve scrape host port from Redis-backed Docker inspect (no FastAPI/DB imports)."""

from __future__ import annotations

from typing import Any


def redis_host_key_for_api_host_id(cdata: dict[str, Any]) -> str | None:
    """Compare with API host_id (Postgres UUID). Prefer host_id over human-readable host_name."""
    return cdata.get("host_id") or cdata.get("host_name")


def _host_port_from_port_bindings(
    info: dict[str, Any],
    preferred_internal: int | None,
) -> int | None:
    """Resolve host port from HostConfig.PortBindings when NetworkSettings.Ports is empty."""
    bindings = (info.get("HostConfig") or {}).get("PortBindings") or {}
    if preferred_internal is not None:
        pk = f"{int(preferred_internal)}/tcp"
        lst = bindings.get(pk)
        if lst and isinstance(lst, list) and lst[0].get("HostPort"):
            hp = lst[0]["HostPort"]
            if hp:
                return int(hp)
    for _pk, lst in bindings.items():
        if str(_pk).endswith("/tcp") and lst and isinstance(lst, list) and lst[0].get("HostPort"):
            hp = lst[0]["HostPort"]
            if hp:
                return int(hp)
    return None


def host_port_from_redis_inspect(
    exporter_cdata: dict[str, Any],
    preferred_internal: int | None,
) -> int | None:
    """Host-published port for a bridge-mode exporter (Docker Ports / bindings)."""
    info = exporter_cdata.get("info") or {}
    ports = (info.get("NetworkSettings") or {}).get("Ports") or {}
    if preferred_internal is not None:
        pk = f"{int(preferred_internal)}/tcp"
        b = ports.get(pk)
        if b and isinstance(b, list) and b[0].get("HostPort"):
            return int(b[0]["HostPort"])
    for _pk, b in ports.items():
        if str(_pk).endswith("/tcp") and b and isinstance(b, list) and b[0].get("HostPort"):
            return int(b[0]["HostPort"])
    return _host_port_from_port_bindings(info, preferred_internal)


def find_exporter_container_data(
    *,
    workload_container_name: str,
    host_id: str,
    all_containers: dict[str, Any],
) -> dict[str, Any] | None:
    exp = f"{workload_container_name.lstrip('/').lower()}-exporter"
    for cdata in all_containers.values():
        if not isinstance(cdata, dict):
            continue
        nm = (cdata.get("info") or {}).get("Name", "").lstrip("/").lower()
        if nm != exp:
            continue
        ch = redis_host_key_for_api_host_id(cdata)
        if ch and ch != host_id:
            continue
        return cdata
    return None


def resolve_scrape_host_port_for_workload(
    *,
    config_info: dict[str, Any] | None,
    exporter_internal_port: int | None,
    workload_container_name: str,
    redis_host_key: str,
    all_containers: dict[str, Any],
) -> int | None:
    """DB scrape_host_port (from up_exporter) then Redis-published port for the exporter."""
    cfgi = config_info or {}
    raw = cfgi.get("scrape_host_port")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    exp_cdata = find_exporter_container_data(
        workload_container_name=workload_container_name,
        host_id=redis_host_key,
        all_containers=all_containers,
    )
    if exp_cdata:
        return host_port_from_redis_inspect(exp_cdata, exporter_internal_port)
    return None


def rewrite_targets_internal_port_to_host_port(
    target: Any,
    *,
    internal_port: int,
    host_port: int,
) -> Any:
    """Replace :internal_port with :host_port in Prometheus static target entries."""
    if target is None:
        return target
    items: list[Any] = target if isinstance(target, list) else [target]
    out: list[Any] = []
    for item in items:
        if not isinstance(item, dict):
            out.append(item)
            continue
        cp = dict(item)
        tl = cp.get("targets")
        if isinstance(tl, list):
            new_tl: list[Any] = []
            for addr in tl:
                if isinstance(addr, str) and ":" in addr:
                    _h, _, ps = addr.rpartition(":")
                    try:
                        pi = int(ps)
                    except ValueError:
                        new_tl.append(addr)
                        continue
                    if pi == internal_port:
                        new_tl.append(f"{_h}:{host_port}")
                    else:
                        new_tl.append(addr)
                else:
                    new_tl.append(addr)
            cp["targets"] = new_tl
        out.append(cp)
    return out if isinstance(target, list) else out[0]
