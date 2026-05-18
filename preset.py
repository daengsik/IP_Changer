"""프리셋/설정/히스토리 영속화 — 모든 파일은 ``%APPDATA%\\IPChanger\\`` 에 저장된다.

  - ``preset.json``     : 12 개 프리셋
  - ``preset.json.bak`` : 마지막 정상 저장본(1세대 자동 백업)
  - ``config.json``     : 테마, 창 geometry, 종료 동작 등 앱 설정
  - ``history.json``    : 최근 N 건 변경 이력 — 되돌리기 소스
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Optional


_PRESET_COUNT = 12
_HISTORY_MAX = 50


def _get_app_folder() -> Path:
    folder = Path(os.getenv("APPDATA") or os.path.expanduser("~")) / "IPChanger"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ──────────────────────────────────────────────
# 앱 설정 (테마 등)
# ──────────────────────────────────────────────

def load_config() -> dict:
    path = _get_app_folder() / "config.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> None:
    path = _get_app_folder() / "config.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ──────────────────────────────────────────────
# 프리셋
# ──────────────────────────────────────────────

DEFAULT_PRESETS: list[dict] = [
    {
        "name": f"프리셋 {i + 1}",
        "desc": f"Preset {i + 1}",
        "ip_addr": f"192.168.{i + 1}.100",
        "subnet": "255.255.255.0",
        "gateway": f"192.168.{i + 1}.1",
        "dns": "",
    }
    for i in range(_PRESET_COUNT)
]

_REQUIRED_KEYS = {"name", "desc", "ip_addr", "subnet", "gateway", "dns"}

# 메모리 캐시 — UI 가 빈번하게 load_presets 를 호출하므로 디스크 I/O 를 줄인다.
_cache_lock = threading.Lock()
_preset_cache: Optional[list[dict]] = None


def get_preset_path() -> Path:
    return _get_app_folder() / "preset.json"


def _backup_path() -> Path:
    return _get_app_folder() / "preset.json.bak"


def _is_valid(data: object) -> bool:
    return (
        isinstance(data, list)
        and len(data) >= _PRESET_COUNT
        and all(_REQUIRED_KEYS.issubset(item.keys()) for item in data[:_PRESET_COUNT])
    )


def _normalize(item: dict) -> dict:
    """누락된 키를 기본값으로 채워 일관된 스키마를 보장."""
    return {
        "name":    str(item.get("name") or "").strip(),
        "desc":    str(item.get("desc") or "").strip(),
        "ip_addr": str(item.get("ip_addr") or "").strip(),
        "subnet":  str(item.get("subnet") or "").strip(),
        "gateway": str(item.get("gateway") or "").strip(),
        "dns":     str(item.get("dns") or "").strip(),
    }


def init_presets() -> None:
    """파일이 없거나 손상되면 백업으로 복구, 그래도 실패하면 기본값으로 초기화."""
    path = get_preset_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if _is_valid(data):
                return
        except (json.JSONDecodeError, OSError):
            pass
        bak = _backup_path()
        if bak.exists():
            try:
                with open(bak, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if _is_valid(data):
                    save_presets(data, _make_backup=False)
                    return
            except (json.JSONDecodeError, OSError):
                pass
    save_presets(list(DEFAULT_PRESETS), _make_backup=False)


def load_presets(*, force_disk: bool = False) -> list[dict]:
    """preset.json 을 읽어 12개 항목 반환. 평소엔 캐시, ``force_disk=True`` 시 강제 재로드."""
    global _preset_cache
    with _cache_lock:
        if _preset_cache is not None and not force_disk:
            return [dict(p) for p in _preset_cache]

    path = get_preset_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if _is_valid(data):
            data = [_normalize(it) for it in data[:_PRESET_COUNT]]
            with _cache_lock:
                _preset_cache = data
            return [dict(p) for p in data]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    fallback = list(DEFAULT_PRESETS)
    save_presets(fallback, _make_backup=False)
    return fallback


def save_presets(data: list[dict], *, _make_backup: bool = True) -> None:
    """원자적 저장(임시파일 → os.replace) + 1세대 백업 + 캐시 갱신."""
    global _preset_cache
    normalized = [_normalize(it) for it in data[:_PRESET_COUNT]]
    while len(normalized) < _PRESET_COUNT:
        normalized.append(dict(DEFAULT_PRESETS[len(normalized)]))

    path = get_preset_path()
    if _make_backup and path.exists():
        try:
            shutil.copy2(path, _backup_path())
        except OSError:
            pass

    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=4)
    os.replace(tmp, path)

    with _cache_lock:
        _preset_cache = normalized


# ──────────────────────────────────────────────
# 가져오기 / 내보내기
# ──────────────────────────────────────────────

def export_presets(target: Path) -> None:
    """현재 프리셋 12개를 지정한 경로로 내보낸다."""
    data = load_presets()
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def import_presets(source: Path) -> list[dict]:
    """외부 JSON 을 읽어 검증 후 현재 프리셋으로 적용. 적용된 데이터 반환."""
    with open(source, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("프리셋 파일 형식이 올바르지 않습니다 (배열이 아님).")
    normalized = [_normalize(it) for it in data[:_PRESET_COUNT]]
    while len(normalized) < _PRESET_COUNT:
        normalized.append(dict(DEFAULT_PRESETS[len(normalized)]))
    save_presets(normalized)
    return normalized


# ──────────────────────────────────────────────
# 히스토리 (변경 이력 / 되돌리기)
# ──────────────────────────────────────────────

def _history_path() -> Path:
    return _get_app_folder() / "history.json"


def append_history(entry: dict) -> None:
    """변경 이력 1건 추가. 최신순으로 정렬해 최대 ``_HISTORY_MAX`` 개까지 보관."""
    path = _history_path()
    items: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, list):
            items = loaded
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    entry = dict(entry)
    entry.setdefault("ts", time.time())
    items.insert(0, entry)
    items = items[:_HISTORY_MAX]

    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_history() -> list[dict]:
    try:
        with open(_history_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def pop_last_undoable(adapter: str) -> Optional[dict]:
    """해당 어댑터의 가장 최근(되돌릴 수 있는) 항목을 꺼내고 파일에서 제거."""
    items = load_history()
    for i, e in enumerate(items):
        if e.get("adapter") == adapter and e.get("before") is not None:
            popped = items.pop(i)
            tmp = _history_path().with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            os.replace(tmp, _history_path())
            return popped
    return None
