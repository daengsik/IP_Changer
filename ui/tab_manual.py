"""수동 IP 설정 탭.

책임
  - 어댑터 선택 + 활성/비활성 토글
  - IP / 서브넷 / 게이트웨이 / DNS 입력 + 정적 적용
  - DHCP 전환, 직전 변경 되돌리기
  - 어댑터/설정 변화를 외부(프리셋 탭/편집 다이얼로그)에 알리는 옵저버

하단 상태 줄은 작업 진행("정보 불러오는 중...")과 어댑터 상태("Up · DHCP",
"Disabled — 어댑터 비활성화") 만 짧게 표시한다. IP 값 자체는 입력 필드와
중복이므로 표기하지 않는다.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

import network
import preset
from network import AdapterDetail, IPConfig


_AdapterListener = Callable[["AdapterDetail"], None]


class ManualTab:
    def __init__(self, parent: ttk.Frame):
        self.window: ttk.Window = parent.winfo_toplevel()
        self.current_adapter: Optional[str] = None
        self.current_detail: Optional[AdapterDetail] = None
        self._adapters: list[network.AdapterInfo] = []
        self._listeners: list[_AdapterListener] = []

        self._build_ui(parent)
        self._load_adapters()

    # ──────────────────────────────────────────
    # 외부 옵저버 API
    # ──────────────────────────────────────────

    def add_listener(self, fn: _AdapterListener) -> None:
        self._listeners.append(fn)

    def _notify(self) -> None:
        if self.current_detail is None:
            return
        for fn in self._listeners:
            try:
                fn(self.current_detail)
            except Exception:
                pass

    # ──────────────────────────────────────────
    # UI 구성
    # ──────────────────────────────────────────

    def _build_ui(self, parent: ttk.Frame):
        frame = ttk.Frame(parent, padding=(10, 10))
        frame.pack(fill=BOTH, expand=YES)

        vcmd = (self.window.register(self._validate_ip), "%P", "%S")

        # ── 어댑터 선택 ─────────────────────────
        adpt_lf = ttk.LabelFrame(frame, text="네트워크 어댑터")
        adpt_lf.pack(fill=X, pady=(0, 8))

        top_row = ttk.Frame(adpt_lf)
        top_row.pack(fill=X, padx=8, pady=(6, 4))

        self.adpt_cbo = ttk.Combobox(top_row, state="readonly")
        self.adpt_cbo.pack(side=LEFT, fill=X, expand=YES)
        self.adpt_cbo.bind("<<ComboboxSelected>>", self._on_adapter_selected)

        ttk.Button(
            top_row, text="새로고침",
            bootstyle=(SECONDARY, OUTLINE), width=8,
            command=self._load_adapters,
        ).pack(side=RIGHT, padx=(8, 0))

        toggle_row = ttk.Frame(adpt_lf)
        toggle_row.pack(fill=X, padx=8, pady=(0, 6))

        self.toggle_var = ttk.BooleanVar(value=False)
        self.toggle_btn = ttk.Checkbutton(
            toggle_row,
            text="어댑터 활성화",
            variable=self.toggle_var,
            bootstyle=(SUCCESS, ROUND, TOGGLE),
            command=self._on_toggle,
            state=DISABLED,
        )
        self.toggle_btn.pack(side=LEFT)

        # ── IP 설정 ─────────────────────────────
        ip_lf = ttk.LabelFrame(frame, text="IP 설정")
        ip_lf.pack(fill=X, pady=(0, 8))

        ip_inner = ttk.Frame(ip_lf)
        ip_inner.pack(fill=X, padx=8, pady=6)
        self.ip_entry      = self._make_entry(ip_inner, "IP 주소",         vcmd)
        self.subnet_entry  = self._make_entry(ip_inner, "서브넷 마스크",   vcmd)
        self.gateway_entry = self._make_entry(ip_inner, "기본 게이트웨이", vcmd)

        # ── DNS 설정 ────────────────────────────
        dns_lf = ttk.LabelFrame(frame, text="DNS 설정")
        dns_lf.pack(fill=X, pady=(0, 8))

        dns_inner = ttk.Frame(dns_lf)
        dns_inner.pack(fill=X, padx=8, pady=6)
        self.dns_entry  = self._make_entry(dns_inner, "기본 DNS",   vcmd)
        self.dns2_entry = self._make_entry(dns_inner, "보조 DNS",   vcmd)

        # ── 액션 버튼 ──────────────────────────
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, pady=(2, 0))

        ttk.Button(
            btn_frame, text="적용", bootstyle=PRIMARY, width=10,
            command=self._on_apply,
        ).pack(side=RIGHT, padx=(8, 0))

        ttk.Button(
            btn_frame, text="DHCP", bootstyle=(SUCCESS, OUTLINE), width=10,
            command=self._on_dhcp,
        ).pack(side=RIGHT)

        self.undo_btn = ttk.Button(
            btn_frame, text="되돌리기", bootstyle=(WARNING, OUTLINE), width=10,
            command=self._on_undo,
            state=DISABLED,
        )
        self.undo_btn.pack(side=LEFT)

        # ── 상태 줄 ────────────────────────────
        # 로드 중 / 어댑터 상태(Up·DHCP·APIPA) / 작업 결과 메시지를 한 줄로 표시.
        # IP 값은 입력 필드와 중복이므로 여기엔 넣지 않는다.
        self.status_lbl = ttk.Label(frame, text="", style="Caption.TLabel")
        self.status_lbl.pack(fill=X, pady=(8, 0))

        self._all_entries = [
            self.ip_entry, self.subnet_entry, self.gateway_entry,
            self.dns_entry, self.dns2_entry,
        ]

    @staticmethod
    def _make_entry(parent, label_text: str, vcmd) -> ttk.Entry:
        row = ttk.Frame(parent)
        row.pack(fill=X, pady=3)
        ttk.Label(row, text=label_text, width=14, style="Body.TLabel").pack(side=LEFT)
        entry = ttk.Entry(
            row, validate="key", validatecommand=vcmd,
            justify="center", state=DISABLED,
        )
        entry.pack(side=RIGHT, fill=X, expand=YES)
        return entry

    # ──────────────────────────────────────────
    # 어댑터 로드 / 선택
    # ──────────────────────────────────────────

    def _load_adapters(self):
        self._set_status("어댑터 목록 불러오는 중...")
        threading.Thread(target=self._load_adapters_thread, daemon=True).start()

    def _load_adapters_thread(self):
        adapters = network.get_adapters()
        self.window.after(0, lambda: self._on_adapters_loaded(adapters))

    def _on_adapters_loaded(self, adapters: list[network.AdapterInfo]):
        self._adapters = adapters
        labels = [a.display_label for a in adapters]
        self.adpt_cbo.configure(values=labels)
        if labels:
            # 새로고침 후에도 사용자가 보던 어댑터를 그대로 유지
            target_idx = 0
            if self.current_adapter:
                for i, a in enumerate(adapters):
                    if a.name == self.current_adapter:
                        target_idx = i
                        break
            self.adpt_cbo.current(target_idx)
            self._start_fetch(adapters[target_idx].name)
        else:
            self._set_status("네트워크 어댑터를 찾을 수 없습니다.")

    def _on_adapter_selected(self, _event):
        idx = self.adpt_cbo.current()
        if idx < 0 or idx >= len(self._adapters):
            return
        self._start_fetch(self._adapters[idx].name)

    # ──────────────────────────────────────────
    # IP 정보 조회 & UI 반영 (백그라운드)
    # ──────────────────────────────────────────

    def _start_fetch(self, adapter_name: str):
        self.current_adapter = adapter_name
        self._set_status("정보 불러오는 중...")
        threading.Thread(
            target=self._fetch_thread, args=(adapter_name,), daemon=True
        ).start()

    def _fetch_thread(self, adapter_name: str):
        detail = network.get_adapter_detail(adapter_name)
        self.window.after(0, lambda: self._apply_detail(detail))

    def _apply_detail(self, detail: AdapterDetail):
        self.current_detail = detail
        info = detail.info
        cfg = detail.config
        is_enabled = info.status != "Disabled"

        self.toggle_var.set(is_enabled)
        self.toggle_btn.configure(state=NORMAL)

        for e in self._all_entries:
            e.configure(state="normal")
            e.delete(0, END)

        if is_enabled and cfg:
            self.ip_entry.insert(0, cfg.ip)
            self.subnet_entry.insert(0, cfg.subnet)
            self.gateway_entry.insert(0, cfg.gateway)
            self.dns_entry.insert(0, cfg.primary_dns)
            self.dns2_entry.insert(0, cfg.secondary_dns)

            mode = "DHCP" if cfg.is_dhcp else "정적 IP"
            parts = [info.status, mode]
            if cfg.is_apipa:
                parts.append("APIPA — 외부 통신 불가")
            elif not cfg.ip:
                parts.append("IP 미할당")
            self._set_status("  ·  ".join(parts))
        else:
            for e in self._all_entries:
                e.configure(state=DISABLED)
            self._set_status(f"{info.status} — 어댑터 비활성화")

        # 되돌리기 가능 여부
        history = preset.load_history()
        can_undo = any(
            e.get("adapter") == info.name and e.get("before") is not None
            for e in history
        )
        self.undo_btn.configure(state=(NORMAL if can_undo else DISABLED))

        self._notify()

    def refresh(self):
        if self.current_adapter:
            self._start_fetch(self.current_adapter)

    def get_current_config(self) -> Optional[IPConfig]:
        if self.current_detail and self.current_detail.config:
            return self.current_detail.config
        return None

    # ──────────────────────────────────────────
    # 이벤트 — 토글 / 적용 / DHCP / 되돌리기
    # ──────────────────────────────────────────

    def _on_toggle(self):
        if not self.current_adapter:
            return
        adapter = self.current_adapter
        want_enable = self.toggle_var.get()
        action = "활성화" if want_enable else "비활성화"
        self._set_status(f"{action} 중...")

        def worker():
            if want_enable:
                ok, msg = network.enable_adapter(adapter)
            else:
                ok, msg = network.disable_adapter(adapter)
            if ok:
                self.window.after(0, lambda: self._set_status(f"어댑터 {action}됨"))
                self.window.after(150, self.refresh)
            else:
                self.window.after(0, lambda: self._toggle_failed(action, msg, want_enable))
        threading.Thread(target=worker, daemon=True).start()

    def _toggle_failed(self, action: str, msg: str, attempted: bool):
        self._set_status(f"{action} 실패: {msg}")
        self.toggle_var.set(not attempted)

    def _collect_input(self) -> Optional[dict]:
        """입력 필드를 읽어 검증 후 dict 반환. 실패 시 None + 메시지박스."""
        ip      = self.ip_entry.get().strip()
        subnet  = self.subnet_entry.get().strip()
        gateway = self.gateway_entry.get().strip()
        dns1    = self.dns_entry.get().strip()
        dns2    = self.dns2_entry.get().strip()

        if not ip or not subnet:
            Messagebox.show_warning(
                "IP 주소와 서브넷 마스크는 필수입니다.", "입력 오류")
            return None
        if not network.is_valid_ip(ip):
            Messagebox.show_warning("IP 주소 형식이 올바르지 않습니다.", "입력 오류")
            return None
        if not network.is_valid_subnet(subnet):
            Messagebox.show_warning(
                "서브넷 마스크가 올바르지 않습니다.\n(예: 255.255.255.0)", "입력 오류")
            return None
        if gateway and not network.is_valid_ip(gateway):
            Messagebox.show_warning("게이트웨이 IP 형식이 올바르지 않습니다.", "입력 오류")
            return None
        if gateway and not network.is_same_subnet(ip, gateway, subnet):
            ans = Messagebox.yesno(
                "게이트웨이가 IP/서브넷과 다른 네트워크에 있습니다.\n"
                "그래도 적용하시겠습니까?",
                "경고",
            )
            if str(ans).strip().lower() not in ("yes", "예", "y"):
                return None
        for d in (dns1, dns2):
            if d and not network.is_valid_ip(d):
                Messagebox.show_warning("DNS 형식이 올바르지 않습니다.", "입력 오류")
                return None

        return {
            "ip": ip,
            "subnet": subnet,
            "gateway": gateway,
            "dns": [x for x in (dns1, dns2) if x],
        }

    def _on_apply(self):
        if not self.current_adapter:
            Messagebox.show_warning("어댑터를 선택하세요.", "경고")
            return
        data = self._collect_input()
        if not data:
            return

        before = self.get_current_config()
        adapter = self.current_adapter

        self._set_status("적용 중...")
        threading.Thread(
            target=self._apply_static_thread,
            args=(adapter, data, before),
            daemon=True,
        ).start()

    def _apply_static_thread(
        self, adapter: str, data: dict, before: Optional[IPConfig]
    ):
        # 변경하려는 IP 가 이미 응답하는지(IP 충돌) ping 1회로 사전 감지.
        # 같은 IP 로 재적용하는 경우(before.ip == data["ip"])는 의미가 없으므로 건너뜀.
        if before is None or before.ip != data["ip"]:
            if network.is_ip_in_use(data["ip"], timeout_ms=400):
                proceed = {"v": False}
                def ask():
                    ans = Messagebox.yesno(
                        f"{data['ip']} 가 이미 네트워크에서 응답합니다.\n"
                        "그래도 적용하시겠습니까?", "IP 충돌 경고",
                    )
                    proceed["v"] = str(ans).strip().lower() in ("yes", "예", "y")
                self.window.after(0, ask)
                # 사용자의 응답을 폴링으로 대기 — Messagebox 가 modal 이라 다른 동기화 수단 사용 시
                # 데드락 위험이 있어 단순 폴링이 가장 안전.
                import time
                t0 = time.time()
                while time.time() - t0 < 60:
                    if proceed["v"]:
                        break
                    time.sleep(0.1)
                if not proceed["v"]:
                    self.window.after(0, lambda: self._set_status("취소되었습니다."))
                    return

        ok, msg = network.apply_static_ipv4(
            adapter, data["ip"], data["subnet"], data["gateway"], data["dns"]
        )
        if ok:
            preset.append_history({
                "action": "static",
                "adapter": adapter,
                "before": network.ipconfig_to_dict(before),
                "after": {
                    "ip": data["ip"], "subnet": data["subnet"],
                    "gateway": data["gateway"], "dns": data["dns"],
                    "is_dhcp": False,
                },
            })
            self.window.after(0, lambda: self._set_status("IP 설정이 적용되었습니다."))
            self.window.after(150, self.refresh)
        else:
            self.window.after(
                0, lambda: Messagebox.show_error(f"적용 실패:\n{msg}", "오류")
            )
            self.window.after(0, lambda: self._set_status("적용 실패"))

    def _on_dhcp(self):
        if not self.current_adapter:
            Messagebox.show_warning("어댑터를 선택하세요.", "경고")
            return
        before = self.get_current_config()
        adapter = self.current_adapter
        self._set_status("DHCP 설정 중...")
        threading.Thread(
            target=self._dhcp_thread, args=(adapter, before), daemon=True
        ).start()

    def _dhcp_thread(self, adapter: str, before: Optional[IPConfig]):
        ok, msg = network.apply_dhcp(adapter)
        if ok:
            preset.append_history({
                "action": "dhcp",
                "adapter": adapter,
                "before": network.ipconfig_to_dict(before),
                "after": {"is_dhcp": True},
            })
            self.window.after(0, lambda: self._set_status("DHCP가 적용되었습니다."))
            self.window.after(150, self.refresh)
        else:
            self.window.after(
                0, lambda: Messagebox.show_error(f"DHCP 설정 실패:\n{msg}", "오류")
            )

    def _on_undo(self):
        if not self.current_adapter:
            return
        entry = preset.pop_last_undoable(self.current_adapter)
        if not entry:
            Messagebox.show_info("되돌릴 변경 이력이 없습니다.", "안내")
            return
        before = network.ipconfig_from_dict(entry.get("before"))
        if not before:
            Messagebox.show_warning(
                "이전 설정 정보가 손상되어 되돌릴 수 없습니다.", "되돌리기 실패")
            return

        adapter = self.current_adapter
        self._set_status("이전 설정으로 되돌리는 중...")

        def worker():
            if before.is_dhcp:
                ok, msg = network.apply_dhcp(adapter)
            else:
                ok, msg = network.apply_static_ipv4(
                    adapter, before.ip, before.subnet, before.gateway, list(before.dns)
                )
            if ok:
                self.window.after(0, lambda: self._set_status("이전 설정으로 복원됨"))
                self.window.after(150, self.refresh)
            else:
                self.window.after(
                    0, lambda: Messagebox.show_error(f"되돌리기 실패:\n{msg}", "오류")
                )
        threading.Thread(target=worker, daemon=True).start()

    # ──────────────────────────────────────────
    # 외부에서 호출 (프리셋 탭 / 트레이 메뉴)
    # ──────────────────────────────────────────

    def apply_from_preset(
        self, ip: str, subnet: str, gateway: str, dns: str | list[str]
    ):
        if not self.current_adapter:
            Messagebox.show_warning(
                "어댑터를 먼저 선택하세요.", "경고")
            return
        dns_list = dns if isinstance(dns, list) else [d for d in [dns] if d]
        data = {"ip": ip, "subnet": subnet, "gateway": gateway, "dns": dns_list}
        before = self.get_current_config()
        adapter = self.current_adapter
        self._set_status("프리셋 적용 중...")
        threading.Thread(
            target=self._apply_static_thread,
            args=(adapter, data, before),
            daemon=True,
        ).start()

    # ──────────────────────────────────────────
    # 유틸
    # ──────────────────────────────────────────

    def _set_status(self, text: str):
        self.status_lbl.configure(text=text)

    @staticmethod
    def _validate_ip(value: str, char: str) -> bool:
        """변경 후 전체 값(`%P`) 만으로 검증.

        한 글자(`%S`) 단위로 검사하면 `entry.insert(0, "192.168.1.100")` 같은
        멀티 문자 삽입이 통째로 거부되어 필드가 비는 부작용이 있다(붙여넣기·자동 채움도 동일).
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
