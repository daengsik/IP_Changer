import subprocess
import re

adapter = "이더넷"
result_dict = {}
result2 = subprocess.run(['netsh', 'interface', 'show', 'interface', 'name=' + adapter], capture_output=True, text=True)

lines = result2.stdout.split('\n')
for line in lines:
    match = re.match(r'\s*(.*?):\s*(.*)', line)
    if match:
        key, value = match.groups()
        result_dict[key.strip()] = value.strip()

# 저장된 결과 출력
print(result_dict.get("관리 상태"))