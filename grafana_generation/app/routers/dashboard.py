import logging
import os

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.grafana_dashboard_importer import GrafanaDashboardImporter, GrafanaHttpError
from app.services.templste_loader import GrafanaTemplateLoader

router = APIRouter()
logger = logging.getLogger(__name__)


class ImportDashboardRequest(BaseModel):
    template_key: str | None = Field(None, description="Ключ из grafana_templates.yml (postgresql, mongodb, ...)")
    dashboard_id: int | None = Field(None, description="Прямой ID дашборда на grafana.com")
    prometheus_datasource_uid: str | None = Field(None, description="UID Prometheus datasource в Grafana")
    instance_suffix: str | None = Field(None, description="Суффикс UID/заголовка; по умолчанию случайный")
    title_prefix: str | None = None
    overwrite: bool = True


class DeleteDashboardResponse(BaseModel):
    ok: bool
    uid: str


@router.get("/templates")
async def list_dashboard_templates():
    loader = GrafanaTemplateLoader()
    return {"templates": loader.load_templates_index()}


@router.post("/import_dashboard", status_code=status.HTTP_200_OK)
async def import_dashboard(req: ImportDashboardRequest):
    default_ds_uid = (
        req.prometheus_datasource_uid
        or os.getenv("DEFAULT_PROMETHEUS_DS_UID", "prometheus")
    ).strip()

    loader = GrafanaTemplateLoader()
    tid = req.dashboard_id
    tmpl_key = (req.template_key or "").strip() or None

    if tid is None:
        if not tmpl_key:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Укажите template_key или dashboard_id",
            )
        idx = loader.load_templates_index()
        lk = tmpl_key.replace(" ", "_").lower()
        meta = idx.get(tmpl_key) or idx.get(lk)
        if not meta or meta.get("dashboard_id") is None:
            keys = sorted(idx.keys())
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Неизвестный template_key '{tmpl_key}'. Доступные: {keys}",
            )
        tid = int(meta["dashboard_id"])

    try:
        raw = loader.fetch_dashboard_json(tid)
        prepared = loader.prepare_for_import(
            raw,
            ds_uid=default_ds_uid,
            instance_suffix=req.instance_suffix,
            title_prefix=req.title_prefix,
        )
        importer = GrafanaDashboardImporter()
        api_result = importer.import_dashboard(
            prepared,
            prometheus_ds_uid=default_ds_uid,
            overwrite=req.overwrite,
        )
        out = dict(api_result)
        out.setdefault("dashboard_title", prepared.get("title"))
        return {
            **out,
            "template_key": tmpl_key,
            "dashboard_source_id": tid,
            "prometheus_datasource_uid": default_ds_uid,
        }
    except GrafanaHttpError as e:
        logger.error("Grafana HTTP error during import: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Dashboard import failed: %s", e)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/dashboard/uid/{uid}", response_model=DeleteDashboardResponse)
async def delete_dashboard_by_uid(uid: str):
    if not uid.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="uid is required")

    importer = GrafanaDashboardImporter()
    if not importer.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="GRAFANA_URL is not configured")

    try:
        importer.delete_dashboard_by_uid(uid)
        return DeleteDashboardResponse(ok=True, uid=uid)
    except GrafanaHttpError as e:
        if e.status_code == 404:
            return DeleteDashboardResponse(ok=True, uid=uid)
        logger.error("Grafana HTTP error during delete: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)
