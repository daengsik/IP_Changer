from tkinter import *
import tkinter as tk
from tkinter import ttk, messagebox

#from ttkbootstrap import Style

import function
import variables

# Window
window = tk.Tk()
window.title('IP Changer')
window.geometry('384x405')
#window.resizable(False, False)

def run_gui():
    # run_as_admin():
    # Style
    style = ttk.Style()
    style.configure("TButton", padding=1, relief="flat", width=8, borderwidth=0)
    style.configure("TLabelframe")
    style.map("TButton", foreground=[("pressed", "#333"), ("active", "#555")])

    #style2=Style(theme='darkly')

    # NOTEBOOK#
    ui_notebook = tk.ttk.Notebook(window, width=400, height=330)
    tab1 = tk.Frame(window)
    ui_notebook.add(tab1, text="일반   ")
    tab2 = tk.Frame(window)
    ui_notebook.add(tab2, text=" 프리셋 ")

    # TAB1 FRAME #
    ui_buttonFrame = tk.Frame(window)

    ui_ipLabelFrame = ttk.LabelFrame(tab1, text="  다음 IP 주소 사용  ")
    ui_dnsLabelFrame = ttk.LabelFrame(tab1, text="  다음 DNS 서버 주소 사용  ")

    ui_txtFrame = tk.Frame(ui_ipLabelFrame, width=130, height=160)
    ui_txtFrame.pack_propagate(False)
    ui_inputFrame = tk.Frame(ui_ipLabelFrame, width=196, height=160)
    ui_inputFrame.pack_propagate(False)

    ui_ipEntryFrame = tk.Frame(ui_inputFrame, bg="white", borderwidth=1, relief="groove")
    ui_subnetEntryFrame = tk.Frame(ui_inputFrame, bg="white", borderwidth=1, relief="groove")
    ui_gatewayEntryFrame = tk.Frame(ui_inputFrame, bg="white", borderwidth=1, relief="groove")
    ui_customButtonFrame = tk.Frame(ui_inputFrame)

    ui_dnstxtFrame = tk.Frame(ui_dnsLabelFrame, width=130, height=50)
    ui_dnstxtFrame.pack_propagate(False)
    ui_dnsInputFrame = tk.Frame(ui_dnsLabelFrame, width=196, height=50)
    ui_dnsInputFrame.pack_propagate(False)
    ui_dnsEntryFrame = tk.Frame(ui_dnsInputFrame, bg="white", borderwidth=1, relief="groove")

    ui_adapterFrame = tk.Frame(ui_inputFrame)


    # TAB2 FRAME #
    ui_presetFrame = tk.Frame(tab2, bg="red")
    ui_presetFrame.pack(fill="both")

    ui_presetEditButton = ttk.Button(ui_presetFrame, text="프리셋 편집", 
                                      command=function.on_presetEdit_click)

    ui_presetButtonFrame = tk.Frame(tab2, bg="blue")
    ui_presetBtn1 =  tk.Button(ui_presetButtonFrame, text="button1")
    ui_presetBtn2 =  tk.Button(ui_presetButtonFrame, text="button2")
    ui_presetBtn3 =  tk.Button(ui_presetButtonFrame, text="button3")
    ui_presetBtn4 =  tk.Button(ui_presetButtonFrame, text="button4")
    ui_presetBtn5 =  tk.Button(ui_presetButtonFrame, text="button5")
    ui_presetBtn6 =  tk.Button(ui_presetButtonFrame, text="button6")
    ui_presetBtn7 =  tk.Button(ui_presetButtonFrame, text="button7")
    ui_presetBtn8 =  tk.Button(ui_presetButtonFrame, text="button8")
    ui_presetBtn9 =  tk.Button(ui_presetButtonFrame, text="button9")
    
    # COMBOBOX #
    ui_adaptCombo = ttk.Combobox(ui_adapterFrame, values=function.get_network_adapter(), state="readonly", width=13)
    ui_adaptCombo.bind('<<ComboboxSelected>>', lambda event: function.on_adapter_selected(event, ui_adaptCombo.get()))

    # RADIO #
    function.init_radio()
    ui_onRadio = ttk.Radiobutton(ui_adapterFrame, text="켬", variable=variables.radio_var,
                                 value="On", command=function.on_radio_click)
    ui_offRadio = ttk.Radiobutton(ui_adapterFrame, text="끔", variable=variables.radio_var,
                                  value="Off", command=function.on_radio_click)

    # PANEL #


    # LABEL #
    ui_descLabel1 = ttk.Label(tab1, text="네트워크 어댑터를 선택하고 IP 구성정보를 입력하세요.\n"
                                          "어댑터 사용유무는 선택후 확인버튼을 눌러야 반영됩니다. \n"
                                          "DHCP 버튼은 어댑터를 자동으로 '사용함' 으로 변경합니다.")
    ui_dnsLabel = tk.Label(ui_dnstxtFrame, text=" 기본 설정 DNS 서버", anchor="w")
    ui_adaptLabel = tk.Label(ui_txtFrame, text=" 어댑터", anchor="w")
    ui_ipLabel = tk.Label(ui_txtFrame, text=" IP 주소", anchor="w")
    ui_subnetLabel = tk.Label(ui_txtFrame, text=" 서브넷 마스크", anchor="w")
    ui_gatewayLabel = tk.Label(ui_txtFrame, text=" 기본 게이트웨이", anchor="w")


    # ENTRY #
    for i in range(4):
        ui_ipEntry = tk.Entry(ui_ipEntryFrame, width=5, relief="flat", bg="white", justify="center",
                     validate="key", validatecommand=(function.validate_cmd(window), "%P"))
        ui_ipEntry.pack(side="left")
        if i < 3:
            label = tk.Label(ui_ipEntryFrame, text=".", bg="white")
            label.pack(side="left")
        variables.ip_entries.append(ui_ipEntry)
        variables.dot_label.append(label)
    for i in range(4):
        ui_subnetEntry = tk.Entry(ui_subnetEntryFrame, width=5, relief="flat", bg="white", justify="center",
                              validate="key", validatecommand=(function.validate_cmd(window), "%P"))
        ui_subnetEntry.pack(side="left")
        if i < 3:
            label = tk.Label(ui_subnetEntryFrame, text=".", bg="white")
            label.pack(side="left")
        variables.subnet_entries.append(ui_subnetEntry)
        variables.dot_label.append(label)
    for i in range(4):
        ui_gatewayEntry = tk.Entry(ui_gatewayEntryFrame, width=5, relief="flat", bg="white", justify="center",
                              validate="key", validatecommand=(function.validate_cmd(window), "%P"))
        ui_gatewayEntry.pack(side="left")
        if i < 3:
            label = tk.Label(ui_gatewayEntryFrame, text=".", bg="white")
            label.pack(side="left")
        variables.gateway_entries.append(ui_gatewayEntry)
        variables.dot_label.append(label)
    for i in range(4):
        ui_dnsEntry = tk.Entry(ui_dnsEntryFrame, width=5, relief="flat", bg="white", justify="center",
                      validate="key", validatecommand=(function.validate_cmd(window), "%P"))
        ui_dnsEntry.pack(side="left")
        if i < 3:
            label = tk.Label(ui_dnsEntryFrame, text=".", bg="white")
            label.pack(side="left")
        variables.dns_entries.append(ui_dnsEntry)
        variables.dot_label.append(label)

    # BUTTON #
    ui_customButton = ttk.Button(ui_customButtonFrame, text="Custom", style="TButton",
                                 command=function.on_custom_click)
    ui_DHCPButton = ttk.Button(ui_customButtonFrame, text="DHCP", style="TButton",
                               command=function.on_DHCP_click)

    ui_applyButton = ttk.Button(ui_buttonFrame, text="확인", style="TButton",
                                command=function.on_apply_click)
    ui_cancelButton = ttk.Button(ui_buttonFrame, text="취소", style="TButton",
                                 command=lambda: window.destroy())


    # PACKING #
    ui_notebook.pack(padx=10, pady=(10, 5))
    ui_descLabel1.pack(fill="x", padx=10, pady=10)
    ui_ipLabelFrame.pack(fill="x", padx=10, pady=5)
    ui_txtFrame.pack(side="left", padx=(5, 0))
    ui_inputFrame.pack(side="left", padx=(0, 5))
    ui_adaptLabel.pack(fill="x", pady=5, padx=5)
    ui_ipLabel.pack(fill="x", pady=5, padx=5)
    ui_subnetLabel.pack(fill="x", pady=5, padx=5)
    ui_gatewayLabel.pack(fill="x", pady=5, padx=5)

    ui_adapterFrame.pack(fill="x")
    ui_adaptCombo.pack(side="left", pady=5, padx=5)
    ui_offRadio.pack(side="right")
    ui_onRadio.pack(side="right")

    ui_ipEntryFrame.pack(fill="x", pady=4, padx=5)
    ui_subnetEntryFrame.pack(fill="x", pady=4, padx=5)
    ui_gatewayEntryFrame.pack(fill="x", pady=4, padx=5)
    ui_customButtonFrame.pack(fill="x", pady=4, padx=5)
    ui_customButton.pack(side="right")
    ui_DHCPButton.pack(side="right")

    ui_dnsLabelFrame.pack(fill="x", padx=10, pady=10)
    ui_dnstxtFrame.pack(side="left", padx=(5, 0))
    ui_dnsLabel.pack(fill="x", pady=5, padx=5)
    ui_dnsInputFrame.pack(side="left", padx=(0, 5))
    ui_dnsEntryFrame.pack(fill="x", pady=4, padx=5)
    ui_buttonFrame.pack(fill="x", padx=10)

    ui_applyButton.pack(side="right", padx=3, pady=(0, 4))
    ui_cancelButton.pack(side="right", padx=3, pady=(0, 4))




    # PACKING TAB2 #
    ui_presetEditButton.pack(fill="both")



    window.mainloop()

if __name__ == "__main__":
    run_gui()