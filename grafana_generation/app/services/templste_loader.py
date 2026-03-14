import requests
import json
import uuid
import os
import hashlib

class GrafanaTemplateLoader:
    """Загрузка и подготовка дашбордов с grafana.com"""

    GRAFANA_COM_API = "https://grafana.com/api/dashboards"

    def __init__(self, cache_dir="./.dashboard_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def fetch_dashboard_json(self, dashboard_id, revision=None):
        """
        Скачивает JSON дашборда с grafana.com
        :param dashboard_id: int, например 9628 для PostgreSQL
        :param revision: int, номер ревизии (None = последняя)
        :return: dict с JSON дашборда
        """
        if revision is None:
            meta_url = f"{self.GRAFANA_COM_API}/{dashboard_id}"
            resp = requests.get(meta_url, timeout=30)
            if resp.status_code != 200:
                raise Exception(f"Не удалось получить метаданные: {resp.text}")
            revision = resp.json()['revision']
            print(f"Последняя ревизия для #{dashboard_id}: {revision}")

        cache_key = f"{dashboard_id}_r{revision}"
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")

        if os.path.exists(cache_path):
            print(f"Загружено из кэша: {cache_path}")
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        download_url = f"{self.GRAFANA_COM_API}/{dashboard_id}/revisions/{revision}/download"
        resp = requests.get(download_url, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Не удалось скачать дашборд: {resp.text}")

        dashboard = resp.json()

        # 4. Сохраняем в кэш
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, indent=2)
        print(f"Сохранено в кэш: {cache_path}")

        return dashboard

    def prepare_for_import(self, dashboard, ds_uid, instance_suffix, title_prefix=None):
        """
        Подготавливает скачанный дашборд к импорту в Grafana
        :param dashboard: dict, JSON дашборда
        :param ds_uid: str, UID источника данных в вашей Grafana
        :param instance_suffix: str, уникальный суффикс (хост, IP, UUID)
        :param title_prefix: str, опциональный префикс для заголовка
        :return: dict, готовый к отправке в API
        """
        dash = json.loads(json.dumps(dashboard))

        dash.pop('id', None)
        dash['version'] = 0

        original_uid = dash.get('uid', 'dashboard')
        dash['uid'] = f"{original_uid}-{instance_suffix}"

        if title_prefix:
            dash['title'] = f"{title_prefix}: {dash.get('title', 'Dashboard')}"
        else:
            dash['title'] = f"{dash.get('title')} [{instance_suffix}]"

        self._replace_datasource_uids(dash, ds_uid)

        return dash

    def _replace_datasource_uids(self, dashboard, new_ds_uid):
        """Рекурсивная замена UID источников данных во всех панелях"""
        def process_element(elem):
            if isinstance(elem, dict):
                if 'targets' in elem:
                    for target in elem['targets']:
                        if 'datasource' in target:
                            if isinstance(target['datasource'], dict):
                                target['datasource']['uid'] = new_ds_uid
                                if 'type' not in target['datasource']:
                                    target['datasource']['type'] = 'prometheus'
                            elif isinstance(target['datasource'], str):
                                target['datasource'] = {'uid': new_ds_uid, 'type': 'prometheus'}

                if 'fieldConfig' in elem and 'defaults' in elem['fieldConfig']:
                    ds_ref = elem['fieldConfig']['defaults'].get('datasource')
                    if ds_ref and isinstance(ds_ref, dict):
                        ds_ref['uid'] = new_ds_uid

                if 'panels' in elem:
                    for panel in elem['panels']:
                        process_element(panel)

        for panel in dashboard.get('panels', []):
            process_element(panel)

a = GrafanaTemplateLoader()
print(a.fetch_dashboard_json('9628'))
