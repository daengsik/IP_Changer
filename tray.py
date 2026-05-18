"""시스템 트레이 컨트롤러 — IP Changer 위젯 모드.

설계 포인트
  - pystray.Icon 은 자체 메시지 루프를 돌리므로 별도 데몬 스레드에서 기동.
    tk `mainloop()` 와 충돌하지 않는다.
  - 트레이 콜백은 트레이 스레드에서 호출되므로 tk 위젯을 직접 건드리지 않고,
    모든 UI 조작을 `window.after(0, fn)` 으로 메인 스레드에 디스패치한다.

위젯 모드가 주는 실질 이득
  - UAC 권한 1회, PowerShell 콜드 스타트(1~2s) 1회, 단일 인스턴스 mutex 유지.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable, Optional

import pystray
from PIL import Image, ImageDraw, ImageFont

import preset

if TYPE_CHECKING:
    from app import IPChangerApp


# ──────────────────────────────────────────────
# 트레이 아이콘 이미지
# ──────────────────────────────────────────────

def _make_icon_image(size: int = 64) -> Image.Image:
    """런타임 생성 아이콘 — 파란 사각형 + 흰색 'IP'. 외부 .ico 파일을 두지 않기 위함."""
    img = Image.new("RGBA", (size, size), (0, 120, 215, 255))  # Windows 11 액센트 블루
    draw = ImageDraw.Draw(img)

    font: Optional[ImageFont.ImageFont]
    for candidate in ("seguibl.ttf", "segoeuib.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(candidate, int(size * 0.55))
            break
        except OSError:
            font = None
    if font is None:
        font = ImageFont.load_default()

    text = "IP"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # textbbox 는 baseline 기준 오프셋이 있어 y 를 살짝 위로 보정해야 시각 중앙에 온다.
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1] - int(size * 0.05)
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    return img


# ──────────────────────────────────────────────
# 컨트롤러
# ──────────────────────────────────────────────

class TrayController:
    """앱 인스턴스를 감싸 트레이 아이콘과 메뉴를 관리.

    사용
        tray = TrayController(app)
        tray.start()           # 데몬 스레드에서 아이콘 활성
        tray.refresh_menu()    # 프리셋/선호도 변경 후 호출
        tray.stop()            # 종료 직전
    """

    def __init__(self, app: "IPChangerApp"):
        self.app = app
        self.window = app.window
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ──────────────────────────────────────────
    # 수명 주기
    # ──────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        try:
            image = _make_icon_image()
            self._icon = pystray.Icon(
                name="IPChanger",
                icon=image,
                title=self._tooltip(),
                menu=self._build_menu(),
            )
            # pystray.run_detached 가 일부 환경(Win11 + Python 3.13)에서 즉시 반환되며
            # 트레이가 사라지는 사례가 있어, 직접 데몬 스레드를 띄워 .run() 을 호출한다.
            self._thread = threading.Thread(
                target=self._icon.run, daemon=True, name="ipchanger-tray"
            )
            self._thread.start()
            self._running = True
        except Exception:
            # 트레이 실패는 치명적이지 않다 — 앱은 X = 즉시 종료로 폴백된다.
            self._icon = None
            self._running = False

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
        self._icon = None
        self._running = False

    # ──────────────────────────────────────────
    # 메뉴 / 툴팁
    # ──────────────────────────────────────────

    def refresh_menu(self) -> None:
        """프리셋 데이터/종료 선호도가 바뀌었을 때 트레이 메뉴를 다시 그린다."""
        if self._icon is None:
            return
        try:
            self._icon.menu = self._build_menu()
            self._icon.title = self._tooltip()
            self._icon.update_menu()
        except Exception:
            pass

    def _tooltip(self) -> str:
        adapter = self.app.manual_tab.current_adapter if self.app.manual_tab else None
        cfg = self.app.manual_tab.get_current_config() if self.app.manual_tab else None
        if adapter and cfg and cfg.ip:
            return f"IP Changer\n{adapter}: {cfg.ip}"
        if adapter:
            return f"IP Changer\n{adapter}"
        return "IP Changer"

    def _build_menu(self) -> pystray.Menu:
        presets = preset.load_presets()

        preset_items: list[pystray.MenuItem] = []
        for i, p in enumerate(presets):
            preset_items.append(
                pystray.MenuItem(
                    self._preset_label(i, p),
                    self._make_preset_callback(i),
                    enabled=bool(p.get("ip_addr")),
                )
            )

        # CLOSE_ACTION_LABELS 는 app 모듈에서 정의되며, app → tray 단방향이지만
        # 모듈 로드 순서상 지연 import 로 순환 참조를 회피한다.
        from app import CLOSE_ACTION_LABELS

        close_items: list[pystray.MenuItem] = []
        for value, label in CLOSE_ACTION_LABELS.items():
            close_items.append(
                pystray.MenuItem(
                    label,
                    self._make_close_action_callback(value),
                    # 람다 기본값으로 value 를 캡처해야 루프 변수가 마지막 값으로 덮이지 않는다.
                    checked=lambda _item, v=value: self.app.get_close_action() == v,
                    radio=True,
                )
            )

        return pystray.Menu(
            pystray.MenuItem("열기", self._cb_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("프리셋", pystray.Menu(*preset_items)),
            pystray.MenuItem("X 버튼 동작", pystray.Menu(*close_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self._cb_quit),
        )

    @staticmethod
    def _preset_label(idx: int, p: dict) -> str:
        name = p.get("name") or p.get("desc") or f"프리셋 {idx + 1}"
        ip = p.get("ip_addr") or "(비어 있음)"
        return f"{idx + 1}. {name} — {ip}"

    # ──────────────────────────────────────────
    # 콜백 (트레이 스레드 → 메인 스레드 디스패치)
    # ──────────────────────────────────────────

    def _dispatch(self, fn: Callable[[], None]) -> None:
        """트레이 스레드 → tk 메인 스레드로 콜백을 안전하게 디스패치.

        윈도우가 이미 destroy 된 종료 시점에선 TclError 가 나는데 무시한다.
        """
        try:
            self.window.after(0, fn)
        except Exception:
            pass

    def _cb_show(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._dispatch(self.app.show_window)

    def _cb_quit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._dispatch(self.app.quit_app)

    def _make_preset_callback(self, idx: int):
        def _cb(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
            self._dispatch(lambda: self.app.apply_preset_from_tray(idx))
        return _cb

    def _make_close_action_callback(self, value: str):
        def _cb(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
            self._dispatch(lambda: self.app._set_close_action(value))
        return _cb
