"""프리셋 탭 — 12 개 카드로 원클릭 IP 적용.

UI 원칙
  - 상단에는 적용 대상 어댑터 이름 한 줄만 표기 (예: "적용 대상: 이더넷 3").
  - 각 프리셋 카드는 "이름 / IP" 두 줄만. 부가 정보는 노이즈.
  - 현재 어댑터 IP 와 일치하는 프리셋은 강조해 상태를 시각화.
  - 빈 프리셋은 강조 대상에서 제외하고, 클릭 시 편집 다이얼로그 안내.
  - 카드는 ttk.Button 대신 Frame+Label 조합을 쓴다 — 이름/IP 를 서로 다른
    폰트 크기로 보여줘야 하고(Button 은 텍스트 전체가 단일 폰트),
    긴 이름이 카드 크기를 늘리지 않도록(고정 크기 + 말줄임) 하기 위함이다.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

import network
import preset
from network import AdapterDetail

if TYPE_CHECKING:
    from ui.tab_manual import ManualTab


_NAME_MAX_CHARS = 12
_CARD_WIDTH = 150
_CARD_HEIGHT = 60


def _truncate(text: str, limit: int = _NAME_MAX_CHARS) -> str:
    """limit 을 넘는 텍스트는 앞부분만 남기고 뒤에 ... 을 붙인다."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 1)].rstrip() + "..."


class PresetTab:
    def __init__(self, parent: ttk.Frame, manual_tab: "ManualTab"):
        self.manual_tab = manual_tab
        self.window: ttk.Window = parent.winfo_toplevel()
        self._cards: list[dict] = []
        # 프리셋 데이터 변경(편집 저장)을 외부 한 곳(트레이 메뉴 갱신)에 알리는 콜백.
        # 다중 구독자가 필요해지면 list 로 바꾸면 된다.
        self._on_change: Optional[Callable[[], None]] = None

        self._build_ui(parent)
        self.reload()

        self.manual_tab.add_listener(self._on_adapter_changed)

    # ──────────────────────────────────────────
    # 외부 옵저버 API
    # ──────────────────────────────────────────

    def set_on_change(self, fn: Callable[[], None]) -> None:
        self._on_change = fn

    def _notify_change(self) -> None:
        if self._on_change is not None:
            try:
                self._on_change()
            except Exception:
                pass

    # ──────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────

    def _build_ui(self, parent: ttk.Frame):
        frame = ttk.Frame(parent, padding=(10, 10))
        frame.pack(fill=BOTH, expand=YES)

        # ── 상단: 적용 대상 + 편집 버튼 ──────────
        # RIGHT 버튼을 먼저 패킹해 자기 자리를 확보한 뒤, 좌측 expand 프레임을 패킹.
        top = ttk.Frame(frame)
        top.pack(fill=X, pady=(0, 4))

        ttk.Button(
            top, text="프리셋 편집",
            bootstyle=(SECONDARY, OUTLINE),
            command=self._open_edit_dialog,
        ).pack(side=RIGHT, padx=(8, 0))

        left = ttk.Frame(top)
        left.pack(side=LEFT, fill=X, expand=YES)

        self.adapter_lbl = ttk.Label(
            left, text="적용 대상: (수동 설정 탭에서 어댑터를 선택)",
            style="Caption.TLabel",
        )
        self.adapter_lbl.pack(anchor="w")

        ttk.Separator(frame).pack(fill=X, pady=(0, 8))

        # ── 4행 × 3열 프리셋 카드 그리드 ───────
        # uniform 그룹으로 묶어 모든 칸이 동일한 크기를 갖도록 강제한다.
        # (카드 자체도 고정 크기라 텍스트 길이는 셀 크기에 영향을 주지 않는다.)
        grid = ttk.Frame(frame)
        grid.pack(fill=BOTH, expand=YES)

        for col in range(3):
            grid.columnconfigure(col, weight=1, uniform="preset_col")
        for row in range(4):
            grid.rowconfigure(row, weight=1, uniform="preset_row")

        for idx in range(12):
            row, col = divmod(idx, 3)
            card = self._make_preset_card(grid, idx)
            card["frame"].grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            self._cards.append(card)

    def _make_preset_card(self, parent: ttk.Frame, idx: int) -> dict:
        """이름(진하게, 일반 크기) / IP(작은 폰트) 두 줄을 중앙정렬로 보여주는 카드.

        grid_propagate(False) + 고정 width/height 로 카드의 요구 크기를
        내용과 무관하게 고정한다. 실제 화면 크기는 부모 grid 의 weight/uniform
        배분에 따라 창 크기에 비례해 커진다.
        """
        outer = ttk.Frame(
            parent, style="PresetCard.TFrame",
            width=_CARD_WIDTH, height=_CARD_HEIGHT,
        )
        outer.grid_propagate(False)

        name_lbl = ttk.Label(
            outer, text="", style="PresetCardName.TLabel",
            anchor=CENTER, justify=CENTER,
        )
        name_lbl.pack(fill=X, expand=YES, padx=4, pady=(10, 0))

        ip_lbl = ttk.Label(
            outer, text="", style="PresetCardIP.TLabel",
            anchor=CENTER, justify=CENTER,
        )
        ip_lbl.pack(fill=X, expand=YES, padx=4, pady=(0, 8))

        card = {"frame": outer, "name_lbl": name_lbl, "ip_lbl": ip_lbl, "active": False}

        for widget in (outer, name_lbl, ip_lbl):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", lambda _e, i=idx: self._on_preset_click(i))
            widget.bind("<Enter>", lambda _e, c=card: self._on_card_enter(c))
            widget.bind("<Leave>", lambda _e, c=card: self._on_card_leave(c))

        return card

    def _on_card_enter(self, card: dict):
        if not card["active"]:
            card["frame"].configure(style="PresetCardHover.TFrame")
            card["name_lbl"].configure(style="PresetCardNameHover.TLabel")
            card["ip_lbl"].configure(style="PresetCardIPHover.TLabel")

    def _on_card_leave(self, card: dict):
        if not card["active"]:
            card["frame"].configure(style="PresetCard.TFrame")
            card["name_lbl"].configure(style="PresetCardName.TLabel")
            card["ip_lbl"].configure(style="PresetCardIP.TLabel")

    # ──────────────────────────────────────────
    # 데이터/상태 갱신
    # ──────────────────────────────────────────

    def reload(self):
        """카드 텍스트와 어댑터 요약을 다시 그리고, 외부 옵저버에 변경을 통지."""
        self._refresh_cards()
        self._update_adapter_summary()
        self._notify_change()

    def _refresh_cards(self):
        data = preset.load_presets()
        current_ip = self._current_ip()
        for i, card in enumerate(self._cards):
            if i >= len(data):
                continue
            p = data[i]
            name = _truncate(p["name"] or f"프리셋 {i + 1}")
            ip = p["ip_addr"] or "(비어 있음)"
            card["name_lbl"].configure(text=name)
            card["ip_lbl"].configure(text=ip)
            # 빈 프리셋끼리 빈 문자열로 일치하는 일이 없도록 IP 가 채워졌을 때만 비교
            is_active = (
                bool(current_ip) and bool(p["ip_addr"])
                and current_ip == p["ip_addr"]
            )
            card["active"] = is_active
            card["frame"].configure(
                style="PresetCardActive.TFrame" if is_active else "PresetCard.TFrame")
            card["name_lbl"].configure(
                style="PresetCardNameActive.TLabel" if is_active else "PresetCardName.TLabel")
            card["ip_lbl"].configure(
                style="PresetCardIPActive.TLabel" if is_active else "PresetCardIP.TLabel")

    def _update_adapter_summary(self):
        adapter = self.manual_tab.current_adapter
        if not adapter:
            self.adapter_lbl.configure(
                text="적용 대상: (수동 설정 탭에서 어댑터를 선택)")
            return
        self.adapter_lbl.configure(text=f"적용 대상: {adapter}")

    def _current_ip(self) -> Optional[str]:
        cfg = self.manual_tab.get_current_config()
        return cfg.ip if cfg else None

    def _on_adapter_changed(self, _detail: AdapterDetail):
        self._refresh_cards()
        self._update_adapter_summary()

    # ──────────────────────────────────────────
    # 이벤트
    # ──────────────────────────────────────────

    def _on_preset_click(self, idx: int):
        adapter = self.manual_tab.current_adapter
        if not adapter:
            Messagebox.show_warning(
                "수동 설정 탭에서 어댑터를 먼저 선택하세요.", "경고")
            return

        data = preset.load_presets()
        if idx >= len(data):
            return

        p = data[idx]
        if not p["ip_addr"]:
            Messagebox.show_info(
                f"프리셋 {idx + 1} 은 등록되지 않았습니다.\n"
                "'프리셋 편집' 에서 값을 입력하세요.",
                "안내",
            )
            return

        before = self.manual_tab.get_current_config()
        dns_list = [p["dns"]] if p["dns"] else []

        threading.Thread(
            target=self._apply_thread,
            args=(adapter, p, dns_list, before),
            daemon=True,
        ).start()

    def _apply_thread(self, adapter: str, p: dict, dns_list: list[str], before):
        ok, msg = network.apply_static_ipv4(
            adapter, p["ip_addr"], p["subnet"], p["gateway"], dns_list,
        )
        if ok:
            preset.append_history({
                "action": "preset",
                "adapter": adapter,
                "preset_name": p["name"] or "",
                "before": network.ipconfig_to_dict(before),
                "after": {
                    "ip": p["ip_addr"], "subnet": p["subnet"],
                    "gateway": p["gateway"], "dns": dns_list,
                    "is_dhcp": False,
                },
            })
            # 결과는 manual_tab.refresh 가 입력 필드/상태 줄을 다시 그려 자동 표시.
            self.window.after(150, self.manual_tab.refresh)
        else:
            self.window.after(
                0,
                lambda: Messagebox.show_error(f"프리셋 적용 실패:\n{msg}", "오류"),
            )

    def _open_edit_dialog(self):
        from ui.dialog_edit import PresetEditDialog

        dlg = PresetEditDialog(
            self.window,
            current_adapter=self.manual_tab.current_adapter,
            current_config=self.manual_tab.get_current_config(),
        )
        self.window.wait_window(dlg.top)
        self.reload()
