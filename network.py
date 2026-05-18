"""네트워크 조회/변경 — 영구 PowerShell 세션 기반.

설계
  - 조회/변경을 모두 1개의 영구 PowerShell 프로세스로 처리. netsh 호출을 없애
    변경 1회당 0.3~0.6s → 0.08~0.15s 수준으로 단축된다.
  - 변경 함수는 (성공여부, 사용자메시지) 튜플 반환. 호출 측이 직전 IPConfig 를
    별도로 받아 히스토리에 기록한다 → 되돌리기 구현 단순화.
"""

import base64
import ipaddress
import json
import subprocess
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional


# ──────────────────────────────────────────────
# PowerShell 영구 세션
# ──────────────────────────────────────────────

class PowerShellSession:
    """단일 PowerShell 프로세스를 유지하며 stdin/stdout 파이프로 명령을 재사용.

    콜드 스타트 1~2s 는 최초 1회로 한정되고, 이후 명령은 ~30~80ms 이내에 반환된다.
    """

    _SENTINEL = "<<<PS_SESSION_DONE_A7F2>>>"
    _ERR_SENTINEL = "<<<PS_SESSION_ERR_A7F2>>>"

    def __init__(self):
        self._proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self._lock = threading.Lock()

        # stderr 누적으로 stdout 파이프가 블록되는 사고 방지용 드레인 스레드.
        threading.Thread(target=self._drain_stderr, daemon=True).start()

        # 인코딩 핸드셰이크 — 한글 어댑터 이름을 안전하게 다루기 위한 필수 준비.
        # 첫 줄(InputEncoding=UTF-8) 자체는 ASCII 만 쓰므로 기본 CP949 로도 정상 디코딩되며,
        # 이후 들어오는 한글 포함 명령부터 UTF-8 로 해석된다. OutputEncoding 두 곳을 모두
        # UTF-8 로 맞춰야 stdout/파이프에서 한글이 깨지지 않는다.
        self._send_raw(
            "[Console]::InputEncoding  = [System.Text.Encoding]::UTF8\n"
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
            "$OutputEncoding           = [System.Text.Encoding]::UTF8\n"
            "$ErrorActionPreference    = 'Continue'\n"
            f"Write-Output '{self._SENTINEL}'\n"
        )
        self._collect_until_sentinel()

    def _drain_stderr(self):
        try:
            for _ in self._proc.stderr:
                pass
        except Exception:
            pass

    def _send_raw(self, text: str):
        self._proc.stdin.write(text.encode("utf-8"))
        self._proc.stdin.flush()

    def _collect_until_sentinel(self) -> str:
        lines: list[str] = []
        while True:
            raw = self._proc.stdout.readline()
            if not raw:
                raise RuntimeError("PowerShell 세션이 예기치 않게 종료되었습니다.")
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if line == self._SENTINEL:
                break
            lines.append(line)
        return "\n".join(lines)

    def run(self, command: str) -> str:
        with self._lock:
            if self._proc.poll() is not None:
                raise RuntimeError("PowerShell 세션이 종료되었습니다.")
            self._send_raw(f"{command}\nWrite-Output '{self._SENTINEL}'\n")
            return self._collect_until_sentinel()

    def close(self):
        try:
            self._proc.stdin.close()
            self._proc.wait(timeout=3)
        except Exception:
            self._proc.kill()


_session: Optional["PowerShellSession"] = None
_session_lock = threading.Lock()


def _get_session() -> PowerShellSession:
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                _session = PowerShellSession()
    return _session


def _run_ps(command: str) -> str:
    """세션이 비정상 종료되었을 때 1회만 자동 재시작 후 재시도."""
    global _session
    try:
        return _get_session().run(command)
    except RuntimeError:
        with _session_lock:
            _session = None
        return _get_session().run(command)


def warmup_session_async() -> None:
    """앱 기동과 동시에 PowerShell 콜드 스타트를 백그라운드로 숨긴다."""
    threading.Thread(target=_get_session, daemon=True).start()


# ──────────────────────────────────────────────
# 보조 유틸
# ──────────────────────────────────────────────

def _ps_str(s: str) -> str:
    """PowerShell 작은따옴표 문자열용 이스케이프 (ASCII 입력 전용)."""
    return s.replace("'", "''")


def _ps_b64_str(s: str) -> str:
    """한글/유니코드를 PowerShell 명령에 안전하게 박아 넣는다.

    명령 텍스트는 ASCII Base64 만 들어가므로 stdin 인코딩 영향이 없다.
    PowerShell 안에서 UTF-8 바이트로 역디코딩되어 원래 문자열이 복원된다.
    반환값은 단일 식이므로 `-Name {expr}` 또는 `$n = {expr}` 로 곧장 사용.
    """
    b64 = base64.b64encode(s.encode("utf-8")).decode("ascii")
    return f"([System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64}')))"


def prefix_to_subnet(prefix_length: int) -> str:
    if not (0 <= prefix_length <= 32):
        return "255.255.255.0"
    mask = (0xFFFFFFFF << (32 - prefix_length)) & 0xFFFFFFFF
    return ".".join(str((mask >> (8 * i)) & 0xFF) for i in reversed(range(4)))


def subnet_to_prefix(subnet: str) -> int:
    """도트 표기 마스크(예: 255.255.255.0)를 CIDR 비트수로 변환.

    비정상(비연속 1비트) 마스크도 비트수만 세어 반환한다 — UI 가 잘못된 입력을
    이미 막고 있어 여기서 추가 검증할 필요가 없다.
    """
    try:
        parts = [int(x) for x in subnet.strip().split(".")]
        if len(parts) != 4 or any(not (0 <= p <= 255) for p in parts):
            return 24
        mask_int = (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]
        return bin(mask_int).count("1")
    except (ValueError, TypeError):
        return 24


def is_valid_ip(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value.strip())
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False


def is_valid_subnet(value: str) -> bool:
    """올바른 서브넷 마스크인지(연속된 1비트) 검사."""
    if not is_valid_ip(value):
        return False
    parts = [int(x) for x in value.split(".")]
    mask_int = (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]
    inverted = (~mask_int) & 0xFFFFFFFF
    return (inverted & (inverted + 1)) == 0


def is_same_subnet(ip: str, gw: str, subnet: str) -> bool:
    """ip 와 gw 가 동일 서브넷에 속하는지 검사. 입력이 잘못되면 False."""
    try:
        prefix = subnet_to_prefix(subnet)
        net = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)
        return ipaddress.IPv4Address(gw) in net
    except (ValueError, ipaddress.AddressValueError):
        return False


# ──────────────────────────────────────────────
# 데이터 모델
# ──────────────────────────────────────────────

@dataclass
class AdapterInfo:
    name: str
    description: str = ""
    status: str = "Unknown"          # "Up" | "Disabled" | "Disconnected" | "Unknown"
    mac_address: str = ""
    link_speed: str = ""             # "1 Gbps" 등 사람이 읽기 좋은 문자열 그대로

    @property
    def display_label(self) -> str:
        if self.description and self.description != self.name:
            return f"{self.name}  —  {self.description}"
        return self.name


@dataclass
class IPConfig:
    ip: str = ""
    subnet: str = "255.255.255.0"
    gateway: str = ""
    dns: list[str] = field(default_factory=list)
    is_dhcp: bool = False
    is_apipa: bool = False     # 169.254.x.x 자가 할당 주소 — 외부 통신 불가 표시

    @property
    def primary_dns(self) -> str:
        return self.dns[0] if self.dns else ""

    @property
    def secondary_dns(self) -> str:
        return self.dns[1] if len(self.dns) > 1 else ""


@dataclass
class AdapterDetail:
    info: AdapterInfo
    config: Optional[IPConfig] = None     # Disabled 어댑터는 None


# ──────────────────────────────────────────────
# 조회
# ──────────────────────────────────────────────

def _format_link_speed(raw: object) -> str:
    # PowerShell LinkSpeed 는 보통 '1 Gbps' / '100 Mbps' 같은 문자열로 이미 가공돼 있다.
    if raw is None or raw == "":
        return ""
    return str(raw)


def _parse_detail(raw: dict) -> AdapterDetail:
    info = AdapterInfo(
        name=str(raw.get("Name") or ""),
        description=str(raw.get("Description") or ""),
        status=str(raw.get("Status") or "Unknown").strip(),
        mac_address=str(raw.get("MacAddress") or "").upper(),
        link_speed=_format_link_speed(raw.get("LinkSpeed")),
    )
    if info.status == "Disabled":
        return AdapterDetail(info=info, config=None)

    dns_raw = raw.get("DNS") or []
    if isinstance(dns_raw, str):
        dns_raw = [dns_raw] if dns_raw else []
    try:
        prefix = int(raw.get("PrefixLength") or 24)
    except (TypeError, ValueError):
        prefix = 24

    config = IPConfig(
        ip=str(raw.get("IP") or ""),
        subnet=prefix_to_subnet(prefix),
        gateway=str(raw.get("Gateway") or ""),
        dns=[str(d) for d in dns_raw if d],
        is_dhcp=bool(raw.get("DHCP", False)),
        is_apipa=bool(raw.get("IsApipa", False)),
    )
    return AdapterDetail(info=info, config=config)


def get_adapters() -> list[AdapterInfo]:
    """시스템의 모든 네트워크 어댑터 목록(이름·설명·상태·MAC·속도)."""
    output = _run_ps(
        "Get-NetAdapter | Select-Object Name,InterfaceDescription,Status,"
        "MacAddress,LinkSpeed | ConvertTo-Json -Compress"
    )
    if not output:
        return []
    try:
        data = json.loads(output)
        items = data if isinstance(data, list) else [data]
        return [
            AdapterInfo(
                name=str(it.get("Name") or ""),
                description=str(it.get("InterfaceDescription") or ""),
                status=str(it.get("Status") or "Unknown").strip(),
                mac_address=str(it.get("MacAddress") or "").upper(),
                link_speed=_format_link_speed(it.get("LinkSpeed")),
            )
            for it in items
            if it.get("Name")
        ]
    except (json.JSONDecodeError, KeyError):
        return []


def get_adapter_detail(adapter_name: str) -> AdapterDetail:
    """어댑터 정보(설명/MAC/속도/상태) + IP 구성을 PowerShell 1회 호출로 동시 반환."""
    ps_cmd = f"""
$n     = {_ps_b64_str(adapter_name)}
$adpt  = Get-NetAdapter -Name $n -ErrorAction SilentlyContinue
$addrs = @(Get-NetIPAddress -InterfaceAlias $n -AddressFamily IPv4 -ErrorAction SilentlyContinue)
# 비-APIPA(정상 라우팅 가능) IP 를 우선, 없으면 APIPA 라도 — 사용자가 현재 상태를 볼 수 있게
$addr  = $addrs | Where-Object {{ $_.IPAddress -notlike '169.254.*' }} | Select-Object -First 1
if (-not $addr) {{ $addr = $addrs | Select-Object -First 1 }}
$isApipa = if ($addr) {{ $addr.IPAddress -like '169.254.*' }} else {{ $false }}
$gw    = (Get-NetIPConfiguration -InterfaceAlias $n -ErrorAction SilentlyContinue).IPv4DefaultGateway
$dns   = (Get-DnsClientServerAddress -InterfaceAlias $n -AddressFamily IPv4 -ErrorAction SilentlyContinue).ServerAddresses
[PSCustomObject]@{{
    Name         = if ($adpt) {{ $adpt.Name }}                          else {{ $n }}
    Description  = if ($adpt) {{ $adpt.InterfaceDescription }}          else {{ '' }}
    Status       = if ($adpt) {{ $adpt.Status }}                        else {{ 'Unknown' }}
    MacAddress   = if ($adpt) {{ $adpt.MacAddress }}                    else {{ '' }}
    LinkSpeed    = if ($adpt) {{ $adpt.LinkSpeed }}                     else {{ '' }}
    IP           = if ($addr) {{ $addr.IPAddress }}                     else {{ '' }}
    PrefixLength = if ($addr) {{ [int]$addr.PrefixLength }}             else {{ 24 }}
    Gateway      = if ($gw)   {{ $gw.NextHop }}                         else {{ '' }}
    DNS          = if ($dns)  {{ @($dns) }}                             else {{ @() }}
    DHCP         = if ($addr) {{ $addr.PrefixOrigin -eq 'Dhcp' }}       else {{ $false }}
    IsApipa      = $isApipa
}} | ConvertTo-Json -Compress
"""
    output = _run_ps(ps_cmd)
    if not output:
        return AdapterDetail(info=AdapterInfo(name=adapter_name))
    try:
        return _parse_detail(json.loads(output))
    except (json.JSONDecodeError, KeyError, ValueError):
        return AdapterDetail(info=AdapterInfo(name=adapter_name))


# ──────────────────────────────────────────────
# 변경 — 모두 PowerShell 영구 세션 안에서 처리
# ──────────────────────────────────────────────

def _ps_bool(b: bool) -> str:
    return "$true" if b else "$false"


def enable_adapter(adapter_name: str) -> tuple[bool, str]:
    cmd = f"""
$n = {_ps_b64_str(adapter_name)}
try {{
    Enable-NetAdapter -Name $n -Confirm:$false -ErrorAction Stop
    Write-Output 'OK'
}} catch {{
    Write-Output ('ERR: ' + $_.Exception.Message)
}}
"""
    out = _run_ps(cmd).strip()
    return (out == "OK"), ("" if out == "OK" else out.removeprefix("ERR: "))


def disable_adapter(adapter_name: str) -> tuple[bool, str]:
    cmd = f"""
$n = {_ps_b64_str(adapter_name)}
try {{
    Disable-NetAdapter -Name $n -Confirm:$false -ErrorAction Stop
    Write-Output 'OK'
}} catch {{
    Write-Output ('ERR: ' + $_.Exception.Message)
}}
"""
    out = _run_ps(cmd).strip()
    return (out == "OK"), ("" if out == "OK" else out.removeprefix("ERR: "))


def apply_static_ipv4(
    adapter_name: str,
    ip: str,
    subnet: str,
    gateway: str,
    dns_list: list[str],
) -> tuple[bool, str]:
    """정적 IPv4 + DNS 를 1회 PowerShell 호출로 적용.

    기존 IP/라우트를 정리하고 새 값을 설정한다. dns_list 가 비어 있으면 DNS 는 건드리지 않는다.
    """
    prefix = subnet_to_prefix(subnet)
    # IP/게이트웨이/DNS 는 ASCII 만 들어오므로 단순 작은따옴표 이스케이프로 충분.
    dns_ps = ",".join(f"'{_ps_str(d)}'" for d in dns_list if d.strip())
    set_dns_block = (
        f"Set-DnsClientServerAddress -InterfaceAlias $n -ServerAddresses @({dns_ps}) -ErrorAction Stop"
        if dns_ps else
        "# DNS 미지정 — 기존 값 유지"
    )
    gw_block = (
        f"-DefaultGateway '{_ps_str(gateway)}' "
        if gateway.strip() else ""
    )
    cmd = f"""
$n = {_ps_b64_str(adapter_name)}
try {{
    if ((Get-NetAdapter -Name $n -ErrorAction Stop).Status -eq 'Disabled') {{
        Enable-NetAdapter -Name $n -Confirm:$false -ErrorAction Stop
        Start-Sleep -Milliseconds 250
    }}
    Set-NetIPInterface -InterfaceAlias $n -Dhcp Disabled -ErrorAction SilentlyContinue
    Remove-NetIPAddress -InterfaceAlias $n -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue
    Remove-NetRoute -InterfaceAlias $n -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue
    New-NetIPAddress -InterfaceAlias $n -IPAddress '{_ps_str(ip)}' -PrefixLength {prefix} {gw_block}-ErrorAction Stop | Out-Null
    {set_dns_block}
    Write-Output 'OK'
}} catch {{
    Write-Output ('ERR: ' + $_.Exception.Message)
}}
"""
    out = _run_ps(cmd).strip().splitlines()
    last = out[-1] if out else ""
    if last == "OK":
        return True, ""
    return False, last.removeprefix("ERR: ") or "알 수 없는 오류"


def apply_dhcp(adapter_name: str) -> tuple[bool, str]:
    """IP/DNS 를 DHCP 로 전환하고 DHCP 재협상을 강제로 트리거.

    순서가 매우 중요하다 — MS 문서 명시:
      Set-NetIPInterface -Dhcp Enabled 는 어댑터에 정적 IP 가 박혀 있으면
      DHCP 활성 플래그만 켤 뿐 기존 정적 IP 를 자동 제거하지 않는다.
      → 정적 IP/라우트를 **먼저** 제거하고, 그 다음에 DHCP 를 활성화해야 한다.

    재협상은 `ipconfig /renew` 대신 `Restart-NetAdapter` 를 쓴다 — PowerShell
    → native exe 의 인자 처리에서 공백/한글 어댑터명(`이더넷 3`)이 분해되어
    /renew 가 실패하는 사례를 회피하기 위함. 어댑터 재시작은 잠깐의 네트워크
    단절을 만들지만 DHCP discover 를 가장 확실하게 트리거한다.
    """
    cmd = f"""
$n = {_ps_b64_str(adapter_name)}
try {{
    Enable-NetAdapter -Name $n -Confirm:$false -ErrorAction SilentlyContinue

    # 1) 정적 IP/라우트 제거 — Set-NetIPInterface 보다 반드시 먼저
    Remove-NetIPAddress -InterfaceAlias $n -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue
    Remove-NetRoute -InterfaceAlias $n -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue

    # 2) DHCP 모드 활성 + DNS 자동
    Set-NetIPInterface -InterfaceAlias $n -Dhcp Enabled -ErrorAction Stop
    Set-DnsClientServerAddress -InterfaceAlias $n -ResetServerAddresses -ErrorAction SilentlyContinue

    # 3) DHCP discover 트리거 — 어댑터 재시작이 가장 확실
    Restart-NetAdapter -Name $n -Confirm:$false -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 800
    Write-Output 'OK'
}} catch {{
    Write-Output ('ERR: ' + $_.Exception.Message)
}}
"""
    out = _run_ps(cmd).strip().splitlines()
    last = out[-1] if out else ""
    if last == "OK":
        return True, ""
    return False, last.removeprefix("ERR: ") or "알 수 없는 오류"


# ──────────────────────────────────────────────
# 안전성 — IP 충돌 사전 감지
# ──────────────────────────────────────────────

def is_ip_in_use(ip: str, timeout_ms: int = 500) -> bool:
    """ping 1회로 해당 IP 가 이미 응답하는지 빠르게 확인.

    ICMP 가 차단된 환경에서는 미사용(False)으로 보일 수 있는 휴리스틱이다.
    """
    cmd = (
        f"$r = Test-Connection -ComputerName '{_ps_str(ip)}' -Count 1 "
        f"-TimeoutSeconds {max(1, timeout_ms // 1000) or 1} "
        f"-Quiet -ErrorAction SilentlyContinue; if ($r) {{ 'YES' }} else {{ 'NO' }}"
    )
    out = _run_ps(cmd).strip().splitlines()
    return any(line.strip() == "YES" for line in out)


# ──────────────────────────────────────────────
# 직렬화 헬퍼 — 히스토리/되돌리기용
# ──────────────────────────────────────────────

def ipconfig_to_dict(cfg: Optional[IPConfig]) -> Optional[dict]:
    return asdict(cfg) if cfg else None


def ipconfig_from_dict(data: Optional[dict]) -> Optional[IPConfig]:
    if not data:
        return None
    return IPConfig(
        ip=data.get("ip", ""),
        subnet=data.get("subnet", "255.255.255.0"),
        gateway=data.get("gateway", ""),
        dns=list(data.get("dns") or []),
        is_dhcp=bool(data.get("is_dhcp", False)),
    )
