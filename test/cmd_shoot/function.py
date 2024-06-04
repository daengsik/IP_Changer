import subprocess
from ttkbootstrap.dialogs import Messagebox
import var

def on_btn1():
    result = subprocess.run(['netsh', 'interface', 'ipv4', 'show', 'address', '이더넷'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW, text=True)
    #print(result.stdout)

    #result = subprocess.run(['netsh', 'interface', 'ipv4', 'show', 'address','이더넷'], capture_output=True, text=True)
    #print(result.stdout)


    