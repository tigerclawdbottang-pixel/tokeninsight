#!/bin/bash
# GPU 现货快照每日更新链路：gpu-radar 采集 → 导出快照 → 重建站点 → 提交（推送尽力而为）
# 路径以脚本自身位置为锚（本机在 modelprice/scripts/ 下），两种环境通用：
#   - macOS 终端直跑：需 gpu-radar 在 $HOME/Documents/TAI/gpu-radar（或用 GPU_RADAR_BACKEND 指定）
#   - 本 App 沙箱/定时任务：用环境变量 GPU_RADAR_BACKEND 指向沙箱挂载路径
set -e
M="$(cd "$(dirname "$0")/.." && pwd)"
R="${GPU_RADAR_BACKEND:-$HOME/Documents/TAI/gpu-radar/backend}"

echo "== 1/4 gpu-radar 单轮采集（$R）=="
cd "$R"
if [ -x ./.venv/bin/python ] && [ "$(uname -s)" = "Darwin" ]; then
  PY=./.venv/bin/python
else
  V=.venv-linux
  if [ ! -x $V/bin/python ]; then
    echo "首次：创建 Linux venv 并安装依赖（需要 pypi.org 可达）"
    python3 -m venv $V
    $V/bin/pip install -q -r requirements.txt
  fi
  PY=$V/bin/python
fi
$PY scripts/collect_once.py

echo "== 2/4 导出 gpu_snapshot.json =="
cd "$M"
python3 scripts/collect_gpu.py

echo "== 3/4 重建站点 =="
MODELPRICE_EMBED_KEY=0 python3 scripts/build_site.py

echo "== 4/4 提交并推送 =="
git add -A
if git diff --cached --quiet; then
  echo "无数据变化，跳过提交"
else
  git -c user.name="tigertang" -c user.email="[EMAIL_REDACTED]" \
      commit -m "GPU 现货快照更新 $(date +%F)"
  if git push origin HEAD 2>&1; then
    echo "已推送"
  else
    echo "⚠️ 推送失败（沙箱无 git 凭据或网络未放行）——已本地提交，请在本机终端 git push"
  fi
fi
echo "== 完成 =="
