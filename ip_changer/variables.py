import locale

current_locale, encoding = locale.getdefaultlocale()
adapters = []
adapter = None

radio_var = None

ip_entries = []
subnet_entries = []
gateway_entries = []
dns_entries = []

dot_label=[]