"""종료 확인 다이얼로그 — 미니멀 명세.

레이아웃
  ┌──────────────────────────────┐
  │  프로그램 종료               │
  │                              │
  │  [ ] 다시 묻지 않기          │
  │                              │
  │      [ 트레이 ] [ 완전종료 ] │
  └──────────────────────────────┘

X 또는 Esc 로 닫으면 "취소"(None) 가 반환된다.

"다시 묻지 않기" 를 체크해서 갇히더라도 사용자는 메인 창 헤더의 ⚙ 메뉴
또는 트레이 아이콘 우클릭 메뉴에서 언제든 선호도를 되돌릴 수 있다.
"""

from __future__ import annotations

from typing import Literal, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *


CloseAction = Literal["minimize", "exit"]


class CloseConfirmDialog:
    def __init__(self, parent: ttk.Window):
        self.top = ttk.Toplevel(parent)
        self.top.title("프로그램 종료")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)

        self.result: Optional[CloseAction] = None
        self.remember = False

        self._remember_var = ttk.BooleanVar(value=False)

        self._build_ui()
        self._autosize_and_center(parent)

        self.top.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.top.bind("<Escape>", lambda _e: self._on_cancel())

    # ──────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────

    def _build_ui(self):
        body = ttk.Frame(self.top, padding=(24, 20, 24, 8))
        body.pack(fill=BOTH, expand=YES)

        ttk.Label(
            body,
            text="프로그램 종료",
            style="Heading.TLabel",
        ).pack(anchor="w")

        ttk.Checkbutton(
            body,
            text="다시 묻지 않기",
            variable=self._remember_var,
        ).pack(anchor="w", pady=(14, 0))

        # ── 버튼 ────────────────────────────────
        btn_bar = ttk.Frame(self.top, padding=(24, 12, 24, 18))
        btn_bar.pack(fill=X)

        # 우측 정렬: [완전종료] [트레이]  (오른쪽 끝이 가장 강조)
        ttk.Button(
            btn_bar, text="완전 종료",
            bootstyle=(DANGER, OUTLINE), width=10,
            command=lambda: self._choose("exit"),
        ).pack(side=RIGHT, padx=(8, 0))

        ttk.Button(
            btn_bar, text="트레이",
            bootstyle=PRIMARY, width=10,
            command=lambda: self._choose("minimize"),
        ).pack(side=RIGHT)

    def _autosize_and_center(self, parent: ttk.Window):
        self.top.update_idletasks()
        w = self.top.winfo_reqwidth()
        h = self.top.winfo_reqheight()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
        except Exception:
            sw = self.top.winfo_screenwidth()
            sh = self.top.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
        self.top.geometry(f"{w}x{h}+{x}+{y}")

    # ──────────────────────────────────────────
    # 핸들러
    # ──────────────────────────────────────────

    def _choose(self, action: CloseAction):
        self.result = action
        self.remember = bool(self._remember_var.get())
        self.top.destroy()

    def _on_cancel(self):
        self.result = None
        self.remember = False
        self.top.destroy()
