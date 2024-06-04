import subprocess
import tkinter
from tkinter import messagebox

import variables
import re

import sys
import os

import json

#import win32com.shell.shell as shell

# run_as_admin
# def run_as_admin():
#     if sys.argv[-1] != 'asadmin':
#         script = os.path.abspath(sys.argv[0])
#         params = ' '.join([script] + sys.argv[1:] + ['asadmin'])
#         shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)
#         sys.exit(0)

# Subprocess result normalization
def normalize_result(result):
    result_dict = {}
    lines = result.stdout.split('\n')
    for line in lines:
        match = re.match(r'\s*(.*?):\s*(.*)', line)
        if match:
            key, value = match.groups()
            # 여백을 제외하고 저장
            result_dict[key.strip()] = value.strip()
    return result_dict

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

    variables.dns_entries[0].delete(0, tkinter.END)
    variables.dns_entries[1].delete(0, tkinter.END)
    variables.dns_entries[2].delete(0, tkinter.END)
    variables.dns_entries[3].delete(0, tkinter.END)

# Radio variable 초기화
def init_radio():
    variables.radio_var = tkinter.StringVar(value="")
    return variables.radio_var

# get network adapter list
def get_network_adapter():
    result = subprocess.run(['netsh', 'interface', 'show', 'interface'], capture_output=True, text=True)
    output_lines = result.stdout.split("\n")

    for line in output_lines:
        adapter_info = re.split(r'\s{2,}', line)
        if len(adapter_info) > 3:
            adapter_name = adapter_info[3]
            variables.adapters.append(adapter_name)
    return variables.adapters

# Entry activate/deactivate
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

# Combobox Event Handler
def on_adapter_selected(event, selected_value):
    # Entry 초기화
    init_entry()
    try:
        variables.adapter = selected_value
        result = subprocess.run(['netsh', 'interface', 'ipv4', 'show', 'address', variables.adapter], capture_output=True, text=True)
        print(normalize_result(result))

        # 어댑터 사용, 사용안함 여부 판단하는 구문
        result2 = subprocess.run(['netsh', 'interface', 'show', 'interface', 'name=' + variables.adapter], capture_output=True, text=True)
        print(normalize_result(result2))
        # dns 주소 가져옴
        result3 = subprocess.run(['netsh', 'interface', 'ip', 'show', 'dns', variables.adapter], capture_output=True, text=True)
        print(normalize_result(result3))

        # 한국어 일 경우 어댑터 사용유무에 따른 Radio 버튼 선택
        if list(normalize_result(result2).values())[1] == "사용 안 함" or list(normalize_result(result2).values())[1] == "Disabled" :
            nouse_Entry()
            variables.radio_var.set("Off")
        if list(normalize_result(result2).values())[1] == "사용" or list(normalize_result(result2).values())[1] == "Enabled":
            use_Entry()
            variables.radio_var.set("On")

    except IndexError:
        messagebox.showerror("Error", "invalid interface name.")

    try:
        ipadd = list(normalize_result(result).values())[1].split(".")
        set_ipEntry(ipadd[0], ipadd[1], ipadd[2], ipadd[3])

        subnet = list(normalize_result(result).values())[2]
        # 영문결과 정규식 수정필요
        subnet = re.search(r'\((마스크\s+([\d.]+))\)', subnet).group(2).split(".")
        set_subnetEntry(subnet[0], subnet[1], subnet[2], subnet[3])

        gateway = list(normalize_result(result).values())[3].split(".")
        set_gatewayEntry(gateway[0], gateway[1], gateway[2], gateway[3])

        dns = list(normalize_result(result3).values())[0].split(".")
        set_dnsEntry(dns[0], dns[1], dns[2], dns[3])

    except IndexError:
        messagebox.showerror("Error", "Failed to retrieve the IP address.")

    # except AttributeError:
    #     subnet = re.search(r'\((mask\s+([\d.]+))\)', subnet).group(2).split(".")
    #     set_subnetEntry(subnet[0], subnet[1], subnet[2], subnet[3])
    #     gateway = list(normalize_result(result).values())[3].split(".")
    #     set_gatewayEntry(gateway[0], gateway[1], gateway[2], gateway[3])

    #     dns = list(normalize_result(result3).values())[0].split(".")
    #     set_dnsEntry(dns[0], dns[1], dns[2], dns[3])

# Radio 버튼 클릭 이벤트 핸들러
def on_radio_click():
    value = variables.radio_var.get()
    if value == "On":
        use_Entry()

    if value == "Off":
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

    # Messagebox 필수만 남기고 정리해야됨
    except TypeError as ty:
        messagebox.showinfo("Error", f"{ty}")

# 확인 버튼 클릭 이벤트 핸들러
def on_apply_click():
    ipadd = ".".join([entry.get() for entry in variables.ip_entries])
    subnet = ".".join([entry.get() for entry in variables.subnet_entries])
    gateway = ".".join([entry.get() for entry in variables.gateway_entries])
    dns = ".".join([entry.get() for entry in variables.dns_entries])

    # 어댑터 사용유무 확인함
    stat = variables.radio_var.get()

    # 사용일때 동작함, Try 로 예외처리 필요함
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

    # Off 일때 사용안함으로 처리함
    if stat == "Off":
        print(variables.adapter)
        result = subprocess.run(['netsh', 'interface', 'set', 'interface', variables.adapter,
                                 'admin=disable'], capture_output=True, text=True)
        # Messagebox 정리필요함
        messagebox.showerror("Error", result.stdout)

# 커스텀 버튼 클릭 이벤트 핸들러 (AhnLab)
def on_custom_click():
    init_entry()
    set_ipEntry("10", "0", "0", "1")
    set_subnetEntry("255", "255", "0", "0")
    set_gatewayEntry("10", "0", "0", "254")
    # Focus
    variables.ip_entries[2].focus_set()


def on_presetEdit_click():
    file_path = r"C:\test.txt"
    os.startfile(file_path)

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
def set_dnsEntry(num1, num2, num3, num4):
    variables.dns_entries[0].insert(0, num1)
    variables.dns_entries[1].insert(0, num2)
    variables.dns_entries[2].insert(0, num3)
    variables.dns_entries[3].insert(0, num4)