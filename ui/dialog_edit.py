"""프리셋 편집 다이얼로그.

동작 원칙
  - 진입 시 저장된 12개 프리셋 값을 그대로 입력 필드에 채워 보여 준다.
  - 빈 프리셋(이름/IP/서브넷/GW/DNS 모두 공란)도 저장 가능.
  - 값이 채워진 행은 형식만 엄격 검증.
  - 손댄 행은 라벨에 ● 표시. 변경된 상태로 취소 시 확인 다이얼로그.
  - "현재값 채우기" 로 어댑터의 현재 IP/서브넷/GW/DNS 를 1행에 일괄 삽입.
  - MouseWheel 글로벌 바인딩은 다이얼로그 destroy 시 반드시 해제.
"""

from __future__ import annotations

from typing import Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

import network
import preset
from network import IPConfig


_IP_FIELDS = {"ip_addr", "subnet", "gateway", "dns"}
_LABELS = [
    ("이름",       "name"),
    ("설명",       "desc"),
    ("IP 주소",    "ip_addr"),
    ("서브넷",     "subnet"),
    ("게이트웨이", "gateway"),
    ("DNS",        "dns"),
]
_LBL_W = 10


class PresetEditDialog:
    def __init__(
        self,
        parent: ttk.Window,
        current_adapter: Optional[str] = None,
        current_config: Optional[IPConfig] = None,
    ):
        self.top = ttk.Toplevel(parent)
        self.top.title("프리셋 편집")
        self.top.transient(parent)
        self.top.grab_set()

        self._current_adapter = current_adapter
        self._current_config = current_config

        # 가로 고정/세로 가변 — 폼 길이는 12개 행이라 늘어날 여지가 있다.
        self.top.resizable(False, True)

        self._row_entries: list[dict[str, ttk.Entry]] = []
        self._row_lbls: list[ttk.Label] = []
        self._row_dirty: list[bool] = [False] * 12
        self._original: list[dict] = []

        self._canvas: Optional[ttk.Canvas] = None
        self._mousewheel_bound = False

        self._build_ui()
        self._load_data()
        self._autosize()

        self.top.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.top.bind("<Destroy>", lambda e: self._unbind_mousewheel())

    # ──────────────────────────────────────────
    # 자연 크기 계산
    # ──────────────────────────────────────────

    def _autosize(self):
        """자연 크기를 계산하되 화면 85% 를 넘지 않게 캡, 화면 중앙에 배치."""
        self.top.update_idletasks()
        req_w = self.top.winfo_reqwidth()
        req_h = self.top.winfo_reqheight()
        screen_h = self.top.winfo_screenheight()
        screen_w = self.top.winfo_screenwidth()
        w = min(req_w, int(screen_w * 0.9))
        h = min(req_h, int(screen_h * 0.85))
        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 2)
        self.top.geometry(f"{w}x{h}+{x}+{y}")

    # ──────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────

    def _build_ui(self):
        vcmd = (self.top.register(self._validate_ip), "%P", "%S")

        # ── 상단: 현재 어댑터 요약 ───────────────
        head = ttk.Frame(self.top, padding=(10, 8, 10, 4))
        head.pack(fill=X)
        head.columnconfigure(1, weight=1)

        ttk.Label(head, text="현재 어댑터:", style="Caption.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 6))
        adapter_text = self._current_adapter or "(선택되지 않음)"
        ttk.Label(head, text=adapter_text, style="Body.TLabel").grid(
            row=0, column=1, sticky="w")

        ttk.Label(head, text="현재 IP:", style="Caption.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=(2, 0))
        if self._current_config:
            cfg = self._current_config
            mode = "DHCP" if cfg.is_dhcp else "정적"
            cur_text = (
                f"{cfg.ip}  /  {cfg.subnet}  /  GW {cfg.gateway}"
                f"  ({mode})"
            )
        else:
            cur_text = "—"
        ttk.Label(head, text=cur_text, style="Body.TLabel").grid(
            row=1, column=1, sticky="w", pady=(2, 0))

        ttk.Separator(self.top).pack(fill=X)

        # ── 스크롤 영역 ─────────────────────────
        container = ttk.Frame(self.top)
        container.pack(fill=BOTH, expand=YES, padx=8, pady=(8, 0))

        scrollbar = ttk.Scrollbar(container, orient="vertical")
        scrollbar.pack(side=RIGHT, fill=Y)

        canvas = ttk.Canvas(container, highlightthickness=0, yscrollcommand=scrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.configure(command=canvas.yview)
        self._canvas = canvas

        self._scroll_frame = ttk.Frame(canvas)
        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        frame_id = canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(frame_id, width=e.width),
        )

        # MouseWheel: 커서가 다이얼로그 안에 있을 때만 동작하도록 enter/leave 로 토글.
        # bind_all 은 전역이라 누수되면 메인 창의 다른 스크롤도 흔들리므로 destroy 시 해제 보장.
        def _wheel(ev):
            canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")
        def _on_enter(_e):
            canvas.bind_all("<MouseWheel>", _wheel)
            self._mousewheel_bound = True
        def _on_leave(_e):
            self._unbind_mousewheel()
        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)

        # ── 12개 프리셋 폼 ─────────────────────
        for i in range(12):
            grp = ttk.LabelFrame(self._scroll_frame, text=f"프리셋 {i + 1}")
            grp.pack(fill=X, padx=6, pady=4)

            # 헤더 라벨(변경 표시 ●) + "현재값 채우기" 버튼
            head_row = ttk.Frame(grp)
            head_row.pack(fill=X, padx=8, pady=(4, 2))

            lbl = ttk.Label(head_row, text="", style="Caption.TLabel")
            lbl.pack(side=LEFT)
            self._row_lbls.append(lbl)

            fill_btn = ttk.Button(
                head_row, text="현재값 채우기",
                bootstyle=(INFO, OUTLINE),
                command=lambda idx=i: self._fill_from_current(idx),
                state=(NORMAL if self._current_config else DISABLED),
            )
            fill_btn.pack(side=RIGHT)

            grp_inner = ttk.Frame(grp)
            grp_inner.pack(fill=X, padx=8, pady=(2, 6))
            grp_inner.columnconfigure(1, weight=1)

            entries: dict[str, ttk.Entry] = {}
            for row_idx, (label_text, key) in enumerate(_LABELS):
                ttk.Label(
                    grp_inner, text=label_text, width=_LBL_W, anchor="w",
                    style="Body.TLabel",
                ).grid(row=row_idx, column=0, sticky="w", padx=(0, 6), pady=2)

                if key in _IP_FIELDS:
                    ent = ttk.Entry(grp_inner, validate="key", validatecommand=vcmd)
                else:
                    ent = ttk.Entry(grp_inner)
                ent.grid(row=row_idx, column=1, sticky="ew", pady=2)
                ent.bind(
                    "<KeyRelease>",
                    lambda _ev, idx=i: self._mark_dirty(idx),
                )
                entries[key] = ent

            self._row_entries.append(entries)

        # ── 하단 버튼 ──────────────────────────
        ttk.Separator(self.top, orient=HORIZONTAL).pack(fill=X, side=BOTTOM)

        btn_bar = ttk.Frame(self.top, padding=(8, 6))
        btn_bar.pack(fill=X, side=BOTTOM)

        ttk.Button(
            btn_bar, text="저장", bootstyle=PRIMARY, width=10,
            command=self._save,
        ).pack(side=RIGHT, padx=(8, 0))

        ttk.Button(
            btn_bar, text="취소", bootstyle=(SECONDARY, OUTLINE), width=10,
            command=self._on_cancel,
        ).pack(side=RIGHT)

    def _unbind_mousewheel(self):
        if self._mousewheel_bound and self._canvas is not None:
            try:
                self._canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            self._mousewheel_bound = False

    # ──────────────────────────────────────────
    # 데이터 로드 / 저장
    # ──────────────────────────────────────────

    def _load_data(self):
        data = preset.load_presets()
        self._original = [dict(d) for d in data]
        for i, entries in enumerate(self._row_entries):
            if i < len(data):
                for key, entry in entries.items():
                    entry.delete(0, END)
                    entry.insert(0, data[i].get(key, ""))
            self._row_dirty[i] = False
            self._row_lbls[i].configure(text="")

    def _fill_from_current(self, idx: int):
        """현재 어댑터의 IP/서브넷/GW/DNS 를 idx 번째 행에 채운다. 이름·설명은 보존."""
        if not self._current_config:
            return
        cfg = self._current_config
        e = self._row_entries[idx]
        def set_entry(entry: ttk.Entry, value: str):
            entry.delete(0, END)
            entry.insert(0, value)
        set_entry(e["ip_addr"], cfg.ip)
        set_entry(e["subnet"], cfg.subnet)
        set_entry(e["gateway"], cfg.gateway)
        set_entry(e["dns"], cfg.primary_dns)
        self._mark_dirty(idx)

    def _mark_dirty(self, idx: int):
        self._row_dirty[idx] = True
        self._row_lbls[idx].configure(
            text="● 변경됨", style="BadgeWarning.TLabel"
        )

    def _has_unsaved_changes(self) -> bool:
        return any(self._row_dirty)

    def _collect(self) -> list[dict]:
        return [
            {key: entry.get().strip() for key, entry in entries.items()}
            for entries in self._row_entries
        ]

    def _validate_row(self, row_idx: int, row: dict) -> Optional[str]:
        """행 1개를 검증. 완전히 빈 프리셋은 허용하며, 채워진 값만 형식 검증한다.

        IP 가 있으면 서브넷이 필수 — 둘 중 하나만으론 적용 불가능하기 때문.
        이름이 비어도 OK (목록 표시 시 "프리셋 N" 로 폴백).
        """
        if row["ip_addr"] and not network.is_valid_ip(row["ip_addr"]):
            return f"프리셋 {row_idx + 1}: IP 주소 형식이 올바르지 않습니다."
        if row["subnet"] and not network.is_valid_subnet(row["subnet"]):
            return f"프리셋 {row_idx + 1}: 서브넷 마스크가 올바르지 않습니다."
        if row["gateway"] and not network.is_valid_ip(row["gateway"]):
            return f"프리셋 {row_idx + 1}: 게이트웨이 형식이 올바르지 않습니다."
        if row["dns"] and not network.is_valid_ip(row["dns"]):
            return f"프리셋 {row_idx + 1}: DNS 형식이 올바르지 않습니다."
        if row["ip_addr"] and not row["subnet"]:
            return f"프리셋 {row_idx + 1}: IP 가 입력되었을 때 서브넷 마스크는 필수입니다."
        return None

    def _save(self):
        data = self._collect()
        errors: list[str] = []
        for i, row in enumerate(data):
            err = self._validate_row(i, row)
            if err:
                errors.append(err)
        if errors:
            # 에러가 12개씩 쌓이면 다이얼로그가 너무 길어지므로 앞 8개만 노출
            Messagebox.show_error("\n".join(errors[:8]), "저장 불가")
            return

        try:
            preset.save_presets(data)
            self._unbind_mousewheel()
            Messagebox.show_info("프리셋이 저장되었습니다.", "저장 완료")
            self.top.destroy()
        except OSError as e:
            Messagebox.show_error(f"저장 실패:\n{e}", "오류")

    def _on_cancel(self):
        if self._has_unsaved_changes():
            ans = Messagebox.yesno(
                "변경된 내용이 있습니다. 저장하지 않고 닫을까요?",
                "확인",
            )
            if str(ans).strip().lower() not in ("yes", "예", "y"):
                return
        self._unbind_mousewheel()
        self.top.destroy()

    # ──────────────────────────────────────────
    # 유효성 검증 (키 입력)
    # ──────────────────────────────────────────

    @staticmethod
    def _validate_ip(value: str, char: str) -> bool:
        """변경 후 전체 값(`%P`) 만으로 검증.

        한 글자(`%S`) 단위로 검사하면 `entry.insert(0, "192.168.1.100")` 같은
        멀티 문자 삽입이 통째로 거부되어 필드가 비는 부작용이 있다.
        """
        if not value:
            return True
        parts = value.split(".")
        if len(parts) > 4:
            return False
        for part in parts:
            if part and (not part.isdigit() or int(part) > 255):
                return False
        return True
