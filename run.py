import streamlit.web.cli as stcli
import os, sys
import socket
import webbrowser
from threading import Timer

def resolve_path(path):
    if getattr(sys, "frozen", False):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

def open_browser():
    webbrowser.open_new("http://localhost:8501")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unknown"

if __name__ == "__main__":
    # ... (前面的打印代码保持不变) ...
    ip = get_local_ip()
    print("-" * 50)
    print(f"✅ 程序启动成功！")
    print(f"🌍 本机访问地址: http://localhost:8501")
    print(f"📡 局域网访问地址: http://{ip}:8501")
    print("-" * 50)

    Timer(1, open_browser).start()

    # === 关键修改在这里 ===
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"),
        "--server.address=0.0.0.0",
        "--global.developmentMode=false",
        "--server.headless=true",       # 1. 禁用交互式提示（防止黑框卡住询问）
        "--browser.gatherUsageStats=false", # 2. 彻底禁用数据收集（这是不再询问邮箱的关键）
        "--theme.base=light"            # (可选) 强制浅色主题，看起来更专业
    ]
    
    sys.exit(stcli.main())