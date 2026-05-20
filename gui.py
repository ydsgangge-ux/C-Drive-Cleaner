"""
C盘清理工具 - 图形界面
基于 tkinter 的 Windows 系统垃圾清理 GUI
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, List

from cleaner import WindowsCleaner, CleanCategory, CleanItem, format_size, is_admin


class CleanerGUI:
    """C盘清理工具图形界面"""

    # 主题颜色
    COLORS = {
        'bg': '#f0f0f0',
        'primary': '#2196F3',
        'primary_dark': '#1976D2',
        'success': '#4CAF50',
        'warning': '#FF9800',
        'danger': '#f44336',
        'text': '#333333',
        'text_light': '#666666',
        'white': '#ffffff',
        'border': '#e0e0e0',
        'card_bg': '#ffffff',
        'progress_bg': '#e0e0e0',
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("C盘清理工具 - Windows 系统垃圾清理")
        self.root.geometry("900x680")
        self.root.minsize(800, 600)
        self.root.configure(bg=self.COLORS['bg'])

        # 设置图标（如果有）
        try:
            self.root.iconbitmap(default='')
        except Exception:
            pass

        self.cleaner = WindowsCleaner()
        self.categories: Dict[str, CleanCategory] = {}
        self.check_vars: Dict[str, Dict[str, tk.BooleanVar]] = {}
        self.is_scanning = False
        self.is_cleaning = False

        self._setup_styles()
        self._build_ui()
        self._center_window()

        # 检查管理员权限
        if not is_admin():
            self.status_var.set("⚠️ 建议以管理员身份运行以获得更好的清理效果")

    def _setup_styles(self):
        """配置 ttk 样式"""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Title.TLabel',
                        font=('Microsoft YaHei', 16, 'bold'),
                        foreground=self.COLORS['text'],
                        background=self.COLORS['bg'])

        style.configure('Header.TLabel',
                        font=('Microsoft YaHei', 12, 'bold'),
                        foreground=self.COLORS['text'],
                        background=self.COLORS['bg'])

        style.configure('Normal.TLabel',
                        font=('Microsoft YaHei', 10),
                        foreground=self.COLORS['text'],
                        background=self.COLORS['bg'])

        style.configure('Light.TLabel',
                        font=('Microsoft YaHei', 9),
                        foreground=self.COLORS['text_light'],
                        background=self.COLORS['bg'])

        style.configure('Scan.TButton',
                        font=('Microsoft YaHei', 11, 'bold'),
                        padding=(20, 8))

        style.configure('Clean.TButton',
                        font=('Microsoft YaHei', 11, 'bold'),
                        padding=(20, 8))

        style.configure('Stop.TButton',
                        font=('Microsoft YaHei', 11, 'bold'),
                        padding=(20, 8))

        style.configure('Status.TLabel',
                        font=('Microsoft YaHei', 9),
                        foreground=self.COLORS['text_light'],
                        background=self.COLORS['bg'])

        style.configure('Category.TLabelframe',
                        font=('Microsoft YaHei', 10, 'bold'),
                        background=self.COLORS['card_bg'])

        style.configure('Category.TLabelframe.Label',
                        font=('Microsoft YaHei', 10, 'bold'),
                        foreground=self.COLORS['text'])

        style.configure('Progress.Horizontal.TProgressbar',
                        background=self.COLORS['primary'],
                        troughcolor=self.COLORS['progress_bg'])

    def _center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        """构建界面"""
        # 主容器
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # ===== 顶部标题栏 =====
        header_frame = tk.Frame(main_frame, bg=self.COLORS['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(
            header_frame,
            text="🧹 C盘清理工具",
            style='Title.TLabel'
        )
        title_label.pack(side=tk.LEFT)

        # 系统信息
        sys_info = f"系统盘: {self.cleaner.drive}  |  用户: {os.environ.get('USERNAME', 'Unknown')}"
        sys_label = ttk.Label(
            header_frame,
            text=sys_info,
            style='Light.TLabel'
        )
        sys_label.pack(side=tk.RIGHT, pady=5)

        # ===== 操作按钮栏 =====
        btn_frame = tk.Frame(main_frame, bg=self.COLORS['bg'])
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.scan_btn = tk.Button(
            btn_frame,
            text="🔍 开始扫描",
            font=('Microsoft YaHei', 11, 'bold'),
            bg=self.COLORS['primary'],
            fg=self.COLORS['white'],
            padx=25, pady=8,
            border=0,
            cursor='hand2',
            activebackground=self.COLORS['primary_dark'],
            activeforeground=self.COLORS['white'],
            command=self._start_scan
        )
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clean_btn = tk.Button(
            btn_frame,
            text="🗑️ 清理选中项",
            font=('Microsoft YaHei', 11, 'bold'),
            bg=self.COLORS['success'],
            fg=self.COLORS['white'],
            padx=25, pady=8,
            border=0,
            cursor='hand2',
            state=tk.DISABLED,
            activebackground='#388E3C',
            activeforeground=self.COLORS['white'],
            command=self._start_clean
        )
        self.clean_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹️ 停止",
            font=('Microsoft YaHei', 11, 'bold'),
            bg=self.COLORS['danger'],
            fg=self.COLORS['white'],
            padx=25, pady=8,
            border=0,
            cursor='hand2',
            state=tk.DISABLED,
            activebackground='#D32F2F',
            activeforeground=self.COLORS['white'],
            command=self._stop_operation
        )
        self.stop_btn.pack(side=tk.LEFT)

        # 全选/取消
        self.select_all_var = tk.BooleanVar(value=True)
        select_all_cb = tk.Checkbutton(
            btn_frame,
            text="全选",
            font=('Microsoft YaHei', 10),
            variable=self.select_all_var,
            bg=self.COLORS['bg'],
            fg=self.COLORS['text'],
            selectcolor=self.COLORS['white'],
            activebackground=self.COLORS['bg'],
            command=self._toggle_all
        )
        select_all_cb.pack(side=tk.RIGHT, padx=(10, 0))

        # ===== 进度条 =====
        progress_frame = tk.Frame(main_frame, bg=self.COLORS['bg'])
        progress_frame.pack(fill=tk.X, pady=(0, 5))

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            style='Progress.Horizontal.TProgressbar',
            length=200
        )
        self.progress_bar.pack(fill=tk.X, expand=True)

        self.progress_label = ttk.Label(
            progress_frame,
            text="就绪",
            style='Light.TLabel'
        )
        self.progress_label.pack(pady=(2, 0))

        # ===== 扫描结果区域（可滚动） =====
        result_frame = tk.Frame(main_frame, bg=self.COLORS['bg'])
        result_frame.pack(fill=tk.BOTH, expand=True)

        # 使用 Canvas + Scrollbar 实现滚动
        canvas = tk.Canvas(result_frame, bg=self.COLORS['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=self.COLORS['bg'])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ===== 底部状态栏 =====
        status_frame = tk.Frame(main_frame, bg=self.COLORS['bg'], height=30)
        status_frame.pack(fill=tk.X, pady=(8, 0))
        status_frame.pack_propagate(False)

        self.status_var = tk.StringVar(value="就绪 - 点击「开始扫描」分析C盘垃圾文件")
        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            style='Status.TLabel'
        )
        status_label.pack(side=tk.LEFT)

        self.size_var = tk.StringVar(value="总计: 0 B")
        size_label = ttk.Label(
            status_frame,
            textvariable=self.size_var,
            style='Status.TLabel'
        )
        size_label.pack(side=tk.RIGHT)

    def _toggle_all(self):
        """全选/取消全选"""
        select_all = self.select_all_var.get()
        for cat_name, items_dict in self.check_vars.items():
            for item_key, var in items_dict.items():
                var.set(select_all)

    def _clear_results(self):
        """清空扫描结果"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.check_vars = {}
        self.categories = {}
        self.size_var.set("总计: 0 B")

    def _display_results(self):
        """显示扫描结果"""
        self._clear_results()

        if not self.categories:
            no_data_label = ttk.Label(
                self.scrollable_frame,
                text="未发现可清理的垃圾文件",
                style='Header.TLabel'
            )
            no_data_label.pack(pady=50)
            return

        for cat_name, cat in self.categories.items():
            self._add_category_card(cat_name, cat)

        # 更新总计
        total = sum(cat.total_size for cat in self.categories.values())
        self.size_var.set(f"总计: {format_size(total)}")

    def _add_category_card(self, cat_name: str, cat: CleanCategory):
        """添加分类卡片"""
        # 卡片容器
        card = tk.Frame(
            self.scrollable_frame,
            bg=self.COLORS['card_bg'],
            highlightbackground=self.COLORS['border'],
            highlightthickness=1,
            padx=12, pady=8
        )
        card.pack(fill=tk.X, pady=(0, 6))

        # 分类标题行
        title_frame = tk.Frame(card, bg=self.COLORS['card_bg'])
        title_frame.pack(fill=tk.X)

        # 分类图标和名称
        cat_icons = {
            'Windows临时文件': '📁',
            '用户临时文件': '📂',
            '浏览器缓存': '🌐',
            '预读取文件': '⚡',
            '最近文档': '📄',
            '下载残留': '⬇️',
            '回收站': '🗑️',
            '.NET缓存': '🔧',
        }
        icon = cat_icons.get(cat_name, '📦')

        # 分类勾选框
        cat_var = tk.BooleanVar(value=True)
        cat_cb = tk.Checkbutton(
            title_frame,
            text=f"{icon} {cat_name}",
            font=('Microsoft YaHei', 11, 'bold'),
            variable=cat_var,
            bg=self.COLORS['card_bg'],
            fg=self.COLORS['text'],
            selectcolor=self.COLORS['white'],
            activebackground=self.COLORS['card_bg'],
            command=lambda cn=cat_name, cv=cat_var: self._toggle_category(cn, cv)
        )
        cat_cb.pack(side=tk.LEFT)

        # 大小和文件数
        info_label = tk.Label(
            title_frame,
            text=f"{format_size(cat.total_size)}  ({len(cat.items)} 个文件)",
            font=('Microsoft YaHei', 10),
            bg=self.COLORS['card_bg'],
            fg=self.COLORS['text_light']
        )
        info_label.pack(side=tk.RIGHT)

        # 文件列表（可展开）
        if len(cat.items) <= 10:
            # 直接显示
            for item in cat.items[:10]:
                self._add_item_row(card, cat_name, item)
        else:
            # 显示前10个 + "更多"按钮
            for item in cat.items[:10]:
                self._add_item_row(card, cat_name, item)

            more_label = tk.Label(
                card,
                text=f"... 还有 {len(cat.items) - 10} 个文件",
                font=('Microsoft YaHei', 9, 'italic'),
                bg=self.COLORS['card_bg'],
                fg=self.COLORS['text_light'],
                cursor='hand2'
            )
            more_label.pack(anchor=tk.W, padx=(35, 0), pady=(2, 0))

        # 存储分类变量
        if cat_name not in self.check_vars:
            self.check_vars[cat_name] = {}

    def _add_item_row(self, parent, cat_name: str, item: CleanItem):
        """添加文件行"""
        row = tk.Frame(parent, bg=self.COLORS['card_bg'])
        row.pack(fill=tk.X, padx=(20, 0), pady=(1, 0))

        # 文件勾选框
        item_key = f"{cat_name}::{item.path}"
        var = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(
            row,
            text="",
            variable=var,
            bg=self.COLORS['card_bg'],
            selectcolor=self.COLORS['white'],
            activebackground=self.COLORS['card_bg']
        )
        cb.pack(side=tk.LEFT)

        # 存储变量
        if cat_name not in self.check_vars:
            self.check_vars[cat_name] = {}
        self.check_vars[cat_name][item_key] = var

        # 文件名
        fname = os.path.basename(item.path) or item.path
        name_label = tk.Label(
            row,
            text=fname,
            font=('Microsoft YaHei', 9),
            bg=self.COLORS['card_bg'],
            fg=self.COLORS['text'],
            anchor=tk.W
        )
        name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 文件大小
        size_label = tk.Label(
            row,
            text=format_size(item.size),
            font=('Microsoft YaHei', 9),
            bg=self.COLORS['card_bg'],
            fg=self.COLORS['text_light'],
            width=10,
            anchor=tk.E
        )
        size_label.pack(side=tk.RIGHT)

    def _toggle_category(self, cat_name: str, cat_var: tk.BooleanVar):
        """切换分类下所有文件的选择状态"""
        if cat_name in self.check_vars:
            for var in self.check_vars[cat_name].values():
                var.set(cat_var.get())

    def _get_selected_items(self) -> List[CleanItem]:
        """获取用户选中的清理项"""
        selected = []
        for cat_name, items_dict in self.check_vars.items():
            if cat_name in self.categories:
                cat = self.categories[cat_name]
                for item in cat.items:
                    item_key = f"{cat_name}::{item.path}"
                    if item_key in items_dict and items_dict[item_key].get():
                        selected.append(item)
        return selected

    def _start_scan(self):
        """开始扫描（后台线程）"""
        if self.is_scanning:
            return

        self.is_scanning = True
        self.scan_btn.config(state=tk.DISABLED)
        self.clean_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="正在扫描...")
        self.status_var.set("🔍 正在扫描C盘垃圾文件，请稍候...")
        self._clear_results()

        def scan_thread():
            try:
                categories = self.cleaner.scan_all(progress_callback=self._update_scan_progress)
                self.root.after(0, self._on_scan_complete, categories)
            except Exception as e:
                self.root.after(0, self._on_scan_error, str(e))

        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()

    def _update_scan_progress(self, current: int, total: int, cat_name: str):
        """更新扫描进度"""
        def update():
            pct = int((current / total) * 100)
            self.progress_bar['value'] = pct
            self.progress_label.config(text=f"正在扫描: {cat_name} ({current}/{total})")
        self.root.after(0, update)

    def _on_scan_complete(self, categories: Dict[str, CleanCategory]):
        """扫描完成回调"""
        self.categories = categories
        self.is_scanning = False
        self.scan_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 100
        self.progress_label.config(text="扫描完成")

        total_size = sum(cat.total_size for cat in categories.values())
        total_files = sum(len(cat.items) for cat in categories.values())

        if total_size > 0:
            self.status_var.set(
                f"✅ 扫描完成！发现 {total_files} 个垃圾文件，可释放 {format_size(total_size)}"
            )
            self.clean_btn.config(state=tk.NORMAL)
        else:
            self.status_var.set("✅ 扫描完成！未发现可清理的垃圾文件")
            self.clean_btn.config(state=tk.DISABLED)

        self._display_results()

    def _on_scan_error(self, error_msg: str):
        """扫描出错回调"""
        self.is_scanning = False
        self.scan_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="扫描失败")
        self.status_var.set(f"❌ 扫描出错: {error_msg}")
        messagebox.showerror("扫描错误", f"扫描过程中出现错误:\n{error_msg}")

    def _start_clean(self):
        """开始清理（后台线程）"""
        if self.is_cleaning:
            return

        selected = self._get_selected_items()
        if not selected:
            messagebox.showinfo("提示", "请先选择要清理的文件")
            return

        total_size = sum(item.size for item in selected)
        result = messagebox.askyesno(
            "确认清理",
            f"确定要清理 {len(selected)} 个文件吗？\n"
            f"预计可释放空间: {format_size(total_size)}\n\n"
            f"⚠️ 清理后文件将被永久删除！"
        )
        if not result:
            return

        self.is_cleaning = True
        self.scan_btn.config(state=tk.DISABLED)
        self.clean_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="正在清理...")
        self.status_var.set("🗑️ 正在清理垃圾文件...")

        def clean_thread():
            try:
                success, failed = self.cleaner.delete_items(
                    selected,
                    delete_callback=self._update_clean_progress
                )
                self.root.after(0, self._on_clean_complete, success, failed)
            except Exception as e:
                self.root.after(0, self._on_clean_error, str(e))

        thread = threading.Thread(target=clean_thread, daemon=True)
        thread.start()

    def _update_clean_progress(self, current: int, total: int, description: str):
        """更新清理进度"""
        def update():
            pct = int((current / total) * 100)
            self.progress_bar['value'] = pct
            self.progress_label.config(text=f"正在清理: {current}/{total}")
            self.status_var.set(f"🗑️ 正在清理: {description}")
        self.root.after(0, update)

    def _on_clean_complete(self, success: int, failed: int):
        """清理完成回调"""
        self.is_cleaning = False
        self.scan_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 100
        self.progress_label.config(text="清理完成")

        if failed > 0:
            self.status_var.set(
                f"✅ 清理完成！成功清理 {success} 个文件，{failed} 个文件清理失败（可能正在使用）"
            )
            messagebox.showwarning(
                "清理结果",
                f"成功清理: {success} 个文件\n"
                f"清理失败: {failed} 个文件（可能正在被系统使用）\n\n"
                f"💡 提示：重启电脑后再次清理可能解决"
            )
        else:
            self.status_var.set(f"✅ 清理完成！成功清理 {success} 个文件")
            messagebox.showinfo(
                "清理完成",
                f"成功清理 {success} 个垃圾文件！\n"
                f"💡 建议定期清理以保持系统流畅"
            )

        self.clean_btn.config(state=tk.DISABLED)
        # 重新扫描以更新状态
        self._start_scan()

    def _on_clean_error(self, error_msg: str):
        """清理出错回调"""
        self.is_cleaning = False
        self.scan_btn.config(state=tk.NORMAL)
        self.clean_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="清理失败")
        self.status_var.set(f"❌ 清理出错: {error_msg}")
        messagebox.showerror("清理错误", f"清理过程中出现错误:\n{error_msg}")

    def _stop_operation(self):
        """停止当前操作"""
        self.cleaner.stop()
        self.status_var.set("⏹️ 正在停止...")
        self.stop_btn.config(state=tk.DISABLED)

    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """入口函数"""
    app = CleanerGUI()
    app.run()


if __name__ == '__main__':
    main()
