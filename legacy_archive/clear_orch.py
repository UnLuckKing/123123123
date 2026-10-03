import urllib.request
try:
    urllib.request.urlopen("http://51.159.121.126:9000/api/slots/clear_all", timeout=3)
    print("Cleared")
except:
    pass
