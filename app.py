"""메인 윈도우 — 탭 컨테이너, 헤더, 트레이(위젯 모드) 통합.

주요 책임
  - 윈도우 geometry(크기/위치) 저장·복원
  - 테마 전환 시 커스텀 스타일 재등록 (ttk 캐시가 테마 단위로 비워짐)
  - X 버튼 → `_on_close_request` 가 사용자 선호("ask"/"minimize"/"exit")로 분기
  - 트레이에서 들어오는 콜백을 메인 스레드로 디스패치
"""

from __future__ import annotations

import re
import tkinter as tk
from typing import Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

import network
import preset
from ui import styles
from ui.tab_manual import ManualTab
from ui.tab_preset import PresetTab


# 저장된 geometry 문자열 패턴: "WIDTHxHEIGHT+X+Y" (음수 X/Y 허용 — 다중 모니터)
_GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$")

# 종료 동작 라벨/값 매핑 — ⚙ 메뉴와 트레이 메뉴 공용
CLOSE_ACTION_LABELS: dict[str, str] = {
    "ask":      "매번 묻기",
    "minimize": "트레이로 내리기",
    "exit":     "완전 종료",
}


_FALLBACK_THEME = "litera"


def _valid_themes() -> set[str]:
    """ttkbootstrap 내장 테마 이름 집합. import 실패 시 빈 집합."""
    try:
        from ttkbootstrap.themes.standard import STANDARD_THEMES
        return set(STANDARD_THEMES.keys())
    except Exception:
        return set()


def _resolve_theme(requested: str) -> str:
    valid = _valid_themes()
    if valid:
        return requested if requested in valid else _FALLBACK_THEME
    # 목록을 못 가져온 경우엔 일단 요청대로 시도 — 실패하면 ttk.Window 가 예외를 던진다
    return requested


class IPChangerApp:
    def __init__(self):
        preset.init_presets()

        cfg = preset.load_config()
        requested = cfg.get("theme", _FALLBACK_THEME)
        applied = _resolve_theme(requested)
        if applied != requested:
            # 잘못된 값은 디스크에서도 정상화 — 매 실행마다 폴백하지 않도록
            preset.save_config({**cfg, "theme": applied})

        self.window = ttk.Window(
            title="IP Changer",
            themename=applied,
            resizable=(True, True),
            minsize=(380, 480),
        )

        # 탭/트레이 핸들 — _build_ui 이전에 미리 None 으로 잡아 둔다.
        # tray.TrayController 가 self.manual_tab 을 참조하므로 속성 자체는 존재해야 함.
        self.manual_tab: Optional[ManualTab] = None
        self.preset_tab: Optional[PresetTab] = None
        self.tray = None  # tray.TrayController | None

        # PowerShell 세션 콜드 스타트(1~2s)를 UI 빌드와 병행해 숨긴다.
        network.warmup_session_async()

        styles.register_styles(ttk.Style())
        self._build_ui()
        self._restore_geometry()

        # 트레이 실패는 치명적이지 않다 — 그 경우 X 는 곧장 완전 종료로 폴백된다.
        self._init_tray()

        self.window.protocol("WM_DELETE_WINDOW", self._on_close_request)

    # ──────────────────────────────────────────
    # 윈도우 geometry — 저장/복원
    # ──────────────────────────────────────────

    def _restore_geometry(self) -> None:
        """저장된 geometry 가 현재 화면에 들어맞으면 복원, 아니면 자연 크기 + 중앙 배치."""
        cfg = preset.load_config()
        saved = cfg.get("window_geometry")
        if isinstance(saved, str) and self._geometry_fits_screen(saved):
            self.window.geometry(saved)
            return
        self._autosize_and_center()

    def _autosize_and_center(self) -> None:
        win = self.window
        win.update_idletasks()
        win.geometry("")
        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        # 화면 90% 캡 — 극단적 저해상도/큰 폰트 환경에서도 창이 화면을 벗어나지 않게
        w = min(w, int(screen_w * 0.9))
        h = min(h, int(screen_h * 0.9))
        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _geometry_fits_screen(self, geom: str) -> bool:
        """저장된 geometry 가 현재 화면 안에 합리적으로 들어오는지 검증.

        외부 모니터에서 저장한 위치는 모니터를 떼면 화면 밖이 된다. 그런 경우엔
        무시하고 자연 크기 + 중앙 배치로 폴백한다.
        """
        m = _GEOMETRY_RE.match(geom.strip())
        if not m:
            return False
        try:
            w, h, x, y = int(m[1]), int(m[2]), int(m[3]), int(m[4])
        except ValueError:
            return False
        if w < 200 or h < 200:
            return False
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        # 창의 50px 이상이 화면 안에 보이면 허용 (음수 좌표는 다중 모니터 정상 케이스)
        if x + w < 50 or y + h < 50:
            return False
        if x > sw - 50 or y > sh - 50:
            return False
        if w > sw or h > sh:
            return False
        return True

    def _save_geometry(self) -> None:
        try:
            geom = self.window.geometry()
        except Exception:
            return
        if not _GEOMETRY_RE.match(geom.strip()):
            return
        try:
            preset.save_config({**preset.load_config(), "window_geometry": geom})
        except OSError:
            pass

    # ──────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────

    def _build_ui(self):
        root = ttk.Frame(self.window, padding=(12, 12))
        root.pack(fill=BOTH, expand=YES)

        # ── 헤더 ──────────────────────────────
        header = ttk.Frame(root)
        header.pack(fill=X)

        ttk.Label(header, text="IP Changer", style="Title.TLabel").pack(side=LEFT)

        # 우측: 테마 선택 + ⚙ 설정 메뉴
        theme_box = ttk.Frame(header)
        theme_box.pack(side=RIGHT)

        ttk.Label(theme_box, text="테마", style="Caption.TLabel").pack(side=LEFT, padx=(0, 6))

        style = ttk.Style()
        theme_names = style.theme_names()
        self.theme_cbo = ttk.Combobox(
            theme_box, values=theme_names, state="readonly", width=14,
        )
        self.theme_cbo.current(theme_names.index(style.theme.name))
        self.theme_cbo.pack(side=LEFT)
        self.theme_cbo.bind("<<ComboboxSelected>>", self._on_theme_change)

        self._build_settings_menu(theme_box)

        ttk.Separator(root).pack(fill=X, pady=10)

        # ── 탭 ────────────────────────────────
        nb = ttk.Notebook(root)
        nb.pack(fill=BOTH, expand=YES)

        manual_frame = ttk.Frame(nb)
        preset_frame = ttk.Frame(nb)
        nb.add(manual_frame, text="  수동 설정  ")
        nb.add(preset_frame, text="  프리셋  ")

        self.manual_tab = ManualTab(manual_frame)
        self.preset_tab = PresetTab(preset_frame, self.manual_tab)

        # ── 푸터 ──────────────────────────────
        footer = ttk.Frame(root)
        footer.pack(fill=X, pady=(8, 0))
        ttk.Label(
            footer, text="made by daengsik  v2.2",
            style="Footer.TLabel",
            bootstyle=SECONDARY,
        ).pack(side=LEFT)

    # ──────────────────────────────────────────
    # ⚙ 설정 메뉴 — "다시 묻지 않기" 를 되돌리는 진입점
    # ──────────────────────────────────────────

    def _build_settings_menu(self, parent: ttk.Frame) -> None:
        # ttk.Menubutton 은 (SECONDARY, LINK) 같은 LINK 합성 스타일을 거부한다
        # (TclError: Layout secondary link not found). OUTLINE 만 허용된다.
        btn = ttk.Menubutton(parent, text="⚙", bootstyle=(SECONDARY, OUTLINE), width=3)
        btn.pack(side=LEFT, padx=(6, 0))

        menu = tk.Menu(btn, tearoff=False)
        btn["menu"] = menu

        current = preset.load_config().get("close_action") or "ask"
        self._close_action_var = tk.StringVar(value=current)

        close_menu = tk.Menu(menu, tearoff=False)
        for value, label in CLOSE_ACTION_LABELS.items():
            close_menu.add_radiobutton(
                label=label,
                value=value,
                variable=self._close_action_var,
                command=lambda v=value: self._set_close_action(v),
            )
        menu.add_cascade(label="X 버튼 동작", menu=close_menu)

    def _set_close_action(self, value: str) -> None:
        """X 버튼 동작 선호도를 갱신하고 ⚙ 메뉴/트레이 메뉴를 동기화."""
        if value not in CLOSE_ACTION_LABELS:
            return
        cfg = preset.load_config()
        if value == "ask":
            # "매번 묻기" = 미설정 상태로 환원. 키를 지워 의도를 명확히 표현.
            cfg.pop("close_action", None)
            preset.save_config(cfg)
        else:
            preset.save_config({**cfg, "close_action": value})
        try:
            self._close_action_var.set(value)
        except Exception:
            pass
        if self.tray is not None:
            self.tray.refresh_menu()

    def get_close_action(self) -> str:
        """현재 저장된 close_action — 'ask' / 'minimize' / 'exit'."""
        return preset.load_config().get("close_action") or "ask"

    def _on_theme_change(self, _event):
        theme = self.theme_cbo.get()
        style = ttk.Style()
        style.theme_use(theme)
        # 테마 전환 시 ttk 의 스타일 캐시가 비워지므로 커스텀 스타일을 다시 등록해야 한다.
        styles.register_styles(style)
        preset.save_config({**preset.load_config(), "theme": theme})
        try:
            if self.manual_tab and self.manual_tab.current_detail:
                self.manual_tab._apply_detail(self.manual_tab.current_detail)
            if self.preset_tab:
                self.preset_tab.reload()
        except Exception:
            pass

    # ──────────────────────────────────────────
    # 트레이(위젯 모드)
    # ──────────────────────────────────────────

    def _init_tray(self) -> None:
        """`tray.TrayController` 를 안전하게 기동. 실패하면 self.tray = None."""
        try:
            from tray import TrayController
            self.tray = TrayController(self)
            self.tray.start()
            if not self.tray.running:
                self.tray = None
            else:
                # 프리셋 데이터가 바뀔 때마다 트레이 메뉴도 같이 갱신
                if self.preset_tab is not None:
                    self.preset_tab.set_on_change(self._refresh_tray_menu)
        except Exception:
            self.tray = None

    def _refresh_tray_menu(self) -> None:
        if self.tray is not None:
            self.tray.refresh_menu()

    def _tray_available(self) -> bool:
        return self.tray is not None and self.tray.running

    def show_window(self) -> None:
        """트레이에서 메인 창을 다시 띄운다."""
        try:
            self.window.deiconify()
            self.window.state("normal")
            self.window.lift()
            self.window.focus_force()
            # 트레이로 내려가 있는 동안 어댑터 상태가 외부에서 바뀌었을 수 있어 1회 갱신
            if self.manual_tab:
                self.manual_tab.refresh()
        except Exception:
            pass

    def minimize_to_tray(self) -> None:
        """메인 창을 숨겨 트레이로 내림. 프로세스/PS 세션/뮤텍스는 모두 유지된다."""
        self._save_geometry()
        try:
            self.window.withdraw()
        except Exception:
            pass

    def apply_preset_from_tray(self, idx: int) -> None:
        """트레이 메뉴에서 선택한 프리셋을 창을 열지 않고 곧장 적용.

        어댑터가 아직 선택되지 않았다면 창을 띄워 사용자에게 안내한다.
        """
        if self.manual_tab is None:
            return
        if not self.manual_tab.current_adapter:
            self.show_window()
            Messagebox.show_warning(
                "어댑터가 선택되지 않았습니다. 수동 설정 탭에서 어댑터를 먼저 선택하세요.",
                "트레이 프리셋",
            )
            return
        data = preset.load_presets()
        if idx >= len(data):
            return
        p = data[idx]
        if not p["ip_addr"]:
            return  # 빈 프리셋은 메뉴에서 이미 disabled 지만 방어
        dns = [d for d in (p["dns"],) if d]
        self.manual_tab.apply_from_preset(
            p["ip_addr"], p["subnet"], p["gateway"], dns,
        )

    # ──────────────────────────────────────────
    # 종료 동작
    # ──────────────────────────────────────────

    def _on_close_request(self) -> None:
        """X 버튼 클릭 시 분기:
          - 트레이 불가 → 즉시 완전 종료 (폴백)
          - 선호 "minimize"/"exit" → 즉시 해당 동작
          - 선호 없음("ask") → 다이얼로그로 묻기
        """
        if not self._tray_available():
            self.quit_app()
            return

        pref = self.get_close_action()
        if pref == "minimize":
            self.minimize_to_tray()
            return
        if pref == "exit":
            self.quit_app()
            return

        from ui.dialog_close import CloseConfirmDialog
        dlg = CloseConfirmDialog(self.window)
        self.window.wait_window(dlg.top)
        if dlg.result is None:
            return  # X / Esc 취소
        if dlg.remember:
            self._set_close_action(dlg.result)
        if dlg.result == "minimize":
            self.minimize_to_tray()
        else:
            self.quit_app()

    def quit_app(self) -> None:
        """geometry 저장 → 트레이 정리 → 윈도우 destroy 순서로 완전 종료."""
        # withdraw 상태에서도 geometry 값은 살아있지만, mapped 상태에서만 저장해
        # 다음 실행 시 의도치 않은 위치 복원을 막는다.
        try:
            if self.window.state() != "withdrawn":
                self._save_geometry()
        except Exception:
            pass

        # 트레이는 별도 스레드의 메시지 루프이므로 윈도우 destroy 전에 먼저 stop.
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
            self.tray = None

        # PowerShell 세션은 daemon 스레드라 프로세스 종료와 함께 같이 정리됨.
        try:
            self.window.destroy()
        except Exception:
            pass

    def run(self):
        self.window.mainloop()
