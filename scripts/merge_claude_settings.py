#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 claude-settings-snippet.json 安全合并进 ~/.claude/settings.json
- 数组（allowedDomains / permissions.allow）：并集去重，保留你已有的条目
- 对象：递归合并，已有键不丢
- 写入前自动备份到 ~/.claude/settings.json.bak-<时间戳>

用法：
    python3 merge_claude_settings.py            # 预览（dry-run，不写盘）
    python3 merge_claude_settings.py --apply    # 实际写入
"""
import json, os, shutil, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SNIPPET = os.path.join(HERE, "claude-settings-snippet.json")
TARGET = os.path.expanduser("~/.claude/settings.json")


def merge(old, new):
    """递归合并：list 取并集，dict 递归，其余以新值为准。"""
    if isinstance(old, list) and isinstance(new, list):
        out = list(old)
        for x in new:
            if x not in out:
                out.append(x)
        return out
    if isinstance(old, dict) and isinstance(new, dict):
        out = dict(old)
        for k, v in new.items():
            out[k] = merge(old[k], v) if k in old else v
        return out
    return new


def main():
    apply = "--apply" in sys.argv
    snippet = json.load(open(SNIPPET, encoding="utf-8"))
    if os.path.exists(TARGET):
        old = json.load(open(TARGET, encoding="utf-8"))
        print(f"现有 settings.json：{len(json.dumps(old))} 字节")
    else:
        old = {}
        print("settings.json 不存在，将新建")
    merged = merge(old, snippet)

    doms = merged.get("sandbox", {}).get("network", {}).get("allowedDomains", [])
    added = [d for d in doms if d not in old.get("sandbox", {}).get("network", {}).get("allowedDomains", [])]
    print(f"allowedDomains：{len(doms)} 条（新增 {len(added)} 条）")
    print(f"permissions.allow：{len(merged.get('permissions', {}).get('allow', []))} 条")
    key_ok = any(d == "*.semianalysis.com" for d in doms)
    print(f"关键检查 *.semianalysis.com：{'✓ 已覆盖' if key_ok else '✗ 缺失'}")

    if not apply:
        print("\n[预览模式] 未写盘。确认无误后运行：\n  python3 merge_claude_settings.py --apply")
        return 0
    if os.path.exists(TARGET):
        bak = f"{TARGET}.bak-{datetime.now():%Y%m%d-%H%M%S}"
        shutil.copy2(TARGET, bak)
        print(f"已备份：{bak}")
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    with open(TARGET, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"已写入 {TARGET}。重启 Claude App 并新开会话后生效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
