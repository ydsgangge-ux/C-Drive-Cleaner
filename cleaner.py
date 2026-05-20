"""
C盘清理大师 - 核心清理引擎
扫描和清理 Windows 系统垃圾文件，功能对标专业清理工具
"""

import os
import shutil
import tempfile
import glob
import ctypes
import sys
import hashlib
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CleanItem:
    """单个清理项"""
    path: str
    size: int  # 字节
    category: str  # 分类
    description: str  # 描述


@dataclass
class CleanCategory:
    """清理分类"""
    name: str
    items: List[CleanItem] = field(default_factory=list)
    total_size: int = 0


def get_windows_drive() -> str:
    """获取 Windows 系统盘符"""
    return os.environ.get('SystemDrive', 'C:')


def format_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes <= 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"


def is_admin() -> bool:
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_user_profile() -> str:
    """获取用户目录"""
    return os.environ.get('USERPROFILE', '')


def run_as_admin():
    """以管理员权限重新启动"""
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)
    except Exception:
        pass


class WindowsCleaner:
    """Windows 系统清理器 - 专业版"""

    # 临时文件扩展名
    TEMP_EXTENSIONS = [
        '*.tmp', '*.temp', '*.~tmp', '*.~*',
        '*.log', '*.bak', '*.old', '*.syd',
        '*.dmp', '*.chk', '*.gid',
    ]

    # 缓存文件夹名称
    CACHE_FOLDERS = [
        'Cache', 'cache', 'CACHE',
        'caches', 'Caches', 'CACHES',
        '缓存', 'temp', 'Temp', 'TEMP',
        'tmp', 'Tmp', 'TMP',
    ]

    def __init__(self):
        self.drive = get_windows_drive()
        self.user_profile = get_user_profile()
        self.categories: Dict[str, CleanCategory] = {}
        self._stop_flag = False
        self._progress_callback = None

    def stop(self):
        """停止扫描"""
        self._stop_flag = True

    def reset(self):
        """重置状态"""
        self._stop_flag = False
        self.categories = {}

    def set_progress_callback(self, callback):
        """设置进度回调"""
        self._progress_callback = callback

    def _report_progress(self, current: int, total: int, message: str = ""):
        """报告进度"""
        if self._progress_callback:
            self._progress_callback(current, total, message)

    def _add_item(self, category_name: str, item: CleanItem):
        """添加清理项到分类"""
        if category_name not in self.categories:
            self.categories[category_name] = CleanCategory(name=category_name)
        self.categories[category_name].items.append(item)
        self.categories[category_name].total_size += item.size

    def _safe_scan_dir(self, directory: str, pattern: str = "*") -> List[str]:
        """安全扫描目录，忽略权限错误"""
        results = []
        try:
            if os.path.isdir(directory):
                for entry in glob.glob(os.path.join(directory, pattern), recursive=True):
                    if self._stop_flag:
                        break
                    results.append(entry)
        except (PermissionError, OSError):
            pass
        return results

    def _safe_get_size(self, path: str) -> int:
        """安全获取文件大小"""
        try:
            if os.path.isfile(path):
                return os.path.getsize(path)
            elif os.path.isdir(path):
                return self._get_dir_size(path)
        except (PermissionError, OSError):
            pass
        return 0

    def _get_dir_size(self, directory: str) -> int:
        """获取目录大小"""
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                if self._stop_flag:
                    break
                for f in filenames:
                    try:
                        fp = os.path.join(dirpath, f)
                        if os.path.isfile(fp):
                            total += os.path.getsize(fp)
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass
        return total

    # ============================================================
    # 模块 1: Windows 临时文件清理
    # ============================================================
    def scan_windows_temp(self) -> CleanCategory:
        """扫描 Windows 临时文件"""
        cat = CleanCategory(name="Windows 临时文件")
        temp_dirs = [
            tempfile.gettempdir(),
            os.path.join(self.drive, 'Windows', 'Temp'),
            os.path.join(self.user_profile, 'Local Settings', 'Temp'),
        ]

        for temp_dir in temp_dirs:
            if self._stop_flag:
                break
            if not os.path.isdir(temp_dir):
                continue

            # 扫描临时文件
            for ext in self.TEMP_EXTENSIONS:
                if self._stop_flag:
                    break
                files = self._safe_scan_dir(temp_dir, ext)
                for f in files:
                    size = self._safe_get_size(f)
                    if size > 0:
                        cat.items.append(CleanItem(
                            path=f, size=size,
                            category="Windows 临时文件",
                            description=f"临时文件 ({os.path.basename(f)})"
                        ))
                        cat.total_size += size

        return cat

    # ============================================================
    # 模块 2: 回收站清理
    # ============================================================
    def scan_recycle_bin(self) -> CleanCategory:
        """扫描回收站"""
        cat = CleanCategory(name="回收站")
        recycle_path = os.path.join(self.drive, '$Recycle.Bin')
        if os.path.isdir(recycle_path):
            size = self._get_dir_size(recycle_path)
            if size > 0:
                cat.items.append(CleanItem(
                    path=recycle_path, size=size,
                    category="回收站",
                    description="回收站中的已删除文件"
                ))
                cat.total_size = size
        return cat

    # ============================================================
    # 模块 3: 浏览器缓存清理
    # ============================================================
    def scan_browser_cache(self) -> CleanCategory:
        """扫描浏览器缓存"""
        cat = CleanCategory(name="浏览器缓存")

        # Chrome
        chrome_cache = os.path.join(
            self.user_profile, 'AppData', 'Local', 'Google', 'Chrome',
            'User Data', 'Default', 'Cache'
        )
        chrome_code_cache = os.path.join(
            self.user_profile, 'AppData', 'Local', 'Google', 'Chrome',
            'User Data', 'Default', 'Code Cache'
        )
        for cache_dir in [chrome_cache, chrome_code_cache]:
            if os.path.isdir(cache_dir):
                size = self._get_dir_size(cache_dir)
                if size > 0:
                    cat.items.append(CleanItem(
                        path=cache_dir, size=size,
                        category="浏览器缓存",
                        description=f"Chrome 缓存 ({os.path.basename(cache_dir)})"
                    ))
                    cat.total_size += size

        # Edge
        edge_cache = os.path.join(
            self.user_profile, 'AppData', 'Local', 'Microsoft', 'Edge',
            'User Data', 'Default', 'Cache'
        )
        if os.path.isdir(edge_cache):
            size = self._get_dir_size(edge_cache)
            if size > 0:
                cat.items.append(CleanItem(
                    path=edge_cache, size=size,
                    category="浏览器缓存",
                    description="Edge 缓存"
                ))
                cat.total_size += size

        # Firefox
        firefox_profiles = os.path.join(
            self.user_profile, 'AppData', 'Local', 'Mozilla', 'Firefox', 'Profiles'
        )
        if os.path.isdir(firefox_profiles):
            for profile in os.listdir(firefox_profiles):
                if self._stop_flag:
                    break
                cache2 = os.path.join(firefox_profiles, profile, 'cache2')
                if os.path.isdir(cache2):
                    size = self._get_dir_size(cache2)
                    if size > 0:
                        cat.items.append(CleanItem(
                            path=cache2, size=size,
                            category="浏览器缓存",
                            description="Firefox 缓存"
                        ))
                        cat.total_size += size

        return cat

    # ============================================================
    # 模块 4: 系统日志文件
    # ============================================================
    def scan_system_logs(self) -> CleanCategory:
        """扫描系统日志文件"""
        cat = CleanCategory(name="系统日志")
        log_dirs = [
            os.path.join(self.drive, 'Windows', 'Logs'),
            os.path.join(self.drive, 'Windows', 'Debug'),
        ]
        for log_dir in log_dirs:
            if self._stop_flag:
                break
            if os.path.isdir(log_dir):
                files = self._safe_scan_dir(log_dir, '*.log')
                for f in files:
                    size = self._safe_get_size(f)
                    if size > 0:
                        cat.items.append(CleanItem(
                            path=f, size=size,
                            category="系统日志",
                            description=f"日志文件 ({os.path.basename(f)})"
                        ))
                        cat.total_size += size

                # 也扫描 .etl 跟踪日志
                etl_files = self._safe_scan_dir(log_dir, '*.etl')
                for f in etl_files:
                    size = self._safe_get_size(f)
                    if size > 0:
                        cat.items.append(CleanItem(
                            path=f, size=size,
                            category="系统日志",
                            description=f"事件跟踪日志 ({os.path.basename(f)})"
                        ))
                        cat.total_size += size
        return cat

    # ============================================================
    # 模块 5: 大文件扫描 (>100MB)
    # ============================================================
    def scan_large_files(self, min_size_mb: int = 100) -> CleanCategory:
        """扫描 C 盘中的大文件"""
        cat = CleanCategory(name="大文件扫描")
        min_size = min_size_mb * 1024 * 1024
        scan_dirs = [
            self.user_profile,  # 用户目录
            os.path.join(self.drive, 'ProgramData'),
        ]

        # 要排除的目录（系统目录不扫描）
        exclude_dirs = {
            'Windows', 'Program Files', 'Program Files (x86)',
            'System32', 'System', '$Recycle.Bin',
            'System Volume Information',
        }

        scanned = 0
        for base_dir in scan_dirs:
            if self._stop_flag or not os.path.isdir(base_dir):
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(base_dir):
                    if self._stop_flag:
                        break
                    scanned += 1
                    if scanned % 500 == 0:
                        self._report_progress(scanned, 0, f"扫描大文件: {dirpath}")

                    # 跳过排除目录
                    rel = os.path.relpath(dirpath, base_dir)
                    parts = rel.split(os.sep)
                    if parts and parts[0] in exclude_dirs:
                        dirnames.clear()
                        continue

                    # 跳过 node_modules, .git 等
                    dirnames[:] = [d for d in dirnames
                                   if not d.startswith('.')
                                   and d not in ('node_modules', 'vendor', 'packages')]

                    for f in filenames:
                        if self._stop_flag:
                            break
                        try:
                            fp = os.path.join(dirpath, f)
                            if os.path.isfile(fp):
                                size = os.path.getsize(fp)
                                if size >= min_size:
                                    cat.items.append(CleanItem(
                                        path=fp, size=size,
                                        category="大文件扫描",
                                        description=f"大文件 ({format_size(size)})"
                                    ))
                                    cat.total_size += size
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass

        # 按大小排序
        cat.items.sort(key=lambda x: x.size, reverse=True)
        # 只保留前 200 个最大的
        cat.items = cat.items[:200]
        cat.total_size = sum(item.size for item in cat.items)
        return cat

    # ============================================================
    # 模块 6: 重复文件检测
    # ============================================================
    def scan_duplicate_files(self) -> CleanCategory:
        """扫描重复文件（按文件名+大小匹配）"""
        cat = CleanCategory(name="重复文件")
        scan_dirs = [
            os.path.join(self.user_profile, 'Downloads'),
            os.path.join(self.user_profile, 'Desktop'),
            os.path.join(self.user_profile, 'Documents'),
            os.path.join(self.user_profile, 'AppData', 'Local', 'Temp'),
        ]

        file_map = defaultdict(list)  # (name, size) -> [paths]
        scanned = 0

        for base_dir in scan_dirs:
            if self._stop_flag or not os.path.isdir(base_dir):
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(base_dir):
                    if self._stop_flag:
                        break
                    scanned += 1
                    if scanned % 1000 == 0:
                        self._report_progress(scanned, 0, f"扫描重复文件: {dirpath}")

                    # 跳过隐藏目录和缓存目录
                    dirnames[:] = [d for d in dirnames
                                   if not d.startswith('.')
                                   and d not in ('node_modules', '.git', '__pycache__')]

                    for f in filenames:
                        if self._stop_flag:
                            break
                        try:
                            fp = os.path.join(dirpath, f)
                            if os.path.isfile(fp) and os.path.getsize(fp) > 1024:  # >1KB
                                size = os.path.getsize(fp)
                                key = (f.lower(), size)
                                file_map[key].append(fp)
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass

        # 找出重复文件
        for (name, size), paths in file_map.items():
            if self._stop_flag:
                break
            if len(paths) >= 2:
                # 保留第一个，其余标记为重复
                for p in paths[1:]:
                    cat.items.append(CleanItem(
                        path=p, size=size,
                        category="重复文件",
                        description=f"重复文件: {name} ({format_size(size)})"
                    ))
                    cat.total_size += size

        # 按大小排序
        cat.items.sort(key=lambda x: x.size, reverse=True)
        cat.items = cat.items[:300]  # 限制数量
        cat.total_size = sum(item.size for item in cat.items)
        return cat

    # ============================================================
    # 模块 7: 空文件夹清理
    # ============================================================
    def scan_empty_folders(self) -> CleanCategory:
        """扫描空文件夹（限制深度为 3 层）"""
        cat = CleanCategory(name="空文件夹")
        scan_dirs = [
            os.path.join(self.user_profile, 'AppData', 'Local'),
            os.path.join(self.user_profile, 'AppData', 'Roaming'),
            os.path.join(self.user_profile, 'Documents'),
            os.path.join(self.user_profile, 'Downloads'),
        ]

        scanned = 0
        for base_dir in scan_dirs:
            if self._stop_flag or not os.path.isdir(base_dir):
                continue
            try:
                base_depth = base_dir.rstrip(os.sep).count(os.sep)
                for dirpath, dirnames, filenames in os.walk(base_dir, topdown=False):
                    if self._stop_flag:
                        break
                    current_depth = dirpath.rstrip(os.sep).count(os.sep) - base_depth
                    if current_depth > 3:
                        continue
                    scanned += 1
                    if scanned % 2000 == 0:
                        self._report_progress(scanned, 0, f"扫描空文件夹: {dirpath}")

                    # 检查是否为空目录
                    if not filenames and not dirnames:
                        try:
                            if len(os.listdir(dirpath)) == 0:
                                cat.items.append(CleanItem(
                                    path=dirpath, size=0,
                                    category="空文件夹",
                                    description=f"空文件夹 ({os.path.basename(dirpath)})"
                                ))
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass

        return cat

    # ============================================================
    # 模块 8: Windows 更新缓存清理
    # ============================================================
    def scan_windows_update_cache(self) -> CleanCategory:
        """扫描 Windows 更新缓存 (SoftwareDistribution)"""
        cat = CleanCategory(name="Windows 更新缓存")
        update_dir = os.path.join(self.drive, 'Windows', 'SoftwareDistribution', 'Download')
        if os.path.isdir(update_dir):
            size = self._get_dir_size(update_dir)
            if size > 0:
                cat.items.append(CleanItem(
                    path=update_dir, size=size,
                    category="Windows 更新缓存",
                    description="Windows Update 下载缓存"
                ))
                cat.total_size = size
        return cat

    # ============================================================
    # 模块 9: Prefetch 预读文件清理
    # ============================================================
    def scan_prefetch(self) -> CleanCategory:
        """扫描 Prefetch 预读文件"""
        cat = CleanCategory(name="预读文件 (Prefetch)")
        prefetch_dir = os.path.join(self.drive, 'Windows', 'Prefetch')
        if os.path.isdir(prefetch_dir):
            files = self._safe_scan_dir(prefetch_dir, '*.pf')
            for f in files:
                size = self._safe_get_size(f)
                if size > 0:
                    cat.items.append(CleanItem(
                        path=f, size=size,
                        category="预读文件 (Prefetch)",
                        description=f"预读文件 ({os.path.basename(f)})"
                    ))
                    cat.total_size += size
        return cat

    # ============================================================
    # 模块 10: 字体缓存清理
    # ============================================================
    def scan_font_cache(self) -> CleanCategory:
        """扫描字体缓存"""
        cat = CleanCategory(name="字体缓存")
        font_cache_paths = [
            os.path.join(self.drive, 'Windows', 'ServiceProfiles', 'LocalService',
                         'AppData', 'Local', 'FontCache'),
            os.path.join(self.drive, 'Windows', 'System32', 'FNTCACHE.DAT'),
        ]
        for path in font_cache_paths:
            if self._stop_flag:
                break
            if os.path.isdir(path):
                size = self._get_dir_size(path)
                if size > 0:
                    cat.items.append(CleanItem(
                        path=path, size=size,
                        category="字体缓存",
                        description=f"字体缓存 ({os.path.basename(path)})"
                    ))
                    cat.total_size += size
            elif os.path.isfile(path):
                size = self._safe_get_size(path)
                if size > 0:
                    cat.items.append(CleanItem(
                        path=path, size=size,
                        category="字体缓存",
                        description="字体缓存文件 (FNTCACHE.DAT)"
                    ))
                    cat.total_size += size
        return cat

    # ============================================================
    # 模块 11: 缩略图缓存清理
    # ============================================================
    def scan_thumbnail_cache(self) -> CleanCategory:
        """扫描缩略图缓存"""
        cat = CleanCategory(name="缩略图缓存")
        thumb_path = os.path.join(
            self.user_profile, 'AppData', 'Local', 'Microsoft', 'Windows', 'Explorer'
        )
        if os.path.isdir(thumb_path):
            patterns = ['thumbcache_*.db', 'thumbcache_*.db_*', 'iconcache_*.db']
            for pattern in patterns:
                if self._stop_flag:
                    break
                files = self._safe_scan_dir(thumb_path, pattern)
                for f in files:
                    size = self._safe_get_size(f)
                    if size > 0:
                        cat.items.append(CleanItem(
                            path=f, size=size,
                            category="缩略图缓存",
                            description=f"缩略图缓存 ({os.path.basename(f)})"
                        ))
                        cat.total_size += size
        return cat

    # ============================================================
    # 模块 12: DNS 缓存清理 (通过命令)
    # ============================================================
    def scan_dns_cache(self) -> CleanCategory:
        """DNS 缓存（通过 ipconfig /flushdns 清理）"""
        cat = CleanCategory(name="DNS 缓存")
        # DNS 缓存大小无法直接获取，标记为可清理项
        cat.items.append(CleanItem(
            path="dns_cache", size=0,
            category="DNS 缓存",
            description="DNS 解析缓存 (ipconfig /flushdns)"
        ))
        return cat

    # ============================================================
    # 模块 13: 剪贴板历史清理
    # ============================================================
    def scan_clipboard_history(self) -> CleanCategory:
        """扫描剪贴板历史"""
        cat = CleanCategory(name="剪贴板历史")
        clipboard_path = os.path.join(
            self.user_profile, 'AppData', 'Local', 'Microsoft', 'Windows',
            'Clipboard'
        )
        if os.path.isdir(clipboard_path):
            size = self._get_dir_size(clipboard_path)
            if size > 0:
                cat.items.append(CleanItem(
                    path=clipboard_path, size=size,
                    category="剪贴板历史",
                    description="剪贴板历史记录"
                ))
                cat.total_size = size
        return cat

    # ============================================================
    # 模块 14: 软件卸载残留扫描
    # ============================================================
    def scan_software_leftovers(self) -> CleanCategory:
        """扫描软件卸载残留（限制深度为 3 层）"""
        cat = CleanCategory(name="软件卸载残留")
        scan_dirs = [
            os.path.join(self.user_profile, 'AppData', 'Local'),
            os.path.join(self.user_profile, 'AppData', 'Roaming'),
        ]

        # 常见的已卸载软件残留文件夹特征
        leftover_names = {
            'Uninstall', 'uninstall', 'UNINSTALL',
            'CrashReports', 'crashreports',
            'Update', 'update', 'Updater', 'updater',
            'Logs', 'logs', 'LOG',
            'Backup', 'backup', 'BACKUP',
        }

        scanned = 0
        for base_dir in scan_dirs:
            if self._stop_flag or not os.path.isdir(base_dir):
                continue
            try:
                base_depth = base_dir.rstrip(os.sep).count(os.sep)
                for dirpath, dirnames, filenames in os.walk(base_dir, topdown=False):
                    if self._stop_flag:
                        break
                    current_depth = dirpath.rstrip(os.sep).count(os.sep) - base_depth
                    if current_depth > 3:
                        continue
                    scanned += 1
                    if scanned % 3000 == 0:
                        self._report_progress(scanned, 0, f"扫描残留: {dirpath}")

                    # 检查文件夹名是否匹配残留特征
                    dir_name = os.path.basename(dirpath)
                    if dir_name in leftover_names:
                        try:
                            size = self._get_dir_size_fast(dirpath, 1)
                            if 0 < size < 50 * 1024 * 1024:  # <50MB 的残留
                                cat.items.append(CleanItem(
                                    path=dirpath, size=size,
                                    category="软件卸载残留",
                                    description=f"可能残留: {dir_name} ({format_size(size)})"
                                ))
                                cat.total_size += size
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass

        return cat

    # ============================================================
    # 模块 15: 无效快捷方式检测
    # ============================================================
    def scan_invalid_shortcuts(self) -> CleanCategory:
        """检测无效的快捷方式 (.lnk 指向不存在的目标)"""
        cat = CleanCategory(name="无效快捷方式")
        import win32com.client  # 可选依赖

        scan_dirs = [
            os.path.join(self.user_profile, 'Desktop'),
            os.path.join(self.user_profile, 'AppData', 'Roaming',
                         'Microsoft', 'Windows', 'Start Menu'),
            os.path.join(self.drive, 'ProgramData',
                         'Microsoft', 'Windows', 'Start Menu'),
        ]

        scanned = 0
        for base_dir in scan_dirs:
            if self._stop_flag or not os.path.isdir(base_dir):
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(base_dir):
                    if self._stop_flag:
                        break
                    scanned += 1
                    if scanned % 500 == 0:
                        self._report_progress(scanned, 0, f"扫描快捷方式: {dirpath}")

                    for f in filenames:
                        if self._stop_flag:
                            break
                        if f.lower().endswith('.lnk'):
                            fp = os.path.join(dirpath, f)
                            try:
                                # 简单检测：检查文件大小是否为 0
                                size = os.path.getsize(fp)
                                if size == 0:
                                    cat.items.append(CleanItem(
                                        path=fp, size=0,
                                        category="无效快捷方式",
                                        description=f"无效快捷方式 ({f})"
                                    ))
                                else:
                                    # 尝试用 shell 方式检测
                                    result = subprocess.run(
                                        ['powershell', '-Command',
                                         f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{fp}');"
                                         f"if(!(Test-Path $s.TargetPath)){{'INVALID'}}else{{'OK'}}"],
                                        capture_output=True, text=True, timeout=5
                                    )
                                    if 'INVALID' in result.stdout:
                                        cat.items.append(CleanItem(
                                            path=fp, size=size,
                                            category="无效快捷方式",
                                            description=f"目标不存在: {f}"
                                        ))
                            except (PermissionError, OSError, subprocess.TimeoutExpired):
                                pass
            except (PermissionError, OSError):
                pass

        return cat

    # ============================================================
    # 模块 16: 磁盘空间分析
    # ============================================================
    def _get_dir_size_fast(self, directory: str, max_depth: int = 2) -> int:
        """快速获取目录大小（限制深度）"""
        total = 0
        try:
            base_depth = directory.rstrip(os.sep).count(os.sep)
            for dirpath, dirnames, filenames in os.walk(directory):
                if self._stop_flag:
                    break
                current_depth = dirpath.rstrip(os.sep).count(os.sep) - base_depth
                if current_depth > max_depth:
                    dirnames.clear()
                    continue
                for f in filenames:
                    try:
                        fp = os.path.join(dirpath, f)
                        if os.path.isfile(fp):
                            total += os.path.getsize(fp)
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass
        return total

    def scan_disk_analysis(self) -> CleanCategory:
        """磁盘空间分析 - 统计各目录占用（快速模式，限制深度）"""
        cat = CleanCategory(name="磁盘空间分析")
        scan_targets = [
            ("用户目录", self.user_profile, 1),
            ("ProgramData", os.path.join(self.drive, 'ProgramData'), 1),
            ("Windows", os.path.join(self.drive, 'Windows'), 1),
        ]

        for label, dir_path, depth in scan_targets:
            if self._stop_flag or not os.path.isdir(dir_path):
                continue
            size = self._get_dir_size_fast(dir_path, depth)
            if size > 0:
                cat.items.append(CleanItem(
                    path=dir_path, size=size,
                    category="磁盘空间分析",
                    description=f"{label}: {format_size(size)}"
                ))
                cat.total_size += size

        # 用户目录下的大子目录（只扫1层）
        user_subdirs = [
            'Desktop', 'Documents', 'Downloads', 'Pictures',
            'Music', 'Videos',
        ]
        for sub in user_subdirs:
            if self._stop_flag:
                break
            sub_path = os.path.join(self.user_profile, sub)
            if os.path.isdir(sub_path):
                size = self._get_dir_size_fast(sub_path, 1)
                if size > 0:
                    cat.items.append(CleanItem(
                        path=sub_path, size=size,
                        category="磁盘空间分析",
                        description=f"  ├ {sub}: {format_size(size)}"
                    ))

        cat.items.sort(key=lambda x: x.size, reverse=True)
        return cat

    # ============================================================
    # 清理执行
    # ============================================================
    def clean_items(self, items: List[CleanItem], callback=None) -> Tuple[int, int]:
        """执行清理，返回 (成功数, 失败数)"""
        success = 0
        failed = 0
        total = len(items)

        for i, item in enumerate(items):
            if self._stop_flag:
                break

            if callback:
                callback(i + 1, total, f"清理: {os.path.basename(item.path)}")

            try:
                path = item.path

                # 特殊处理：DNS 缓存
                if path == "dns_cache":
                    subprocess.run(['ipconfig', '/flushdns'],
                                   capture_output=True, timeout=10)
                    success += 1
                    continue

                if os.path.isfile(path):
                    os.remove(path)
                    success += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    # 验证是否删除成功
                    if not os.path.exists(path):
                        success += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        return success, failed

    # ============================================================
    # 全量扫描
    # ============================================================
    def scan_all(self, progress_callback=None) -> Dict[str, CleanCategory]:
        """执行全量扫描"""
        self.reset()
        if progress_callback:
            self.set_progress_callback(progress_callback)

        scan_modules = [
            ("Windows 临时文件", self.scan_windows_temp),
            ("回收站", self.scan_recycle_bin),
            ("浏览器缓存", self.scan_browser_cache),
            ("系统日志", self.scan_system_logs),
            ("Windows 更新缓存", self.scan_windows_update_cache),
            ("预读文件 (Prefetch)", self.scan_prefetch),
            ("字体缓存", self.scan_font_cache),
            ("缩略图缓存", self.scan_thumbnail_cache),
            ("剪贴板历史", self.scan_clipboard_history),
            ("DNS 缓存", self.scan_dns_cache),
            ("空文件夹", self.scan_empty_folders),
            ("软件卸载残留", self.scan_software_leftovers),
            ("无效快捷方式", self.scan_invalid_shortcuts),
            ("大文件扫描", self.scan_large_files),
            ("重复文件", self.scan_duplicate_files),
        ]

        total_modules = len(scan_modules)
        for idx, (name, scan_func) in enumerate(scan_modules):
            if self._stop_flag:
                break
            self._report_progress(idx, total_modules, f"正在扫描: {name}")
            try:
                cat = scan_func()
                if cat.items:
                    self.categories[name] = cat
            except Exception as e:
                print(f"扫描 {name} 失败: {e}")

        self._report_progress(total_modules, total_modules, "扫描完成")
        return self.categories
