# IPChanger.spec — PyInstaller 빌드 설정
#
# 사용:
#   pyinstaller IPChanger.spec --clean --noconfirm
#
# 산출물:
#   dist\IPChanger.exe   (단일 파일, 콘솔 없음, 더블클릭 시 UAC 자동 요청)
#
# 설계 메모:
#   - onefile + windowed(console=False) + uac_admin
#   - pystray 백엔드(_win32 등)와 Pillow 의 tkinter 헬퍼는 PyInstaller 가
#     기본 분석으로 놓치는 경우가 있어 collect_submodules 로 명시 포함.
#   - ttkbootstrap 의 폰트/테마 데이터는 patcage 내부에 있으므로 collect_data_files
#     로 묶지 않으면 일부 테마(`litera`, `darkly` 등)가 런타임에 깨진다.
#   - 데이터 파일(preset.json/config.json/history.json)은 런타임에 %APPDATA% 에
#     자동 생성되므로 datas 에 동봉할 필요가 없다.

from PyInstaller.utils.hooks import collect_submodules, collect_data_files


block_cipher = None


a = Analysis(
    ['__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=collect_data_files('ttkbootstrap'),
    hiddenimports=(
        collect_submodules('pystray')
        + collect_submodules('PIL')
        + ['tkinter', 'tkinter.ttk', 'tkinter.font']
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='IPChanger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # 콘솔 창 숨김 (--windowed)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,          # manifest 에 requireAdministrator 포함
    uac_uiaccess=False,
    icon=None,               # 'icon.ico' 가 있으면 경로 지정
)
