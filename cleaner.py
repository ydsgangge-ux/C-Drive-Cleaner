"""
C盘清理工具 - 核心清理引擎
扫描和清理 Windows 系统垃圾文件
"""

import os
import shutil
import tempfile
import glob
import ctypes
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, field


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


class WindowsCleaner:
    """Windows 系统清理器"""

    # 临时文件扩展名
    TEMP_EXTENSIONS = [
        '*.tmp', '*.temp', '*.~tmp', '*.~*',
        '*.log', '*.bak', '*.old', '*.syd',
        '*.dmp', '*.chk', '*.gid',
    ]

    # 缓存文件夹名称
    CACHE_FOLDERS = [
        'Cache', 'cache', 'CACHE',
        'Temp', 'temp', 'TEMP',
        'Temporary Internet Files',
        'INetCache',
        'Code Cache',
        'GPUCache',
        'ServiceWorkerCache',
    ]

    def __init__(self, drive: str = None):
        self.drive = drive or get_windows_drive()
        self.user_profile = get_user_profile()
        self.categories: Dict[str, CleanCategory] = {}
        self.total_size = 0
        self._stop_flag = False

    def stop(self):
        """停止扫描"""
        self._stop_flag = True

    def reset(self):
        """重置状态"""
        self.categories = {}
        self.total_size = 0
        self._stop_flag = False

    def scan_windows_temp(self) -> List[CleanItem]:
        """扫描 Windows 临时文件夹"""
        items = []
        temp_paths = [
            os.environ.get('TEMP', ''),
            os.environ.get('TMP', ''),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
        ]

        for temp_dir in temp_paths:
            if not temp_dir or not os.path.exists(temp_dir):
                continue
            try:
                for root, dirs, files in os.walk(temp_dir):
                    if self._stop_flag:
                        break
                    # 跳过正在使用的文件
                    for f in files:
                        try:
                            fpath = os.path.join(root, f)
                            try:
                                size = os.path.getsize(fpath)
                            except (OSError, PermissionError):
                                size = 0
                            if size > 0:
                                items.append(CleanItem(
                                    path=fpath,
                                    size=size,
                                    category='Windows临时文件',
                                    description=f'临时文件: {f}'
                                ))
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue
            if self._stop_flag:
                break
        return items

    def scan_recycle_bin(self) -> List[CleanItem]:
        """扫描回收站（仅获取大小信息）"""
        items = []
        try:
            # 回收站路径
            recycle_path = os.path.join(self.drive, '$Recycle.Bin')
            if os.path.exists(recycle_path):
                total_size = 0
                for root, dirs, files in os.walk(recycle_path):
                    if self._stop_flag:
                        break
                    for f in files:
                        try:
                            fpath = os.path.join(root, f)
                            try:
                                total_size += os.path.getsize(fpath)
                            except (OSError, PermissionError):
                                pass
                        except (OSError, PermissionError):
                            continue
                if total_size > 0:
                    items.append(CleanItem(
                        path=recycle_path,
                        size=total_size,
                        category='回收站',
                        description=f'回收站文件 (共 {format_size(total_size)})'
                    ))
        except (OSError, PermissionError):
            pass
        return items

    def scan_user_temp(self) -> List[CleanItem]:
        """扫描用户临时文件夹"""
        items = []
        if not self.user_profile:
            return items

        temp_dirs = [
            os.path.join(self.user_profile, 'AppData', 'Local', 'Temp'),
            os.path.join(self.user_profile, 'AppData', 'Local', 'Microsoft', 'Windows', 'INetCache'),
            os.path.join(self.user_profile, 'AppData', 'Local', 'Microsoft', 'Windows', 'Temporary Internet Files'),
        ]

        for temp_dir in temp_dirs:
            if not os.path.exists(temp_dir):
                continue
            try:
                for root, dirs, files in os.walk(temp_dir):
                    if self._stop_flag:
                        break
                    for f in files:
                        try:
                            fpath = os.path.join(root, f)
                            try:
                                size = os.path.getsize(fpath)
                            except (OSError, PermissionError):
                                size = 0
                            if size > 0:
                                items.append(CleanItem(
                                    path=fpath,
                                    size=size,
                                    category='用户临时文件',
                                    description=f'用户临时文件: {f}'
                                ))
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue
            if self._stop_flag:
                break
        return items

    def scan_browser_cache(self) -> List[CleanItem]:
        """扫描浏览器缓存"""
        items = []
        if not self.user_profile:
            return items

        # Chrome/Edge 缓存
        chrome_cache_paths = [
            os.path.join(self.user_profile, 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
            os.path.join(self.user_profile, 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Code Cache'),
            os.path.join(self.user_profile, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
            os.path.join(self.user_profile, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Code Cache'),
        ]

        for cache_dir in chrome_cache_paths:
            if not os.path.exists(cache_dir):
                continue
            try:
                total_size = 0
                file_count = 0
                for root, dirs, files in os.walk(cache_dir):
                    if self._stop_flag:
                        break
                    for f in files:
                        try:
                            fpath = os.path.join(root, f)
                            try:
                                total_size += os.path.getsize(fpath)
                                file_count += 1
                            except (OSError, PermissionError):
                                pass
                        except (OSError, PermissionError):
                            continue
                if total_size > 0:
                    browser_name = 'Chrome' if 'Google' in cache_dir else 'Edge'
                    items.append(CleanItem(
                        path=cache_dir,
                        size=total_size,
                        category='浏览器缓存',
                        description=f'{browser_name} 缓存 ({file_count} 个文件, 共 {format_size(total_size)})'
                    ))
            except (OSError, PermissionError):
                continue
            if self._stop_flag:
                break
        return items

    def scan_prefetch(self) -> List[CleanItem]:
        """扫描预读取文件"""
        items = []
        prefetch_dir = os.path.join(self.drive, 'Windows', 'Prefetch')
        if not os.path.exists(prefetch_dir):
            return items

        try:
            for f in os.listdir(prefetch_dir):
                if self._stop_flag:
                    break
                try:
                    fpath = os.path.join(prefetch_dir, f)
                    if os.path.isfile(fpath):
                        size = os.path.getsize(fpath)
                        if size > 0:
                            items.append(CleanItem(
                                path=fpath,
                                size=size,
                                category='预读取文件',
                                description=f'Prefetch: {f}'
                            ))
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass
        return items

    def scan_recent_documents(self) -> List[CleanItem]:
        """扫描最近文档记录"""
        items = []
        if not self.user_profile:
            return items

        recent_dir = os.path.join(self.user_profile, 'AppData', 'Roaming', 'Microsoft', 'Windows', 'Recent')
        if not os.path.exists(recent_dir):
            return items

        try:
            for f in os.listdir(recent_dir):
                if self._stop_flag:
                    break
                try:
                    fpath = os.path.join(recent_dir, f)
                    if os.path.isfile(fpath):
                        size = os.path.getsize(fpath)
                        if size > 0:
                            items.append(CleanItem(
                                path=fpath,
                                size=size,
                                category='最近文档',
                                description=f'最近文档快捷方式: {f}'
                            ))
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass
        return items

    def scan_downloads_folder(self) -> List[CleanItem]:
        """扫描下载文件夹中的临时/无用文件"""
        items = []
        if not self.user_profile:
            return items

        downloads_dir = os.path.join(self.user_profile, 'Downloads')
        if not os.path.exists(downloads_dir):
            return items

        # 常见的无用下载文件扩展名
        useless_exts = {'.tmp', '.temp', '.part', '.crdownload', '.download'}
        try:
            for f in os.listdir(downloads_dir):
                if self._stop_flag:
                    break
                ext = os.path.splitext(f)[1].lower()
                if ext in useless_exts:
                    try:
                        fpath = os.path.join(downloads_dir, f)
                        if os.path.isfile(fpath):
                            size = os.path.getsize(fpath)
                            if size > 0:
                                items.append(CleanItem(
                                    path=fpath,
                                    size=size,
                                    category='下载残留',
                                    description=f'未完成的下载: {f}'
                                ))
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
        return items

    def scan_dotnet_cache(self) -> List[CleanItem]:
        """扫描 .NET 程序集缓存"""
        items = []
        if not self.user_profile:
            return items

        dotnet_dirs = [
            os.path.join(self.user_profile, 'AppData', 'Local', 'assembly'),
            os.path.join(self.user_profile, 'AppData', 'Local', 'Microsoft', 'CLR_v4.0'),
        ]

        for d in dotnet_dirs:
            if not os.path.exists(d):
                continue
            try:
                total_size = 0
                file_count = 0
                for root, dirs, files in os.walk(d):
                    if self._stop_flag:
                        break
                    for f in files:
                        try:
                            fpath = os.path.join(root, f)
                            try:
                                total_size += os.path.getsize(fpath)
                                file_count += 1
                            except (OSError, PermissionError):
                                pass
                        except (OSError, PermissionError):
                            continue
                if total_size > 0:
                    items.append(CleanItem(
                        path=d,
                        size=total_size,
                        category='.NET缓存',
                        description=f'.NET 程序集缓存 ({file_count} 个文件, 共 {format_size(total_size)})'
                    ))
            except (OSError, PermissionError):
                continue
            if self._stop_flag:
                break
        return items

    def scan_all(self, progress_callback=None) -> Dict[str, CleanCategory]:
        """扫描所有垃圾文件"""
        self.reset()
        self.categories = {}

        scan_funcs = [
            ('Windows临时文件', self.scan_windows_temp),
            ('用户临时文件', self.scan_user_temp),
            ('浏览器缓存', self.scan_browser_cache),
            ('预读取文件', self.scan_prefetch),
            ('最近文档', self.scan_recent_documents),
            ('下载残留', self.scan_downloads_folder),
            ('回收站', self.scan_recycle_bin),
            ('.NET缓存', self.scan_dotnet_cache),
        ]

        total_steps = len(scan_funcs)
        for i, (cat_name, func) in enumerate(scan_funcs):
            if self._stop_flag:
                break
            try:
                items = func()
                if items:
                    cat = CleanCategory(name=cat_name, items=items)
                    cat.total_size = sum(item.size for item in items)
                    self.categories[cat_name] = cat
                    self.total_size += cat.total_size
            except Exception:
                pass

            if progress_callback:
                progress_callback(i + 1, total_steps, cat_name)

        return self.categories

    def delete_items(self, items: List[CleanItem], delete_callback=None) -> Tuple[int, int]:
        """
        删除指定的文件列表
        返回: (成功数, 失败数)
        """
        success = 0
        failed = 0
        total = len(items)

        for i, item in enumerate(items):
            if self._stop_flag:
                break
            try:
                path = item.path
                if not os.path.exists(path):
                    success += 1
                    continue

                if os.path.isfile(path):
                    os.chmod(path, 0o777)  # 尝试解除权限限制
                    os.remove(path)
                    success += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    if not os.path.exists(path):
                        success += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            except (OSError, PermissionError):
                failed += 1
            except Exception:
                failed += 1

            if delete_callback:
                delete_callback(i + 1, total, item.description)

        return success, failed

    def delete_category(self, category_name: str, delete_callback=None) -> Tuple[int, int]:
        """删除指定分类的所有文件"""
        if category_name not in self.categories:
            return 0, 0
        return self.delete_items(self.categories[category_name].items, delete_callback)

    def delete_all(self, delete_callback=None) -> Dict[str, Tuple[int, int]]:
        """删除所有已扫描的垃圾文件"""
        results = {}
        for cat_name in list(self.categories.keys()):
            if self._stop_flag:
                break
            success, failed = self.delete_category(cat_name, delete_callback)
            results[cat_name] = (success, failed)
        return results


if __name__ == '__main__':
    # 测试模式
    cleaner = WindowsCleaner()
    print(f"系统盘: {cleaner.drive}")
    print(f"用户目录: {cleaner.user_profile}")
    print(f"管理员权限: {is_admin()}")
    print("\n开始扫描...")
    categories = cleaner.scan_all()
    print(f"\n扫描完成! 共发现 {len(categories)} 类垃圾文件")
    for cat_name, cat in categories.items():
        print(f"  {cat_name}: {format_size(cat.total_size)} ({len(cat.items)} 个文件)")
    print(f"\n总计可清理: {format_size(cleaner.total_size)}")
