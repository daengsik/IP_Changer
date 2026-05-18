# IP Changer v2.2

Windows 11 이더넷 어댑터 IP 변경 GUI. ttkbootstrap 기반 단일 윈도우 + 12 슬롯 프리셋 + **트레이 상주(위젯) 모드**.

## 설치

```powershell
python -m pip install -r requirements.txt
```

## 실행

```powershell
python -m IP_Changer_v2
```

또는 폴더 진입 후

```powershell
python __main__.py
```

UAC 권한이 자동으로 요청됩니다 (`Set-NetIPAddress` 가 관리자 권한 필요).

## 데이터 경로

| 파일 | 용도 |
|---|---|
| `%APPDATA%\IPChanger\preset.json` | 12 개 프리셋 |
| `%APPDATA%\IPChanger\preset.json.bak` | 마지막 정상 저장본 (자동 백업) |
| `%APPDATA%\IPChanger\config.json` | 테마 등 앱 설정 |
| `%APPDATA%\IPChanger\history.json` | 변경 이력 (최근 50건, 되돌리기용) |

> **첫 실행 시 자동 생성됩니다.** `%APPDATA%\IPChanger\` 폴더와 그 안의 파일들은
> `preset.init_presets()` 가 앱 시작 즉시 자동으로 만든다. EXE 옆에 어떤 데이터
> 파일도 두지 않으며, 별도 설치 절차나 디렉터리 권한 설정도 필요하지 않다.

## 빌드 (단일 EXE 배포)

PyInstaller 로 콘솔 창 없는 단일 EXE 를 만들 수 있습니다.

### 가장 빠른 방법 — 더블클릭 빌드

```powershell
# IP_Changer_v2 폴더 안에서
.\build.bat
```

진행 흐름: 의존성 자동 설치 → 이전 빌드 정리 → `IPChanger.spec` 으로 PyInstaller 실행.

산출물: **`dist\IPChanger.exe`**
- 단일 파일 (의존성 동봉)
- **콘솔 창 없음** (`console=False`)
- 더블클릭 시 **UAC 자동 요청** (manifest 에 `requireAdministrator` 포함, `uac_admin=True`)

### 수동 빌드 (스크립트를 거치지 않고 직접)

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller IPChanger.spec --clean --noconfirm
```

### `IPChanger.spec` 의 핵심 옵션

| 옵션 | 의미 |
|---|---|
| `console=False` | 검은 콘솔 창 미표시 (서브프로세스 PowerShell 도 `CREATE_NO_WINDOW` 로 이미 숨김) |
| `uac_admin=True` | manifest 에 관리자 권한 요구 박힘 → 더블클릭 즉시 UAC 가 뜸 |
| `collect_submodules('pystray')` | 트레이 백엔드(`pystray._win32`) 누락 방지 |
| `collect_submodules('PIL')` | Pillow 의 tkinter 헬퍼 누락 방지 |
| `collect_data_files('ttkbootstrap')` | 테마/폰트 데이터 동봉 — 빼면 일부 테마가 깨짐 |
| `icon=None` | `icon.ico` 가 있으면 경로 지정 (선택) |

## 배포 (사용자 입장)

1. `dist\IPChanger.exe` 를 USB/공유폴더/메신저 등 어디든 복사 — **설치 마법사 없음**
2. 사용자가 더블클릭 → **UAC 승인 1회**
3. `%APPDATA%\IPChanger\` 가 자동 생성되며 12 개 기본 프리셋이 들어감
4. 이후 사용자가 프리셋을 편집하면 같은 폴더의 `preset.json` 에 저장됨

### 완전 제거(언인스톨)
1. `IPChanger.exe` 삭제
2. (선택) `%APPDATA%\IPChanger\` 폴더 삭제 — 프리셋·이력까지 깨끗이 지움
   * 탐색기 주소창에 `%APPDATA%\IPChanger` 붙여넣으면 바로 진입

## v2.2 주요 변경점

### 위젯(트레이) 모드 — 신규
- **X 버튼 → "트레이 / 완전 종료" 선택 다이얼로그** (다시 묻지 않기 체크 가능)
- 트레이로 내려도 **프로세스가 계속 살아 있어**:
  - 다시 띄울 때 **UAC 권한 재요청 없음**
  - PowerShell 세션 콜드 스타트 없음 (조회/적용이 항상 ~0.1s)
- **트레이 아이콘 우클릭 메뉴**:
  - **열기** (좌클릭 더블 = 동일)
  - **프리셋 1~12 즉시 적용** (창을 열지 않고 IP 변경)
  - **X 버튼 동작** ─ 라디오 (매번 묻기 / 트레이로 내리기 / 완전 종료)
  - **종료**
- 두 번째 인스턴스 실행 시도는 자동 차단 + 안내 메시지

### "다시 묻지 않기" 를 되돌리는 방법
체크해서 갇히더라도 두 곳에서 언제든 되돌릴 수 있습니다.
1. **메인 창 헤더의 ⚙ 메뉴 → X 버튼 동작 → "매번 묻기"** 선택
2. **트레이 아이콘 우클릭 → X 버튼 동작 → "매번 묻기"** 선택

최후 수단으로 `%APPDATA%\IPChanger\config.json` 의 `close_action` 키를 지워도 됩니다.

### UI 단순화
- 어댑터 카드(설명/MAC/링크속도/상태 뱃지/모드 뱃지) 제거 — IP 정보는 입력 필드가 단일 표출 지점
- 토글은 어댑터 콤보 바로 아래 한 줄로 이동
- 프리셋 탭 상단: **"적용 대상: 이더넷 3"** 한 줄만 표기
- 프리셋 버튼: 이름 / IP 두 줄만
- 프리셋 편집창에서 가져오기/내보내기 버튼 제거
- **하단 상태 메시지 줄 제거** — 작업 진행은 입력 필드 자동 갱신으로, 에러는 다이얼로그로 대체

### 윈도우 크기/위치
- **자유롭게 가로/세로 리사이즈 가능** (`resizable=(True, True)`)
- 종료/트레이로 내리는 직전 현재 크기·위치를 `config.json` 에 저장 → 다음 실행 시 복원
- 화면이 줄거나 모니터가 분리된 경우엔 자연 크기 + 중앙 폴백

### 버그 픽스 / 사용성
- **다이얼로그가 빈 채로 열리던 문제 수정** — `validatecommand` 의 한 글자 단위
  필터가 `entry.insert(0, "192.168.1.100")` 같은 multi-char 삽입을 거부하던 버그.
  `%P` (변경 후 전체값) 기반 검증으로 전환.
- **빈 프리셋 저장 허용** — 미등록 슬롯을 강제로 채울 필요 없음. 채워진 값만 형식 검증.
- 빈 프리셋 클릭 시 안내 메시지 + 강조 오작동 차단

### 성능 (v2.1 부터 유지)
- 변경 작업이 **netsh 다중 호출 → PowerShell 단일 호출** 통합 (~0.6 s → ~0.15 s)
- PowerShell 세션 워밍업 — 앱 시작과 동시에 백그라운드로 가동
- 트레이 모드에서 세션이 살아 있으므로 콜드 스타트가 영구적으로 사라짐

## 구조

```
IP_Changer_v2/
├── __main__.py        # 진입점: UAC, DPI, 단일 인스턴스
├── app.py             # 메인 윈도우 + 트레이 통합 + 종료 동작 분기
├── tray.py            # 트레이 아이콘/메뉴 컨트롤러 (위젯 모드)
├── network.py         # PowerShell 세션 + 정적/DHCP/ping/검증
├── preset.py          # 프리셋/설정/히스토리 영속화 (%APPDATA%)
├── requirements.txt
├── IPChanger.spec     # PyInstaller 빌드 설정 (onefile + windowed + uac)
├── build.bat          # 더블클릭 빌드 스크립트
└── ui/
    ├── __init__.py
    ├── styles.py       # 폰트·뱃지·버튼 스타일 토큰
    ├── tab_manual.py   # 수동 설정 탭 (어댑터 콤보 + IP 입력 + 되돌리기)
    ├── tab_preset.py   # 프리셋 탭 (12 버튼 그리드)
    ├── dialog_edit.py  # 프리셋 편집 다이얼로그
    └── dialog_close.py # 종료 확인 다이얼로그 (위젯창/완전 종료)
```

## 설정 키 (`%APPDATA%\IPChanger\config.json`)

| 키 | 값 | 의미 |
|---|---|---|
| `theme` | ttkbootstrap 테마명 (예: `litera`, `darkly`) | UI 테마 |
| `close_action` | `"minimize"` \| `"exit"` \| 키 없음 | X 버튼 동작. 키가 없으면 매번 확인 다이얼로그 |
| `window_geometry` | `"480x600+100+50"` 형식 | 마지막 창 크기/위치. 다음 실행 시 복원 |
