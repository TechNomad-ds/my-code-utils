#!/usr/bin/env python3
"""
获取本机 SSH 公钥：若已存在则直接输出，否则创建后输出。
支持 Linux / macOS / Windows（需已安装 OpenSSH 客户端）。
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# 按优先级查找的密钥类型（现代系统优先 ed25519）
KEY_TYPES = ("ed25519", "rsa", "ecdsa", "dsa")
DEFAULT_KEY_TYPE = "ed25519"


def ssh_dir() -> Path:
    """返回当前用户的 ~/.ssh 目录。"""
    home = Path.home()
    if platform.system() == "Windows":
        # Windows OpenSSH 默认路径
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            return Path(userprofile) / ".ssh"
    return home / ".ssh"


def find_public_key(directory: Path) -> Path | None:
    """在目录中查找第一个存在的公钥文件。"""
    for key_type in KEY_TYPES:
        pub = directory / f"id_{key_type}.pub"
        if pub.is_file() and pub.stat().st_size > 0:
            return pub
    return None


def ensure_ssh_dir(directory: Path) -> None:
    """创建 .ssh 目录并设置合适权限（Unix）。"""
    directory.mkdir(parents=True, exist_ok=True)
    if platform.system() != "Windows":
        os.chmod(directory, 0o700)


def find_ssh_keygen() -> str:
    """定位 ssh-keygen 可执行文件。"""
    path = shutil.which("ssh-keygen")
    if path:
        return path
    # Windows 常见安装路径
    if platform.system() == "Windows":
        candidates = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "OpenSSH"
            / "ssh-keygen.exe",
            Path(os.environ.get("SystemRoot", r"C:\Windows"))
            / "System32"
            / "OpenSSH"
            / "ssh-keygen.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    sys.stderr.write(
        "错误: 未找到 ssh-keygen。请安装 OpenSSH 客户端后重试。\n"
        "  Linux: sudo apt install openssh-client / sudo yum install openssh-clients\n"
        "  macOS: 通常已预装\n"
        "  Windows: 设置 -> 应用 -> 可选功能 -> OpenSSH 客户端\n"
    )
    sys.exit(1)


def generate_key(directory: Path, key_type: str = DEFAULT_KEY_TYPE) -> Path:
    """生成新的 SSH 密钥对，返回公钥路径。"""
    ssh_keygen = find_ssh_keygen()
    private_key = directory / f"id_{key_type}"
    public_key = directory / f"id_{key_type}.pub"

    if private_key.exists():
        # 私钥存在但公钥缺失时，从私钥恢复公钥
        result = subprocess.run(
            [ssh_keygen, "-y", "-f", str(private_key)],
            check=True,
            capture_output=True,
            text=True,
        )
        public_key.write_text(result.stdout, encoding="utf-8")
        return public_key

    cmd = [
        ssh_keygen,
        "-q",  # 静默模式，避免污染 stdout
        "-t",
        key_type,
        "-f",
        str(private_key),
        "-N",
        "",  # 空密码，非交互
        "-C",
        f"{os.environ.get('USER', os.environ.get('USERNAME', 'user'))}@{platform.node()}",
    ]
    # ed25519 不需要额外参数；rsa 使用较安全的默认长度
    if key_type == "rsa":
        cmd.extend(["-b", "4096"])

    subprocess.run(cmd, check=True, input="\n", text=True)

    if platform.system() != "Windows":
        os.chmod(private_key, 0o600)
        os.chmod(public_key, 0o644)

    return public_key


def get_public_key() -> str:
    """获取公钥内容（查找或创建）。"""
    directory = ssh_dir()
    ensure_ssh_dir(directory)

    pub_path = find_public_key(directory)
    if pub_path is None:
        pub_path = generate_key(directory)

    content = pub_path.read_text(encoding="utf-8").strip()
    if not content:
        sys.stderr.write(f"错误: 公钥文件为空: {pub_path}\n")
        sys.exit(1)
    return content


def main() -> int:
    try:
        print(get_public_key())
        return 0
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"错误: ssh-keygen 执行失败: {exc}\n")
        if exc.stderr:
            sys.stderr.write(exc.stderr)
        return 1
    except OSError as exc:
        sys.stderr.write(f"错误: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
