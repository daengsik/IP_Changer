"""IP Changer 진입점.

기동 순서
  1) UAC 권한 확인/승격 — 승격이 필요하면 절대경로 + cwd 를 명시한 ShellExecute.
     (cwd 가 None 이면 elevated 프로세스가 system32 에서 시작되어 `__main__.py`
      를 못 찾고 즉시 죽는 사고가 발생했었음.)
  2) DPI 인식 선언 — Tk 창 생성 전에 호출해야 적용된다.
  3) 단일 인스턴스 mutex — 이미 실행 중이면 트레이 안내 후 종료.
  4) GUI 기동 (예외는 MessageBox 로 가시화).
"""

import os
import sys
import ctypes
import traceback


# ──────────────────────────────────────────────
# 관리자 권한 확인 / 승격
# ──────────────────────────────────────────────

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def _script_abs_path() -> str:
    """현재 실행 중인 스크립트의 절대경로. PyInstaller exe 면 그 exe 경로."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def elevate() -> bool:
    """관리자 권한으로 재실행. ShellExecuteW 의 반환값이 32 이하이면 실패."""
    script = _script_abs_path()
    cwd = os.path.dirname(script) or os.getcwd()

    if getattr(sys, "frozen", False):
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
        target = script
    else:
        params_parts = [f'"{script}"'] + [f'"{a}"' for a in sys.argv[1:]]
        params = " ".join(params_parts)
        target = sys.executable

    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", target, params, cwd, 1
    )
    # ShellExecuteW: 성공 시 32 초과(HINSTANCE), 실패 시 32 이하 오류 코드
    return int(result) > 32


# ──────────────────────────────────────────────
# DPI 인식 선언 — Tk 에서는 "System Aware" 만 안전
# ──────────────────────────────────────────────
#
# Tk(Tcl 8.6)는 WM_DPICHANGED 를 처리하지 않는다. Per-Monitor V2 로 선언하면
# 다른 DPI 모니터로 창을 끌고 갔을 때 윈도우 사각형만 새 비율로 늘어나고
# 내부 위젯이 그 자리에 멈춰 레이아웃이 깨지며, 원래 모니터로 돌아와도 복구되지 않는다.
# System Aware 는 시작 모니터 DPI 로 고정되고 다른 DPI 에서는 OS 가 비트맵
# 스케일링을 한다(약간 흐릿하지만 레이아웃은 안 깨짐) — Tk 에선 이게 최선.

_DPI_AWARENESS_CONTEXT_SYSTEM_AWARE = -2
_PROCESS_SYSTEM_DPI_AWARE = 1


def _set_dpi_awareness() -> None:
    """최신 API 부터 차례로 시도해 DPI 인식을 켠다. (Win10 1703+ → 8.1+ → Vista+)"""
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(
            ctypes.c_void_p(_DPI_AWARENESS_CONTEXT_SYSTEM_AWARE)
        ):
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(_PROCESS_SYSTEM_DPI_AWARE)
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


# ──────────────────────────────────────────────
# 단일 실행 인스턴스 (named mutex)
# ──────────────────────────────────────────────

# Local\: 같은 로그온 세션 한정. Global\ 보다 권한 요구가 적다.
_MUTEX_NAME = "Local\\IPChanger_KDY_Single_Instance"
_ERROR_ALREADY_EXISTS = 183


def _acquire_single_instance_lock():
    """이미 실행 중이면 None. 정상이면 mutex 핸들(프로세스 수명 동안 보관)."""
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        if not handle:
            # 핸들 생성 자체가 실패한 비정상 케이스 — 락 보호 없이 진행시킨다.
            return object()
        err = ctypes.get_last_error()
        if err == _ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel32.CloseHandle(handle)
            return None
        return handle
    except (AttributeError, OSError):
        return object()


def _show_message(title: str, text: str, icon: int = 0x40) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, icon)
    except Exception:
        pass


# ──────────────────────────────────────────────
# 진입
# ──────────────────────────────────────────────

def _run() -> None:
    # app import 는 DPI 선언 이후로 미뤄야 Tk 가 올바른 배율로 초기화된다.
    from app import IPChangerApp
    IPChangerApp().run()


if __name__ == "__main__":
    if not is_admin():
        ok = elevate()
        if not ok:
            _show_message(
                "IP Changer",
                "관리자 권한 승격이 취소되었거나 실패했습니다.\n"
                "프로그램을 실행하려면 UAC 승인이 필요합니다.",
                0x30,  # MB_ICONWARNING
            )
        # 승격 성공 시에도 현재 프로세스는 종료 — elevated 새 프로세스가 이어 실행한다.
        sys.exit(0)

    _set_dpi_awareness()

    lock = _acquire_single_instance_lock()
    if lock is None:
        _show_message(
            "IP Changer",
            "IP Changer 가 이미 실행 중입니다.\n\n"
            "트레이(작업 표시줄 우측 알림 영역)의 IP 아이콘을 클릭하면\n"
            "기존 인스턴스를 다시 띄울 수 있습니다 — UAC 재요청 없이 즉시 사용 가능합니다.",
            0x40,  # MB_ICONINFORMATION
        )
        sys.exit(0)

    try:
        _run()
    except SystemExit:
        raise
    except BaseException:
        # 임포트 실패·테마 오류 등 사용자에게 보이지 않는 콘솔 오류를 가시화.
        _show_message(
            "IP Changer — 시작 실패",
            "프로그램 시작 중 오류가 발생했습니다:\n\n"
            + traceback.format_exc(),
            0x10,  # MB_ICONERROR
        )
        sys.exit(1)
