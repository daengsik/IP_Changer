import subprocess
import tkinter
from tkinter import messagebox

import variables
import re

# Entry 입력값 체크
def chk_entry_data(data):
    return data.isdigit() and len(data) <= 3 or data ==""
def validate_cmd(window):
    return window.register(chk_entry_data)

# Entry 초기화
def init_entry():
    variables.ip_entries[0].delete(0, tkinter.END)
    variables.ip_entries[1].delete(0, tkinter.END)
    variables.ip_entries[2].delete(0, tkinter.END)
    variables.ip_entries[3].delete(0, tkinter.END)

    variables.subnet_entries[0].delete(0, tkinter.END)
    variables.subnet_entries[1].delete(0, tkinter.END)
    variables.subnet_entries[2].delete(0, tkinter.END)
    variables.subnet_entries[3].delete(0, tkinter.END)

    variables.gateway_entries[0].delete(0, tkinter.END)
    variables.gateway_entries[1].delete(0, tkinter.END)
    variables.gateway_entries[2].delete(0, tkinter.END)
    variables.gateway_entries[3].delete(0, tkinter.END)

# Radio variable 초기화
def init_radio():
    variables.radio_var = tkinter.StringVar(value="")
    return variables.radio_var

# 네트워크 어댑터 get
def get_network_adapter():
    result = subprocess.run(['netsh', 'interface', 'show', 'interface'], capture_output=True, text=True)
    output_lines = result.stdout.split("\n")

    for line in output_lines:
        adapter_info = re.split(r'\s{2,}', line)
        if len(adapter_info) > 3:
            adapter_name = adapter_info[3]
            variables.adapters.append(adapter_name)
    return variables.adapters

# Entry 활성화/비활성화
def nouse_Entry():
    print("nouse ENTRY")
    for entry in variables.ip_entries + variables.subnet_entries + \
                 variables.gateway_entries + variables.dns_entries:
        entry.config(state=tkinter.DISABLED)
    for label in variables.dot_label:
        label.config(bg="#f0f0f0")
def use_Entry():
    print("use ENTRY")
    for entry in variables.ip_entries + variables.subnet_entries + \
                 variables.gateway_entries + variables.dns_entries:
        entry.config(state=tkinter.NORMAL)
    for label in variables.dot_label:
        label.config(bg="white")

# Combobox 선택 이벤트 핸들러
def on_adapter_selected(event, selected_value):
    print("event")
    variables.adapter = selected_value
    result = subprocess.run(['netsh', 'interface', 'ipv4', 'show', 'address', variables.adapter],
                            capture_output=True, text=True)
    tmp = result.stdout.split()

    result2 = subprocess.run(['netsh', 'interface', 'show', 'interface', 'name=' + variables.adapter],
                             capture_output=True, text=True)
    tmp2 = re.split(r'\s{2,}', result2.stdout)
    tmp2 = tmp2[tmp2.index('관리 상태:') + 1]

    init_entry()

    if tmp2 == "사용 안 함":
        nouse_Entry()
        variables.radio_var.set("Off")
    if tmp2 == "사용":
        use_Entry()
        variables.radio_var.set("On")


    try:
        ipadd = tmp[tmp.index('IP')+2].split(".")
        set_ipEntry(ipadd[0], ipadd[1], ipadd[2], ipadd[3])
        print(tmp)
        if "Subnet" in tmp:
            subnet = tmp[tmp.index('Subnet') + 4].rstrip(')').split(".")
            set_subnetEntry(subnet[0], subnet[1], subnet[2], subnet[3])

            gateway = tmp[tmp.index('Default') + 2].split(".")
            set_gatewayEntry(gateway[0], gateway[1], gateway[2], gateway[3])

        else:
            subnet = tmp[tmp.index('서브넷') + 3].rstrip(')').split(".")
            set_subnetEntry(subnet[0], subnet[1], subnet[2], subnet[3])

            gateway = tmp[tmp.index('게이트웨이:') + 1].split(".")
            set_gatewayEntry(gateway[0], gateway[1], gateway[2], gateway[3])

        #print("def on adapter selected", variables.adapter)

    except ValueError as ve:
        print(f"{ve}")

    ### 여기서 구현해야된다 ###

# Radio 버튼 클릭 이벤트 핸들러
def on_radio_click():
    value = variables.radio_var.get()
    if value == "On":
        use_Entry()
    else:
        init_entry()
        nouse_Entry()

# DHCP 버튼 클릭 이벤트 핸들러
def on_DHCP_click():
    try:
        result = subprocess.run(['netsh', 'interface', 'set', 'interface', variables.adapter, 'admin=enable'],
                                capture_output=True, text=True)
        messagebox.showinfo("", result.stdout)
        result = subprocess.run(['netsh', 'interface', 'ipv4', 'set', 'address', variables.adapter, 'dhcp'],
                                capture_output=True, text=True)
        messagebox.showinfo("", result.stdout)
        result = subprocess.run(['netsh', 'interface', 'ipv4', 'set', 'dns', 'name=' + variables.adapter, 'source=dhcp'],
                                capture_output=True, text=True)
        messagebox.showinfo("", result.stdout)
    except TypeError as ty:
        messagebox.showinfo("Error", f"{ty}")

# 확인 버튼 클릭 이벤트 핸들러
def on_apply_click():
    ipadd = ".".join([entry.get() for entry in variables.ip_entries])
    subnet = ".".join([entry.get() for entry in variables.subnet_entries])
    gateway = ".".join([entry.get() for entry in variables.gateway_entries])
    dns = ".".join([entry.get() for entry in variables.dns_entries])
    stat = variables.radio_var.get()

    if stat == "On":
        result = subprocess.run(['netsh', 'interface', 'set', 'interface', variables.adapter,
                                 'admin=enable'], capture_output=True, text=True)
        print("On")
        print(result.stdout)

        # Gateway 입력값 조건검사
        if gateway != "..." and all(part.isdigit() for part in gateway.split("."))\
                and len(gateway.split(".")) == 4:
            print(gateway ,"정상")

            result = subprocess.run(['netsh', 'interface', 'ipv4', 'set', 'address', 'name=' +
                                     variables.adapter, 'static', ipadd, subnet, gateway],
                                    capture_output=True, text=True)
            messagebox.showinfo("", result.stdout)
        # Skip Gw
        else:
            print("gw 값 올바르지 않음")
            result = subprocess.run(['netsh', 'interface', 'ipv4', 'set', 'address', 'name=' +
                                     variables.adapter, 'static', ipadd, subnet],
                                    capture_output=True, text=True)
            messagebox.showinfo("", result.stdout)
        # Dns 입력값 조건검사
        if dns != "..." and all(part.isdigit() for part in dns.split(".")) \
                and len(dns.split(".")) == 4:
            print("dns 입력값 정상")
            result = subprocess.run(['netsh', 'interface', 'ipv4', 'set', 'dns', 'name=' +
                                    variables.adapter, 'source=static', 'address=' +
                                    dns, 'validate=no'], capture_output=True, text=True)
            messagebox.showinfo("", result.stdout)


    if stat == "Off":
        print(variables.adapter)
        result = subprocess.run(['netsh', 'interface', 'set', 'interface', variables.adapter,
                                 'admin=disable'], capture_output=True, text=True)
        messagebox.showerror("Error", result.stdout)


    print(ipadd)
    print(subnet)
    print(gateway)
    #print(dns)
    print(stat)

# 커스텀 버튼 클릭 이벤트 핸들러 (AhnLab)
def on_custom_click():
    init_entry()
    set_ipEntry("10", "0", "0", "1")
    set_subnetEntry("255", "255", "0", "0")
    set_gatewayEntry("10", "0", "0", "254")
    variables.ip_entries[2].focus_set()

def set_ipEntry(num1, num2, num3, num4):
    variables.ip_entries[0].insert(0, num1)
    variables.ip_entries[1].insert(0, num2)
    variables.ip_entries[2].insert(0, num3)
    variables.ip_entries[3].insert(0, num4)
def set_subnetEntry(num1, num2, num3, num4):
    variables.subnet_entries[0].insert(0, num1)
    variables.subnet_entries[1].insert(0, num2)
    variables.subnet_entries[2].insert(0, num3)
    variables.subnet_entries[3].insert(0, num4)
def set_gatewayEntry(num1, num2, num3, num4):
    variables.gateway_entries[0].insert(0, num1)
    variables.gateway_entries[1].insert(0, num2)
    variables.gateway_entries[2].insert(0, num3)
    variables.gateway_entries[3].insert(0, num4)
