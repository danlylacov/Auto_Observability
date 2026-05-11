"""Grafana — прокси к grafana_generation + учёт импортированных дашбордов."""

from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.postgres.database import get_db
from app.db.redis.docker_containers import DockerContainers
from app.models.postgres.grafana_dashboard import GrafanaDashboard
from app.models.postgres.prometheus_config import PrometheusConfig
from app.services.api_getaway import APIGateway

router = APIRouter()

load_dotenv()
grafana_generation_url = os.getenv("GRAFANA_GENERATION_URL")
prometheus_generation_url = os.getenv("PROMETHEUS_GENERATION_URL")


def _generation_gateway() -> APIGateway:
    if not grafana_generation_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GRAFANA_GENERATION_URL is not configured",
        )
    return APIGateway(grafana_generation_url)


def _main_config_jobs() -> set[str]:
    """Read current job_name set from main Prometheus config service."""
    if not prometheus_generation_url:
        return set()
    try:
        gw = APIGateway(prometheus_generation_url)
        data = gw.make_request("GET", "/api/v1/main-config/", timeout=15.0)
        main_cfg = data.get("main_config") if isinstance(data, dict) else None
        scrape_configs = (main_cfg or {}).get("scrape_configs") or []
        jobs = set()
        for sc in scrape_configs:
            if isinstance(sc, dict) and sc.get("job_name"):
                jobs.add(str(sc["job_name"]))
        return jobs
    except Exception:
        return set()


class ImportDashboardBody(BaseModel):
    template_key: Optional[str] = Field(None)
    dashboard_id: Optional[int] = None
    prometheus_datasource_uid: Optional[str] = None
    instance_suffix: Optional[str] = None
    title_prefix: Optional[str] = None
    overwrite: bool = True


@router.get("/templates")
async def grafana_templates() -> dict[str, Any]:
    """Список шаблонов из grafana_templates.yml."""
    gw = _generation_gateway()
    return gw.make_request("GET", "/api/v1/grafana/templates", timeout=30.0)


@router.post("/import_dashboard", status_code=status.HTTP_200_OK)
async def import_dashboard(
    body: ImportDashboardBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Загружает шаблон, переписывает datasource Prometheus, импортирует в Grafana."""
    gw = _generation_gateway()
    payload = body.model_dump(exclude_none=True)

    # Server-side guard: resolve template by container stack to avoid wrong dashboard type.
    resolved_stack = None
    resolved_template = body.template_key
    suffix = (body.instance_suffix or "").strip()
    if suffix:
        cfg_rows = (
            db.query(PrometheusConfig)
            .filter(
                PrometheusConfig.status == "active",
            )
            .order_by(PrometheusConfig.created_at.desc())
            .all()
        )
        suffix_norm = suffix.lstrip("/").lower()
        cfg = next(
            (
                r for r in cfg_rows
                if str((r.container_name or "")).lstrip("/").lower() == suffix_norm
            ),
            None,
        )
        if cfg and cfg.stack:
            resolved_stack = str(cfg.stack).lower()
            if not resolved_template or str(resolved_template).lower() != resolved_stack:
                try:
                    templates = gw.make_request("GET", "/api/v1/grafana/templates", timeout=20.0) or {}
                    available = set((templates.get("templates") or {}).keys())
                    if resolved_stack in available:
                        resolved_template = resolved_stack
                except Exception:
                    # keep user-provided template if template index is unavailable
                    pass
    if resolved_template:
        payload["template_key"] = resolved_template
    resp = gw.make_request(
        "POST",
        "/api/v1/grafana/import_dashboard",
        json_data=payload,
        timeout=120.0,
    )

    uid = resp.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ответ grafana_generation не содержит uid",
        )

    title = resp.get("dashboard_title")
    dash = resp.get("dashboard") if isinstance(resp.get("dashboard"), dict) else None
    if not title and isinstance(dash, dict):
        title = dash.get("title")

    tmpl_key = resolved_template or body.template_key
    sid = resp.get("dashboard_source_id") or body.dashboard_id

    row = db.query(GrafanaDashboard).filter(GrafanaDashboard.uid == uid).first()
    if row:
        row.title = title or row.title
        row.template_key = tmpl_key or row.template_key
        if sid is not None:
            row.source_dashboard_id = int(sid)
        row.slug = resp.get("slug") or row.slug
        row.url = resp.get("url") or row.url
    else:
        row = GrafanaDashboard(
            uid=uid,
            title=title or tmpl_key or uid,
            template_key=tmpl_key or "",
            source_dashboard_id=int(sid) if sid is not None else None,
            slug=resp.get("slug"),
            url=resp.get("url"),
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return {"db_record_id": row.id, **resp}


@router.get("/imported_dashboards")
async def list_imported_dashboards(db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = (
        db.query(GrafanaDashboard)
        .order_by(GrafanaDashboard.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "uid": r.uid,
                "title": r.title,
                "template_key": r.template_key,
                "source_dashboard_id": r.source_dashboard_id,
                "slug": r.slug,
                "url": r.url,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/eligible_containers")
async def list_eligible_containers(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Containers available for dashboard creation:
    - active Prometheus config exists
    - exporter running
    - job is already in main Prometheus config (metrics imported)
    """
    docker_containers = DockerContainers()
    all_containers_data = docker_containers.get_containers()
    main_jobs = _main_config_jobs()

    configs = db.query(PrometheusConfig).filter(
        PrometheusConfig.status == "active"
    ).order_by(PrometheusConfig.created_at.desc()).all()

    rows: list[dict[str, Any]] = []
    for cfg in configs:
        metadata = cfg.config_metadata or {}
        host_name = metadata.get("host_name", "localhost")
        base_name = (cfg.container_name or "").lstrip("/")
        exporter_name = f"{base_name}-exporter".lower()

        exporter_running = False
        exporter_status = None
        for cdata in all_containers_data.values():
            if not isinstance(cdata, dict):
                continue
            cname = cdata.get("info", {}).get("Name", "").lstrip("/").lower()
            chost = cdata.get("host_name") or cdata.get("host_id")
            if cname == exporter_name and chost == host_name:
                exporter_status = cdata.get("info", {}).get("State", {}).get("Status", "")
                exporter_running = str(exporter_status).lower() in ("running", "up")
                break
        if not exporter_status:
            for cdata in all_containers_data.values():
                if not isinstance(cdata, dict):
                    continue
                cname = cdata.get("info", {}).get("Name", "").lstrip("/").lower()
                if cname == exporter_name:
                    exporter_status = cdata.get("info", {}).get("State", {}).get("Status", "")
                    exporter_running = str(exporter_status).lower() in ("running", "up")
                    break

        job_name = cfg.job_name
        in_main_config = bool(job_name and job_name in main_jobs)
        metrics_ready = exporter_running and in_main_config

        rows.append(
            {
                "config_id": cfg.id,
                "container_id": cfg.container_id,
                "container_name": cfg.container_name,
                "stack": cfg.stack,
                "job_name": job_name,
                "host_name": host_name,
                "target_address": cfg.target_address,
                "exporter_port": cfg.exporter_port,
                "exporter_running": exporter_running,
                "exporter_status": exporter_status,
                "in_main_config": in_main_config,
                "metrics_ready": metrics_ready,
                "config_metadata": metadata,
            }
        )
    return {"items": rows}


@router.delete("/imported_dashboards/{dashboard_id}", status_code=status.HTTP_200_OK)
async def delete_imported_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    row = db.query(GrafanaDashboard).filter(GrafanaDashboard.id == dashboard_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Dashboard record not found")

    gw = _generation_gateway()
    gw.make_request(
        "DELETE",
        f"/api/v1/grafana/dashboard/uid/{row.uid}",
        timeout=60.0,
    )

    db.delete(row)
    db.commit()
    return {"ok": True, "deleted_id": dashboard_id, "uid": row.uid}
