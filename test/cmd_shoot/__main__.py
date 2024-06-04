import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import function

def run_gui(master):
    root = ttk.Frame(master, padding=10)
    btn1 = ttk.Button(root, text='execute', command=lambda:function.on_btn1())
    btn1.pack()
    
    return root

if __name__ == "__main__":
    app = ttk.Window('IP Changer')
    app.geometry('500x600')
    start = run_gui(app)
    start.pack(fill=BOTH, expand=YES)
    app.mainloop()