#!/usr/bin/env python3
"""
从 Hugging Face Hub 下载指定的模型 / 数据集 / 普通仓库到本地路径。

最简单的用法：直接修改下面 “配置区” 的变量，然后运行：
    python hf_download.py

也支持命令行参数覆盖配置（命令行优先级高于配置区）：
    python hf_download.py --repo-id bert-base-uncased --repo-type model --local-dir ./bert
    python hf_download.py --repo-id squad --repo-type dataset --local-dir ./squad
"""

from __future__ import annotations

import argparse
import os
import sys

# ============================== 配置区 ==============================
# 直接改这里的变量即可使用，无需命令行参数。

# 仓库 ID，形如 "用户名/仓库名" 或官方短名（如 "bert-base-uncased"）。
REPO_ID = "bert-base-uncased"

# 仓库类型: "model"（模型）/ "dataset"（数据集）/ "space"（空间）。
REPO_TYPE = "model"

# 下载到的本地目录。
LOCAL_DIR = "./hf_download"

# 指定版本：分支名、tag 或 commit hash；None 表示默认分支（通常是 main）。
REVISION = None

# 只下载匹配这些通配符的文件，None 表示全部。例: ["*.safetensors", "*.json"]
ALLOW_PATTERNS = None

# 跳过匹配这些通配符的文件，None 表示不跳过。例: ["*.bin", "*.h5"]
IGNORE_PATTERNS = None

# 访问令牌：私有仓库需要。None 时回退到环境变量 HF_TOKEN / 已登录凭证。
HF_TOKEN = None

# 镜像站点。国内可设为 "https://hf-mirror.com"；None 表示官方默认。
ENDPOINT = None

# 并发下载线程数。
MAX_WORKERS = 8
# ===================================================================


def parse_args() -> argparse.Namespace:
    """解析命令行参数，未提供的项回退到配置区默认值。"""
    parser = argparse.ArgumentParser(
        description="下载 Hugging Face 上的模型或数据集到指定路径。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--repo-id", default=REPO_ID, help="仓库 ID")
    parser.add_argument(
        "--repo-type",
        default=REPO_TYPE,
        choices=("model", "dataset", "space"),
        help="仓库类型",
    )
    parser.add_argument("--local-dir", default=LOCAL_DIR, help="本地保存目录")
    parser.add_argument("--revision", default=REVISION, help="分支 / tag / commit")
    parser.add_argument(
        "--allow-patterns",
        nargs="*",
        default=ALLOW_PATTERNS,
        help="仅下载匹配的文件通配符",
    )
    parser.add_argument(
        "--ignore-patterns",
        nargs="*",
        default=IGNORE_PATTERNS,
        help="跳过匹配的文件通配符",
    )
    parser.add_argument("--token", default=HF_TOKEN, help="访问令牌（私有仓库）")
    parser.add_argument("--endpoint", default=ENDPOINT, help="镜像 endpoint")
    parser.add_argument(
        "--max-workers", type=int, default=MAX_WORKERS, help="并发下载线程数"
    )
    return parser.parse_args()


def import_snapshot_download():
    """延迟导入 huggingface_hub，缺失时给出安装提示。"""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        sys.stderr.write(
            "错误: 未安装 huggingface_hub。请先安装：\n"
            "  pip install -U huggingface_hub\n"
            "  # 如需更快下载可一并安装: pip install -U hf_transfer\n"
        )
        sys.exit(1)
    return snapshot_download


def download(args: argparse.Namespace) -> str:
    """执行下载，返回本地目录路径。"""
    snapshot_download = import_snapshot_download()

    # 镜像 endpoint 需在导入后通过环境变量生效。
    if args.endpoint:
        os.environ["HF_ENDPOINT"] = args.endpoint

    token = args.token or os.environ.get("HF_TOKEN")

    sys.stderr.write(
        f"开始下载: repo_id={args.repo_id} type={args.repo_type} "
        f"-> {args.local_dir}\n"
    )

    local_path = snapshot_download(
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        local_dir=args.local_dir,
        revision=args.revision,
        allow_patterns=args.allow_patterns,
        ignore_patterns=args.ignore_patterns,
        token=token,
        max_workers=args.max_workers,
    )
    return local_path


def main() -> int:
    args = parse_args()
    try:
        local_path = download(args)
    except KeyboardInterrupt:
        sys.stderr.write("\n已取消。\n")
        return 130
    except Exception as exc:  # noqa: BLE001 - 顶层兜底，打印简洁错误
        sys.stderr.write(f"错误: 下载失败: {exc}\n")
        return 1

    sys.stderr.write("下载完成。\n")
    print(local_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
