"""K-RESA macOS 데스크톱 런처

Streamlit 서버를 백그라운드로 실행하고 기본 브라우저에서 열기
"""

import subprocess
import sys
import os
import time
import signal
import webbrowser
import socket
from pathlib import Path


def find_free_port(start=8501):
    """사용 가능한 포트 찾기"""
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    return start


def get_app_dir():
    """앱 디렉토리 찾기 (.app 번들 내부 또는 개발 환경)"""
    # .app 번들 내부인 경우
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.parent / "Resources" / "k-resa"

    # 개발 환경
    return Path(__file__).parent.parent


def main():
    app_dir = get_app_dir()
    app_py = app_dir / "app.py"

    if not app_py.exists():
        print(f"오류: {app_py} 를 찾을 수 없습니다.")
        sys.exit(1)

    port = find_free_port()
    url = f"http://localhost:{port}"

    # Streamlit 서버 실행
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(app_py),
         "--server.port", str(port),
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=str(app_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 서버 시작 대기
    print(f"K-RESA 시작 중... (포트: {port})")
    for _ in range(30):
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) == 0:
                break
    else:
        print("서버 시작 실패")
        process.terminate()
        sys.exit(1)

    # 브라우저 열기
    print(f"브라우저에서 {url} 를 엽니다...")
    webbrowser.open(url)

    # 종료 시 서버도 종료
    def cleanup(signum=None, frame=None):
        print("\nK-RESA 종료 중...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("K-RESA 실행 중. 종료하려면 Ctrl+C를 누르세요.")

    try:
        process.wait()
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
