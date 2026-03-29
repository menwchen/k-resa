#!/bin/bash
# K-RESA macOS .app 번들 빌드 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_NAME="K-RESA"
APP_DIR="$PROJECT_DIR/dist/${APP_NAME}.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

echo "🔨 K-RESA macOS 앱 빌드 시작..."

# 기존 빌드 정리
rm -rf "$APP_DIR"

# .app 번들 구조 생성
mkdir -p "$MACOS"
mkdir -p "$RESOURCES/k-resa"

# ─── Info.plist ───
cat > "$CONTENTS/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>K-RESA</string>
    <key>CFBundleDisplayName</key>
    <string>K-RESA</string>
    <key>CFBundleIdentifier</key>
    <string>com.menwchen.k-resa</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>k-resa</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>© 2026 송종운 (menwchen@mac.com)</string>
</dict>
</plist>
PLIST

# ─── 실행 스크립트 ───
cat > "$MACOS/k-resa" << 'LAUNCHER'
#!/bin/bash
DIR="$(cd "$(dirname "$0")/../Resources/k-resa" && pwd)"

# arm64로 강제 실행 (유니버셜 바이너리 대응)
if [ "$(uname -m)" = "arm64" ] || [ "$(sysctl -n sysctl.proc_translated 2>/dev/null)" = "1" ]; then
    if [ -z "$KRESA_ARCH_SET" ]; then
        export KRESA_ARCH_SET=1
        exec arch -arm64 "$0" "$@"
    fi
fi

# Python 찾기 (python3 우선)
PYTHON=""
for p in python3 python; do
    if command -v "$p" &>/dev/null; then
        PYTHON="$p"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    osascript -e 'display dialog "Python이 설치되어 있지 않습니다.\n\nhttps://www.python.org 에서 설치해주세요." buttons {"확인"} default button 1 with title "K-RESA" with icon stop'
    exit 1
fi

# 의존성 확인 및 설치
if ! "$PYTHON" -c "import streamlit" 2>/dev/null; then
    osascript -e 'display notification "필수 패키지를 설치 중입니다..." with title "K-RESA"'
    "$PYTHON" -m pip install -q streamlit pandas numpy plotly matplotlib scipy statsmodels requests pyyaml fredapi 2>/dev/null
fi

# Streamlit 서버 시작
PORT=8501
while lsof -i :"$PORT" &>/dev/null; do
    PORT=$((PORT + 1))
done

export STREAMLIT_SERVER_PORT="$PORT"
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

"$PYTHON" -m streamlit run "$DIR/app.py" \
    --server.port "$PORT" \
    --server.headless true \
    --browser.gatherUsageStats false &

SERVER_PID=$!

# 서버 시작 대기
for i in $(seq 1 30); do
    if curl -s "http://localhost:$PORT" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

# 브라우저 열기 (Chrome 우선, 없으면 기본 브라우저)
if [ -d "/Applications/Google Chrome.app" ]; then
    open -a "Google Chrome" "http://localhost:$PORT"
else
    open "http://localhost:$PORT"
fi

# 종료 대기
wait $SERVER_PID
LAUNCHER

chmod +x "$MACOS/k-resa"

# ─── 프로젝트 파일 복사 ───
echo "📦 프로젝트 파일 복사 중..."

# 필요한 디렉토리/파일만 복사
for item in app.py requirements.txt config data models dashboard utils; do
    if [ -d "$PROJECT_DIR/$item" ]; then
        cp -R "$PROJECT_DIR/$item" "$RESOURCES/k-resa/"
    elif [ -f "$PROJECT_DIR/$item" ]; then
        cp "$PROJECT_DIR/$item" "$RESOURCES/k-resa/"
    fi
done

# .streamlit 설정 복사
if [ -d "$PROJECT_DIR/.streamlit" ]; then
    cp -R "$PROJECT_DIR/.streamlit" "$RESOURCES/k-resa/"
fi

# settings.yaml 복사 (로컬 키 포함)
if [ -f "$PROJECT_DIR/config/settings.yaml" ]; then
    cp "$PROJECT_DIR/config/settings.yaml" "$RESOURCES/k-resa/config/"
fi

# 캐시/불필요 파일 제거
find "$RESOURCES/k-resa" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find "$RESOURCES/k-resa" -name "*.pyc" -delete 2>/dev/null
rm -rf "$RESOURCES/k-resa/data/cache" 2>/dev/null
mkdir -p "$RESOURCES/k-resa/data/cache"

# ─── 앱 아이콘 생성 ───
echo "🎨 앱 아이콘 생성 중..."

ICON_DIR="$RESOURCES/AppIcon.iconset"
mkdir -p "$ICON_DIR"

# Python 찾기
PYTHON="$(command -v python3 || command -v python)"

# Python으로 아이콘 이미지 생성
"$PYTHON" - "$ICON_DIR" << 'ICONPY'
import sys, os
try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit(0)

icon_dir = sys.argv[1]

# 1024px 마스터 이미지 생성
size = 1024
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 둥근 사각형 배경
m = 80
draw.rounded_rectangle([m, m, size-m, size-m], radius=180, fill=(14, 17, 23, 255))

# 주황색 원
cm = 200
draw.ellipse([cm, cm, size-cm, size-cm], fill=(255, 107, 53, 255))

# 내부 작은 원 (도넛 모양)
im = 340
draw.ellipse([im, im, size-im, size-im], fill=(14, 17, 23, 255))

# 차트 바 3개
bar_w = 60
for i, (h, color) in enumerate([(280, (76,175,80)), (380, (255,107,53)), (200, (33,150,243))]):
    x = 300 + i * (bar_w + 40)
    draw.rectangle([x, size//2 + 150 - h, x + bar_w, size//2 + 150], fill=color)

# 각 사이즈로 리사이즈
for s in [16, 32, 64, 128, 256, 512, 1024]:
    resized = img.resize((s, s), Image.LANCZOS)
    resized.save(os.path.join(icon_dir, f"icon_{s}x{s}.png"))
    if s <= 512:
        s2 = min(s * 2, 1024)
        resized2 = img.resize((s2, s2), Image.LANCZOS)
        resized2.save(os.path.join(icon_dir, f"icon_{s}x{s}@2x.png"))

print("아이콘 생성 완료")
ICONPY

# iconutil로 .icns 변환
if [ -f "$ICON_DIR/icon_512x512.png" ]; then
    iconutil -c icns "$ICON_DIR" -o "$RESOURCES/AppIcon.icns" 2>/dev/null || true
fi
rm -rf "$ICON_DIR"

# ─── 빌드 완료 ───
APP_SIZE=$(du -sh "$APP_DIR" | cut -f1)
echo ""
echo "✅ 빌드 완료!"
echo "   앱: $APP_DIR"
echo "   크기: $APP_SIZE"
echo ""
echo "🚀 실행: open \"$APP_DIR\""
echo "📂 Finder에서 열기: open \"$(dirname "$APP_DIR")\""
