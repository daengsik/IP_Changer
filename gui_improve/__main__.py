import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import function, variables

def run_gui(master):

    # toggle value #
    toggle = ttk.IntVar()
    toggle.set(0)
    root = ttk.Frame(master, padding=10)
    style = ttk.Style()
    theme_names = style.theme_names()

    theme_selection = ttk.Frame(root, padding=(10, 10, 10, 0))
    theme_selection.pack(fill=X, expand=YES)
    

    ### 타이틀 ###
    nameLabel = ttk.Label(
        master=theme_selection, text="IP Changer", font="-size 24 -weight bold"
    )
    nameLabel.pack(side=LEFT)

    ### 테마 콤보박스 ###
    theme_cbo = ttk.Combobox(
        master=theme_selection,
        text=style.theme.name,
        values=theme_names,
    )
    theme_cbo.pack(padx=10, side=RIGHT)
    theme_cbo.current(theme_names.index(style.theme.name))

    ### 테마변경 ###
    def change_theme(e):
        t = theme_cbo.get()
        style.theme_use(t)

    theme_cbo.bind("<<ComboboxSelected>>", change_theme)

    ### 구분선 ###
    ttk.Separator(root).pack(fill=X, pady=10, padx=10)

    ### 메인프레임 ###
    mFrame = ttk.Frame(root, padding=5)
    mFrame.pack(side=TOP, fill=BOTH, expand=YES)
    
    ### 트리프레임 ###
    tFrame = ttk.Frame(mFrame)
    tFrame.pack(pady=5, fill=X, side=TOP)

    ### 노트북 ###
    nb = ttk.Notebook(tFrame)
    nb.pack(side=LEFT, padx=(5, 0), fill=BOTH, expand=YES)
    tab1 = ttk.Frame(tFrame)
    nb.add(tab1, text="일반")
    tab2 = ttk.Frame(tFrame)
    nb.add(tab2, text="프리셋")

    ### TAB1 ###
    desc = ttk.Label(tab1, text="네트워크 어댑터를 선택하고 IP 구성정보를 입력하세요.\n"
                                "어댑터 사용유무는 선택 후 확인버튼을 눌러야 적용됩니다.\n"
                                "DHCP 버튼은 어댑터를 자동으로 '사용함' 상태로 변경합니다.")
    desc.pack(fill=X, padx=10, pady=10)

    ### 라벨프레임 ###
    input_group = ttk.LabelFrame(tab1, text="다음 IP 주소 사용", padding=5)
    input_group.pack(fill=X, padx=10, pady=10, side=TOP)

    ### 어댑터프레임 ###
    adpt_group = ttk.Frame(input_group)
    adpt_group.pack(side=TOP, fill=X)

    ### 어댑터 콤보박스 ###
    adpt_cbo = ttk.Combobox(
        adpt_group, 
        values=function.get_network_adapter(),
        width=30,
        state="readonly"
    )
    adpt_cbo.bind('<<ComboboxSelected>>', 
                  lambda event: function.on_adapter_selected(event, adpt_cbo.get(), toggle)
                  )
    adpt_cbo.pack(side=LEFT, padx=5, pady=5)

    ### 어댑터 토글버튼 ###
    useBtn = ttk.Checkbutton(
        adpt_group, 
        bootstyle=(SUCCESS, ROUND, TOGGLE),
        text="use toggle",
        onvalue=1,
        offvalue=0,
        variable=toggle,
        command=lambda:function.on_toggle(toggle)
    )
    useBtn.invoke()

    useBtn.pack(fill=X, side=LEFT, padx=20, pady=5)

    ### IP 프레임 ###
    ip_group = ttk.Frame(input_group)
    ip_group.pack(fill=X, side=TOP, padx=10, pady=5)

    ### SUBNET 프레임 ###
    subnet_group = ttk.Frame(input_group)
    subnet_group.pack(fill=X, side=TOP, padx=10, pady=5)

    ### GATEWAY 프레임 ###
    gateway_group = ttk.Frame(input_group)
    gateway_group.pack(fill=X, side=TOP, padx=10, pady=5)

    ### 서브버튼프레임 ###
    sBtnFrame = ttk.Frame(input_group)
    sBtnFrame.pack(fill=X, side=TOP, padx=10, pady=5)

    ipaddl = ttk.Label(ip_group, text="IP 주소")
    ipaddl.pack(side=LEFT)
    ipadd_Entry = ttk.Entry(ip_group, width=30, 
                            validate="key", 
                            validatecommand=(function.validate_cmd(app), "%P", "%S"),
                            )
    ipadd_Entry.pack(side=RIGHT, fill=X)
    ipadd_Entry.configure(justify="center")
    variables.data.append(ipadd_Entry)

    subnetl = ttk.Label(subnet_group, text="서브넷 마스크",)
    subnetl.pack(side=LEFT)
    subnet_Entry = ttk.Entry(subnet_group, width=30, 
                             validate="key", 
                             validatecommand=(function.validate_cmd(app), "%P", "%S"),
                             )
    subnet_Entry.pack(side=RIGHT)
    subnet_Entry.configure(justify="center")
    variables.data.append(subnet_Entry)

    gatewayl = ttk.Label(gateway_group, text="기본 게이트웨이")
    gatewayl.pack(side=LEFT)
    gateway_Entry = ttk.Entry(gateway_group, width=30, 
                              validate="key", 
                              validatecommand=(function.validate_cmd(app), "%P", "%S"),
                              )
    gateway_Entry.pack(side=RIGHT)
    gateway_Entry.configure(justify="center")
    variables.data.append(gateway_Entry)

    ### 커스텀 버튼 ###
    customBtn = ttk.Button(sBtnFrame, text="Custom", bootstyle=(SECONDARY))
    customBtn.pack(side=RIGHT,padx=(15,0))
    dhcpBtn = ttk.Button(sBtnFrame, text="DHCP", bootstyle=(SECONDARY), command=lambda:function.on_DHCP())
    dhcpBtn.pack(side=RIGHT)
    
    ### DNS 라벨프레임 ###
    dns_group = ttk.LabelFrame(tab1, text="DNS 설정", padding=5)
    dns_group.pack(fill=X, padx=10, pady=10, side=TOP)
    
    dnsl = ttk.Label(dns_group, text="기본 설정 DNS 서버")
    dnsl.pack(side=LEFT)
    dns_Entry = ttk.Entry(dns_group, width=30, 
                          validate="key", 
                          validatecommand=(function.validate_cmd(app), "%P", "%S"),
                          )
    dns_Entry.pack(side=RIGHT)
    dns_Entry.configure(justify="center")
    variables.data.append(dns_Entry)



    ### TAB2 ###
    preFrame = ttk.Frame(tab2)
    preFrame.pack(side=TOP, fill=X)
    
    editBtn = ttk.Button(preFrame, 
                         text="프리셋 편집 (업데이트)",
                         bootstyle=(LIGHT), 
                         padding=10, 
                         command=lambda:function.editPreset()
                         )
    editBtn.pack(fill=X, side=TOP,padx=10, pady=(10,0))

    pBtnFrame = ttk.Frame(preFrame)
    pBtnFrame.pack(side=TOP, fill=BOTH, expand=YES, pady=5)

    row1F = ttk.Frame(pBtnFrame)
    row1F.pack(side=TOP, fill=BOTH, expand=YES)
    
    preBtn1 = ttk.Button(row1F, text="Button 1\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(0))
    preBtn1.pack(side=LEFT, fill=BOTH, padx=(10,5), pady=5)

    variables.preBtn.append(preBtn1)
    preBtn2 = ttk.Button(row1F, text="Button 2\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(1))
    preBtn2.pack(side=LEFT, fill=BOTH, padx=(5,5), pady=5)
    variables.preBtn.append(preBtn2)
    preBtn3 = ttk.Button(row1F, text="Button 3\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(2))
    preBtn3.pack(side=LEFT, fill=BOTH, padx=(5,10), pady=5)
    variables.preBtn.append(preBtn3)

    row2F = ttk.Frame(pBtnFrame)
    row2F.pack(side=TOP, fill=BOTH, expand=YES)
    preBtn4 = ttk.Button(row2F, text="Button 4\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(3))
    preBtn4.pack(side=LEFT, fill=BOTH, padx=(10,5), pady=5)
    variables.preBtn.append(preBtn4)
    preBtn5 = ttk.Button(row2F, text="Button 5\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(4))
    preBtn5.pack(side=LEFT, fill=BOTH, padx=(5,5), pady=5)
    variables.preBtn.append(preBtn5)
    preBtn6 = ttk.Button(row2F, text="Button 6\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(5))
    preBtn6.pack(side=LEFT, fill=BOTH, padx=(5,10), pady=5)
    variables.preBtn.append(preBtn6)

    row3F = ttk.Frame(pBtnFrame)
    row3F.pack(side=TOP, fill=BOTH, expand=YES)
    preBtn7 = ttk.Button(row3F, text="Button 7\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(6))
    preBtn7.pack(side=LEFT, fill=BOTH, padx=(10,5), pady=5)
    variables.preBtn.append(preBtn7)
    preBtn8 = ttk.Button(row3F, text="Button 8\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(7))
    preBtn8.pack(side=LEFT, fill=BOTH, padx=(5,5), pady=5)
    variables.preBtn.append(preBtn8)
    preBtn9 = ttk.Button(row3F, text="Button 9\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(8))
    preBtn9.pack(side=LEFT, fill=BOTH, padx=(5,10), pady=5)
    variables.preBtn.append(preBtn9)

    row4F = ttk.Frame(pBtnFrame)
    row4F.pack(side=TOP, fill=BOTH, expand=YES)
    preBtn10 = ttk.Button(row4F, text="Button 10\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(9))
    preBtn10.pack(side=LEFT, fill=BOTH, padx=(10,5), pady=5)
    variables.preBtn.append(preBtn10)
    preBtn11 = ttk.Button(row4F, text="Button 11\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(10))
    preBtn11.pack(side=LEFT, fill=BOTH, padx=(5,5), pady=5)
    variables.preBtn.append(preBtn11)
    preBtn12 = ttk.Button(row4F, text="Button 12\n0.0.0.0", padding=(8,20,8,20), width=15,
                         command=lambda:function.on_preBtn(11))
    preBtn12.pack(side=LEFT, fill=BOTH, padx=(5,10), pady=5)
    variables.preBtn.append(preBtn12)


    ### 메인프레임 버튼 ###
    mBtnFrame = ttk.Frame(root, padding=5)
    mBtnFrame.pack(side=BOTTOM, fill=BOTH, expand=YES)
    applyBtn = ttk.Button(mBtnFrame, 
                          text="Apply", 
                          bootstyle=(PRIMARY),
                          command=lambda:function.on_apply(variables.data[0], variables.data[1], variables[2], variables[3])
                          )
    applyBtn.pack(side=RIGHT, padx=(15,0))
    cancleBtn = ttk.Button(
                            mBtnFrame, text="Cancle", 
                            bootstyle=(INFO, OUTLINE),
                            command=lambda:app.destroy()
                            )
    cancleBtn.pack(side=RIGHT)

    ### Info ###
    infol = ttk.Label(mBtnFrame, 
                      text="made by KDY, gui improve ver 1.0", 
                      font="-size 8",
                      padding=5
                      )
    infol.pack(side=LEFT)

    function.read_json()
    
    return root

class Progress:
    def __init__(self, parent):
        self.top = ttk.Toplevel(parent)
        self.top.title("Progress")
        self.top.geometry("300x100")

        label = ttk.Label(self.top, text="Progressing...")
        label.pack(pady=10)

        self.progress = ttk.Progressbar(self.top, mode='determinate', maximum=100)
        self.progress.pack(pady=10, padx=20, fill='x')

        self.progress_value = 0
        self.max_value = 100
        self.update_progress()

    def update_progress(self):
        if self.progress_value < self.max_value:
            self.progress_value += 1
            self.progress['value'] = self.progress_value
            self.top.after(10, self.update_progress)
        else:
            self.top.destroy()

if __name__ == "__main__":
    
    app = ttk.Window("Adapter IP Changer")
    app.geometry("500x644")
    app.resizable(FALSE,FALSE)
    start = run_gui(app)
    start.pack(fill=BOTH, expand=YES)
    

    app.mainloop()
    
