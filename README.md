# IP_Changer with Python (ver Korean)
파이썬을 사용한 GUI 기반의 네트워크 어댑터 구성 설정 변경 프로그램

###### ❗Windows 기반에서만 동작합니다.
<br>
<br>

## ⚠️ 사전설정

1. 프로그램은 항상 **관리자 권한** 으로 실행되어야 합니다.
   - **[우클릭]** > **[속성]** > **[호환성]** > **[관리자 권한으로 이 프로그램 실행]** > 을 적용하여, 항상 관리자 권한을 취득하게 설정하세요.
2. 향상된 GUI 프로그램은 data 디렉토리 안에 위치한 **preset.json 파일이 올바른 위치에 있어야 실행이 가능** 합니다.
   - **[Window + R]** > **%appdata%** > 해당 **[Roaming] 폴더 안에 preset.json 파일** 을 넣어주세요.
<br>
<br>

## ❗사용법

1. **OS 언어설정이 영어일 경우 정상동작하지 않습니다.** 향후 개선예정입니다.
2. 모든 설정은, **어댑터를 우선 선택하여야 합니다. "언플러그" 상태인 어댑터는 구성 변경이 불가합니다.**
3. [프리셋] TAB 역시 어댑터를 우선 선택해야 합니다.
   1. 잘못된 어댑터에서 프리셋 버튼으로 설정이 변경된 경우, 구성 설정의 충돌이 발생할 수 있습니다.
   2. [프리셋 편집] 버튼으로 preset.json 파일을 편집할 때는 프로그램 기능이 동작하지 않습니다. 반드시 preset.json 파일을 저장하고, 종료해주세요.
   3. [프리셋 편집]을 사용하여 버튼설정을 수정한 경우, preset.json 파일을 저장하고 다시 한번 [프리셋 편집] 버튼을 누르는 것으로 버튼 설정의 업데이트가 가능합니다. 또는 프로그램을 다시 시작해주세요.
   4. [프리셋 버튼] 또는 [DHCP] 버튼으로 어댑터 구성이 변경되었을 때, 프로그램이 해당 변경 정보를 반영하기까지 1~5초의 시간이 소요됩니다. IP 변경이 보이기까지 다른 동작을 중복해서 실행하지 말아주세요.
4. 어댑터 정보를 읽어오지 못하는 경우, 어댑터 구성 정보가 일반적이지 않은 상태일 수 있습니다.
5. 모든 입력값은 정규식으로 데이터를 검사합니다. 즉, IP 범위 외의 값과 dot(.)을 제외한 어떤 문자도 입력이 불가능합니다.
<br>
<br>

## ❌ 미구현, 구현예정

- OS 언어설정이 영어일 경우 데이터 정규화 불가능
- 지정한 테마의 저장기능 미구현
- 프로세스 동작 예외처리 일부 미구현
- 해상도, 배율의 차이로 발생하는 GUI 왜곡의 개선
- Custom 버튼 미구현
