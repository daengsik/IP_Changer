
from ttkbootstrap.dialogs import Messagebox
import ttkbootstrap as ttk
import subprocess, threading
import re, os, time, json

import variables

### GET JSON FILE PATH ###
def get_appdata_path():
    path_appdata = os.getenv('APPDATA')
    return os.path.join(path_appdata, 'preset.json')

### READ_JSON FILE ###
def read_json():
    with open(get_appdata_path(), 'r', encoding='utf-8') as file:
        data = json.load(file)
        #print(data)

        init_preBtn(data)
        return data

### 어댑터 리스트 ###
def get_network_adapter():
    result = subprocess.run(['netsh', 'interface', 'show', 'interface'], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    output_lines = result.stdout.split("\n")

    for line in output_lines:
        adapter_info = re.split(r'\s{2,}', line)
        if len(adapter_info) > 3:
            adapter_name = adapter_info[3]
            variables.adapters.append(adapter_name)
    return variables.adapters

### 데이터정규화 ###
def normalize_result(result):
    result_dict = {}
    lines = result.stdout.split('\n')
    for line in lines:
        match = re.match(r'\s*(.*?):\s*(.*)', line)
        if match:
            key, value = match.groups()
            # 여백제거
            result_dict[key.strip()] = value.strip()
    return result_dict

### ADAPTER SELECT EVENT ###
def on_adapter_selected(event, selected_value, toggle):
    init_entry()
    
    try:
        variables.adapter = selected_value
        result = subprocess.run(['netsh', 'interface', 'ipv4', 'show', 'address', '"'+variables.adapter+'"'], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        #print(normalize_result(result))

        # 어댑터 사용, 사용안함 여부 판단하는 구문
        result2 = subprocess.run(['netsh', 'interface', 'show', 'interface', 'name=' + variables.adapter], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        #print(normalize_result(result2))
        # dns 주소 가져옴
        result3 = subprocess.run(['netsh', 'interface', 'ip', 'show', 'dns', variables.adapter], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        #print(normalize_result(result3))

        # 한국어 일 경우 어댑터 사용유무에 따른 Radio 버튼 선택
        if list(normalize_result(result2).values())[1] == "사용 안 함" or list(normalize_result(result2).values())[1] == "Disabled" :
            nouse_Entry()
            toggle.set(0)

        if list(normalize_result(result2).values())[1] == "사용" or list(normalize_result(result2).values())[1] == "Enabled":
            use_Entry()
            toggle.set(1)

    except IndexError:
        Messagebox.showerror("invalid interface name.", "Index Error")


    try:
        ### 한국어 설정의 경우 ###
        ipadd = list(normalize_result(result).values())[1]
        subnet = list(normalize_result(result).values())[2]
        subnet = re.search(r'\((마스크\s+([\d.]+))\)', subnet).group(2)
        gateway = list(normalize_result(result).values())[3]
        dns = list(normalize_result(result3).values())[0]
        set_Entry(ipadd, subnet, gateway, dns)
        #
        #
        # 영어 설정일 경우 구현 필요
        #
        #

    except IndexError:
        Messagebox.show_error("Failed to retrieve the IP address.", "Index Error")
    
    except AttributeError:
        Messagebox.show_error("Failed to retrieve the IP address.", "Attribute Error")

### ENTRY VALUE CHECK ###
def chk_entry_data(value_if_allowed, text):
    ip_pattern = re.compile(
        r"^$|"
        r"^(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\."
        r"(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\."
        r"(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\."
        r"(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])$"
    )
    if text.isdigit() or text=="." or text=="" or ip_pattern.match(value_if_allowed):
        parts = value_if_allowed.split(".")
        if len(parts) > 4:
            return False
        for part in parts:
            if part and (not part.isdigit() or int(part) > 255):
                return False
        return True
    else:
        return False
### ENTRY VALUE CHECK ### 
def validate_cmd(app):
    return app.register(chk_entry_data)

### CLICK DHCP BUTTON ###
def on_DHCP():
    try:
        # 어댑터 사용
        result = subprocess.run(['netsh', 'interface', 'set', 'interface', variables.adapter, 'admin=enable'],
                                creationflags=subprocess.CREATE_NO_WINDOW, shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        #Messagebox.showinfo("", result.stdout)

        # DHCP 사용
        result = subprocess.run(['netsh', 'interface', 'ipv4', 'set', 'address', variables.adapter, 'dhcp'],
                                creationflags=subprocess.CREATE_NO_WINDOW, shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        if result.returncode == 0:
            Messagebox.show_info("DHCP 설정 적용", "DHCP")
        else:
            Messagebox.show_info(result.stdout,"DHCP")

        # DHCP DNS 사용
        result = subprocess.run(['netsh', 'interface', 'ipv4', 'set', 'dns', 'name=' + variables.adapter, 'source=dhcp'],
                                creationflags=subprocess.CREATE_NO_WINDOW, shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        #Messagebox.showinfo("", result.stdout)
        
        threading.Thread(target=lambda: time.sleep(1) or update_Entry()).start()

    except TypeError as ty:
        Messagebox.show_info(f"{ty}", "Error")
   
### PRESET EDIT BTN ###
def editPreset():
    read_json()
    path = get_appdata_path()
    subprocess.run(f'notepad.exe "{path}"')

### INIT_PRESET BUTTON TEXT ###
def init_preBtn(data):
    for i in range(12):
        txt = data[i]['desc'] + "\n" + data[i]['ip_addr']
        variables.preBtn[i].configure(text=txt)

### PRESS PRESET BTN ###
def on_preBtn(num):
    data = read_json()
    on_apply(data[num]['ip_addr'], data[num]['subnet'], data[num]['gateway'], data[num]['dns'])
    
    threading.Thread(target=lambda: time.sleep(4) or update_Entry()).start()

### ADAPTER TOGGLE ON/OFF ###
def on_toggle(value):
    # not selected adapter #
    if variables.adapter == None:
        return
    # adapter OFF #
    if value.get() == 0:
        subprocess.run(['netsh', 'interface', 'set', 'interface', variables.adapter, 'admin=disable'], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        init_entry()
        nouse_Entry()

    # adapter ON #
    if value.get() == 1:
        subprocess.run(['netsh', 'interface', 'set', 'interface', variables.adapter, 'admin=enable'], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        use_Entry()
        update_Entry()

### INIT ENTRY VARIABLES ###
def init_entry():
    variables.data[0].delete(0, ttk.END)
    variables.data[1].delete(0, ttk.END)
    variables.data[2].delete(0, ttk.END)
    variables.data[3].delete(0, ttk.END)

### ENTRY FIELD SET ###
def set_Entry(ipadd, subnet, gateway, dns):
    init_entry()
    variables.data[0].insert(0, ipadd)
    variables.data[1].insert(0, subnet)
    variables.data[2].insert(0, gateway)
    variables.data[3].insert(0, dns)

### UPDATE ENTRY TEXT ###
def update_Entry():

    result = subprocess.run(['netsh', 'interface', 'ipv4', 'show', 'address', '"'+variables.adapter+'"'], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    #result2 = subprocess.run(['netsh', 'interface', 'show', 'interface', 'name=' + variables.adapter], stdout=subprocess.PIPE, text=True)
    result3 = subprocess.run(['netsh', 'interface', 'ip', 'show', 'dns', variables.adapter], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

    ipadd = list(normalize_result(result).values())[1]
    subnet = list(normalize_result(result).values())[2]
    subnet = re.search(r'\((마스크\s+([\d.]+))\)', subnet).group(2)
    gateway = list(normalize_result(result).values())[3]
    dns = list(normalize_result(result3).values())[0]
    set_Entry(ipadd, subnet, gateway, dns)

### ENTRY ACTIVATE / DEACTIVATE ###
def nouse_Entry():
    init_entry()
    variables.data[0].config(state=ttk.DISABLED)
    variables.data[1].config(state=ttk.DISABLED)
    variables.data[2].config(state=ttk.DISABLED)
    variables.data[3].config(state=ttk.DISABLED)
def use_Entry():
    init_entry()
    variables.data[0].config(state=ttk.ACTIVE)
    variables.data[1].config(state=ttk.ACTIVE)
    variables.data[2].config(state=ttk.ACTIVE)
    variables.data[3].config(state=ttk.ACTIVE)

### SETTING APPLY ###
def on_apply(ip, subnet, gateway, dns):
    result = subprocess.run(['netsh', 'interface', 'ipv4', 'set', 'address', 'name=', '"'+variables.adapter+'"', 'static', ip, subnet, gateway], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

    # DNS EMPTY #
    if dns=="":
        return
    # USED DNS SETTING #
    else:
        result = subprocess.run(['netsh', 'interface', 'ipv4', 'set', 'dns', 'name=', '"'+variables.adapter+'"', 'source=static', 'address=' + dns, 'validate=no'], stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)