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
    # 尝试打开浏览器访问 localhost
    webbrowser.open_new("http://localhost:8501")

def get_local_ip():
    try:
        # 获取本机局域网IP，方便打印出来提示用户
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unknown"

if __name__ == "__main__":
    # 1. 打印局域网访问地址
    ip = get_local_ip()
    print("-" * 50)
    print(f"✅ 程序启动成功！")
    print(f"🌍 本机访问地址: http://localhost:8501")
    print(f"📡 局域网访问地址: http://{ip}:8501")
    print(f"   (请将局域网地址发给同事，他们即可访问)")
    print("-" * 50)

    # 2. 延迟1秒自动打开浏览器
    Timer(1, open_browser).start()

    # 3. 启动 Streamlit
    # --server.address=0.0.0.0 允许外部访问
    # --server.headless=true 不自动弹窗（我们上面自己弹了）
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"),
        "--server.address=0.0.0.0",
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())