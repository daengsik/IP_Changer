"""중앙 집중식 스타일/폰트 토큰.

설계 원칙
  - 모든 폰트·여백·뱃지 색은 여기에서 등록한 ttk Style 이름으로만 참조한다.
    각 위젯에서 `font="-size 9"` 같은 매직 넘버를 박지 않는다.
  - 등록된 스타일은 ttk Style 이 테마 단위로 캐시하므로 테마 전환 시
    재등록을 호출해야 신 테마 색이 반영된다. `register_styles()` 를 한 번,
    그리고 테마 콤보 변경 핸들러에서 다시 한 번 호출한다.
  - 폰트 크기 자체는 DPI 와 무관한 포인트 단위(`-size N`) 로 지정한다.
    Tk 가 OS DPI 배율에 맞춰 포인트→픽셀 변환을 자동 수행한다.
"""

from __future__ import annotations

import tkinter.font as tkfont
import ttkbootstrap as ttk
from ttkbootstrap.style import Colors


# 폰트 토큰 — 포인트 단위 (DPI 자동 환산)
FONT_TITLE_SIZE = 18    # 큰 헤더
FONT_HEADING_SIZE = 11  # LabelFrame 등 그룹 헤더
FONT_BODY_SIZE = 10     # 일반 라벨/엔트리
FONT_CAPTION_SIZE = 9   # 작은 상태 메시지
FONT_FOOTER_SIZE = 8    # 푸터 작은 글씨


def _font_family(style: ttk.Style) -> str:
    """현재 테마의 기본 폰트 패밀리를 사용 — OS 와 일관."""
    try:
        return tkfont.nametofont("TkDefaultFont").actual("family")
    except Exception:
        return "Segoe UI"


def register_styles(style: ttk.Style | None = None) -> None:
    """앱 전역에서 사용하는 ttk 스타일을 등록한다. 테마 변경 후에는 재호출 필요."""
    style = style or ttk.Style()
    fam = _font_family(style)

    style.configure("Title.TLabel",   font=(fam, FONT_TITLE_SIZE, "bold"))
    style.configure("Heading.TLabel", font=(fam, FONT_HEADING_SIZE, "bold"))
    style.configure("Body.TLabel",    font=(fam, FONT_BODY_SIZE))
    style.configure("Caption.TLabel", font=(fam, FONT_CAPTION_SIZE))
    style.configure("Footer.TLabel",  font=(fam, FONT_FOOTER_SIZE))

    style.configure("Mono.TLabel",
                    font=("Consolas", FONT_BODY_SIZE))

    # 어댑터 상태 뱃지 — 테마 색을 그대로 활용해 다크/라이트 모두 자연스러움
    style.configure("BadgeSuccess.TLabel",
                    foreground=style.colors.success,
                    font=(fam, FONT_CAPTION_SIZE, "bold"))
    style.configure("BadgeWarning.TLabel",
                    foreground=style.colors.warning,
                    font=(fam, FONT_CAPTION_SIZE, "bold"))
    style.configure("BadgeDanger.TLabel",
                    foreground=style.colors.danger,
                    font=(fam, FONT_CAPTION_SIZE, "bold"))
    style.configure("BadgeInfo.TLabel",
                    foreground=style.colors.info,
                    font=(fam, FONT_CAPTION_SIZE, "bold"))
    style.configure("BadgeSecondary.TLabel",
                    foreground=style.colors.secondary,
                    font=(fam, FONT_CAPTION_SIZE, "bold"))

    # 프리셋 카드(이름+IP 두 줄, 각각 다른 폰트 크기) — Frame + Label 조합이라
    # 버튼과 달리 텍스트 길이가 카드 크기에 영향을 주지 않는다.
    # 기본 배경은 테마 primary 색(예전 ttk.Button DEFAULT 와 동일한 느낌),
    # 현재 적용된 프리셋만 secondary 색으로 구분한다.
    base_bg = style.colors.primary
    base_fg = style.colors.get_foreground("primary")
    active_bg = style.colors.secondary
    active_fg = style.colors.get_foreground("secondary")
    hover_bg = Colors.make_transparent(0.85, base_bg, style.colors.bg)

    style.configure("PresetCard.TFrame",
                    relief="raised", borderwidth=1,
                    background=base_bg)
    style.configure("PresetCardActive.TFrame",
                    relief="raised", borderwidth=2,
                    background=active_bg)
    style.configure("PresetCardHover.TFrame",
                    relief="raised", borderwidth=1,
                    background=hover_bg)

    style.configure("PresetCardName.TLabel",
                    font=(fam, FONT_BODY_SIZE, "bold"),
                    background=base_bg, foreground=base_fg)
    style.configure("PresetCardNameActive.TLabel",
                    font=(fam, FONT_BODY_SIZE, "bold"),
                    background=active_bg, foreground=active_fg)
    style.configure("PresetCardNameHover.TLabel",
                    font=(fam, FONT_BODY_SIZE, "bold"),
                    background=hover_bg, foreground=base_fg)

    style.configure("PresetCardIP.TLabel",
                    font=("Consolas", FONT_FOOTER_SIZE),
                    background=base_bg, foreground=base_fg)
    style.configure("PresetCardIPActive.TLabel",
                    font=("Consolas", FONT_FOOTER_SIZE),
                    background=active_bg, foreground=active_fg)
    style.configure("PresetCardIPHover.TLabel",
                    font=("Consolas", FONT_FOOTER_SIZE),
                    background=hover_bg, foreground=base_fg)


def status_badge_style(status: str) -> str:
    """어댑터 상태 문자열을 ttk 스타일 이름으로 매핑."""
    s = (status or "").strip().lower()
    if s == "up":
        return "BadgeSuccess.TLabel"
    if s == "disabled":
        return "BadgeDanger.TLabel"
    if s == "disconnected":
        return "BadgeWarning.TLabel"
    return "BadgeSecondary.TLabel"


def mode_badge_style(is_dhcp: bool) -> str:
    return "BadgeInfo.TLabel" if is_dhcp else "BadgeSecondary.TLabel"
