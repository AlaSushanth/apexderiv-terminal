import uvicorn
import webbrowser
import threading
import time
import socket
import sys

def find_available_port(preferred_port=8000, max_attempts=10):
    for port in range(preferred_port, preferred_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred_port

def open_browser(port):
    time.sleep(1.2)
    url = f"http://127.0.0.1:{port}"
    print(f"\n[+] Launching ApexDeriv in your default browser at {url} ...")
    webbrowser.open(url)

if __name__ == "__main__":
    port = find_available_port(8000)
    
    print("==================================================================")
    print("  APEXDERIV // INTERNATIONAL DERIVATIVES TRADING TERMINAL")
    print("  Modeled for Futures First (Hertshten Group) Trainee Role")
    print(f"  Target Server: http://127.0.0.1:{port}")
    print("==================================================================")
    
    # Launch browser automatically
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    
    # Run FastAPI + Uvicorn server
    uvicorn.run("backend.server:app", host="127.0.0.1", port=port, log_level="info")
