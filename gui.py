"""
C盘清理大师 - 图形界面
基于 tkinter 的专业 Windows 系统垃圾清理 GUI
功能对标：Dism++、CCleaner、火绒垃圾清理
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, List, Optional
from datetime import datetime

from cleaner import (
    WindowsCleaner, CleanCategory, CleanItem,
    format_size, is_admin, run_as_admin
)


class CleanerGUI:
    """C盘清理大师图形界面 - 专业版"""

    # 主题颜色 - 现代清爽风格
    COLORS = {
        'bg': '#f5f5f5',
        'primary': '#2196F3',
        'primary_dark': '#1565C0',
        'primary_light': '#BBDEFB',
        'success': '#4CAF50',
        'warning': '#FF9800',
        'danger': '#f44336',
        'info': '#00BCD4',
        'text': '#212121',
        'text_light': '#757575',
        'white': '#ffffff',
        'border': '#e0e0e0',
        'card_bg': '#ffffff',
        'progress_bg': '#e0e0e0',
        'hover': '#e3f2fd',
        'selected': '#c8e6c9',
        'header_bg': '#1976D2',
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("C盘清理大师 - 专业版")
        self.root.geometry("1100x750")
        self.root.minsize(900, 650)
        self.root.configure(bg=self.COLORS['bg'])

        # 设置图标
        try:
            self.root.iconbitmap(default='')
        except Exception:
            pass

        self.cleaner = WindowsCleaner()
        self.categories: Dict[str, CleanCategory] = {}
        self.check_vars: Dict[str, Dict[str, tk.BooleanVar]] = {}
        self.is_scanning = False
        self.is_cleaning = False
        self.scan_thread = None
        self.clean_thread = None

        self._setup_styles()
        self._build_ui()
        self._center_window()

        # 检查管理员权限
        if not is_admin():
            self._show_admin_warning()

    def _show_admin_warning(self):
        """显示管理员权限提示"""
        warn_frame = tk.Frame(self.root, bg=self.COLORS['warning'], height=36)
        warn_frame.pack(fill=tk.X, side=tk.TOP)
        warn_frame.pack_propagate(False)

        lbl = tk.Label(
            warn_frame,
            text="⚠️ 建议以管理员身份运行以获得最佳清理效果  [点击以管理员身份重启]",
            bg=self.COLORS['warning'], fg=self.COLORS['white'],
            font=('Microsoft YaHei', 10), cursor='hand2'
        )
        lbl.pack(expand=True, fill=tk.BOTH)
        lbl.bind('<Button-1>', lambda e: run_as_admin())

    def _setup_styles(self):
        """配置 ttk 样式"""
        style = ttk.Style()
        style.theme_use('clam')

        # 自定义样式
        style.configure('Title.TLabel',
                        font=('Microsoft YaHei', 16, 'bold'),
                        foreground=self.COLORS['text'],
                        background=self.COLORS['card_bg'])

        style.configure('Header.TLabel',
                        font=('Microsoft YaHei', 12, 'bold'),
                        foreground=self.COLORS['text'])

        style.configure('Status.TLabel',
                        font=('Microsoft YaHei', 9),
                        foreground=self.COLORS['text_light'])

        style.configure('Size.TLabel',
                        font=('Microsoft YaHei', 9),
                        foreground=self.COLORS['primary'])

        style.configure('Primary.TButton',
                        font=('Microsoft YaHei', 10, 'bold'),
                        padding=(15, 8))

        style.configure('Success.TButton',
                        font=('Microsoft YaHei', 10, 'bold'),
                        padding=(15, 8))

        style.configure('Danger.TButton',
                        font=('Microsoft YaHei', 10, 'bold'),
                        padding=(15, 8))

        style.configure('Card.TFrame',
                        background=self.COLORS['card_bg'],
                        relief='solid',
                        borderwidth=1)

        style.configure('Progressbar.Horizontal',
                        background=self.COLORS['primary'],
                        troughcolor=self.COLORS['progress_bg'])

        style.configure('Treeview',
                        font=('Microsoft YaHei', 9),
                        rowheight=28,
                        background=self.COLORS['white'],
                        fieldbackground=self.COLORS['white'])

        style.configure('Treeview.Heading',
                        font=('Microsoft YaHei', 9, 'bold'),
                        background=self.COLORS['primary'],
                        foreground=self.COLORS['white'])

        style.map('Treeview',
                  background=[('selected', self.COLORS['primary_light']),
                              ('hover', self.COLORS['hover'])],
                  foreground=[('selected', self.COLORS['text'])])

    def _center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f'+{x}+{y}')

    def _build_ui(self):
        """构建主界面"""
        # 主容器
        main_container = tk.Frame(self.root, bg=self.COLORS['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ========== 顶部标题栏 ==========
        header_frame = tk.Frame(main_container, bg=self.COLORS['card_bg'],
                                relief='solid', borderwidth=1)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_frame = tk.Frame(header_frame, bg=self.COLORS['card_bg'])
        title_frame.pack(fill=tk.X, padx=20, pady=15)

        # 标题和图标
        tk.Label(title_frame, text="🧹", font=('Segoe UI Emoji', 28),
                 bg=self.COLORS['card_bg']).pack(side=tk.LEFT, padx=(0, 10))

        text_frame = tk.Frame(title_frame, bg=self.COLORS['card_bg'])
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(text_frame, text="C盘清理大师",
                 font=('Microsoft YaHei', 20, 'bold'),
                 fg=self.COLORS['primary_dark'],
                 bg=self.COLORS['card_bg']).pack(anchor=tk.W)

        tk.Label(text_frame,
                 text="全面扫描 · 深度清理 · 释放磁盘空间",
                 font=('Microsoft YaHei', 9),
                 fg=self.COLORS['text_light'],
                 bg=self.COLORS['card_bg']).pack(anchor=tk.W)

        # 右侧统计信息
        stats_frame = tk.Frame(title_frame, bg=self.COLORS['card_bg'])
        stats_frame.pack(side=tk.RIGHT)

        self.stats_label = tk.Label(
            stats_frame,
            text="就绪 | 上次清理: 未执行",
            font=('Microsoft YaHei', 9),
            fg=self.COLORS['text_light'],
            bg=self.COLORS['card_bg']
        )
        self.stats_label.pack()

        # ========== 工具栏 ==========
        toolbar = tk.Frame(main_container, bg=self.COLORS['bg'])
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # 左侧按钮组
        btn_group = tk.Frame(toolbar, bg=self.COLORS['bg'])
        btn_group.pack(side=tk.LEFT)

        self.scan_btn = tk.Button(
            btn_group, text="🔍 开始扫描",
            font=('Microsoft YaHei', 10, 'bold'),
            bg=self.COLORS['primary'], fg=self.COLORS['white'],
            padx=20, pady=8, border=0, cursor='hand2',
            activebackground=self.COLORS['primary_dark'],
            activeforeground=self.COLORS['white'],
            command=self._start_scan
        )
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clean_btn = tk.Button(
            btn_group, text="🗑️ 清理选中项",
            font=('Microsoft YaHei', 10, 'bold'),
            bg=self.COLORS['success'], fg=self.COLORS['white'],
            padx=20, pady=8, border=0, cursor='hand2',
            activebackground='#388E3C',
            activeforeground=self.COLORS['white'],
            command=self._start_clean,
            state=tk.DISABLED
        )
        self.clean_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.select_all_btn = tk.Button(
            btn_group, text="☑️ 全选",
            font=('Microsoft YaHei', 9),
            bg=self.COLORS['white'], fg=self.COLORS['text'],
            padx=12, pady=6, border=1, cursor='hand2',
            relief='solid', bd=1,
            command=self._toggle_all
        )
        self.select_all_btn.pack(side=tk.LEFT, padx=(0, 8))

        # 右侧信息
        self.status_var = tk.StringVar(value="就绪，点击「开始扫描」分析 C 盘")
        status_label = tk.Label(
            toolbar, textvariable=self.status_var,
            font=('Microsoft YaHei', 9),
            fg=self.COLORS['text_light'], bg=self.COLORS['bg']
        )
        status_label.pack(side=tk.RIGHT, padx=(10, 0))

        # ========== 进度条 ==========
        progress_frame = tk.Frame(main_container, bg=self.COLORS['bg'])
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_bar = ttk.Progressbar(
            progress_frame, mode='determinate',
            length=200
        )
        self.progress_bar.pack(fill=tk.X, expand=True)

        self.progress_label = tk.Label(
            progress_frame, text="",
            font=('Microsoft YaHei', 8),
            fg=self.COLORS['text_light'], bg=self.COLORS['bg']
        )
        self.progress_label.pack()

        # ========== 主内容区 ==========
        content_frame = tk.Frame(main_container, bg=self.COLORS['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧：分类列表
        left_frame = tk.Frame(content_frame, bg=self.COLORS['card_bg'],
                              relief='solid', borderwidth=1, width=280)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_frame.pack_propagate(False)

        tk.Label(left_frame, text="📋 清理项目",
                 font=('Microsoft YaHei', 11, 'bold'),
                 fg=self.COLORS['text'],
                 bg=self.COLORS['card_bg']).pack(anchor=tk.W, padx=12, pady=(12, 8))

        # 分类列表容器（带滚动）
        list_container = tk.Frame(left_frame, bg=self.COLORS['card_bg'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.canvas = tk.Canvas(list_container, bg=self.COLORS['card_bg'],
                                highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL,
                                 command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.COLORS['card_bg'])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮支持
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 右侧：详情区域
        right_frame = tk.Frame(content_frame, bg=self.COLORS['card_bg'],
                               relief='solid', borderwidth=1)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 详情标题
        detail_header = tk.Frame(right_frame, bg=self.COLORS['card_bg'])
        detail_header.pack(fill=tk.X, padx=12, pady=(12, 8))

        tk.Label(detail_header, text="📄 文件详情",
                 font=('Microsoft YaHei', 11, 'bold'),
                 fg=self.COLORS['text'],
                 bg=self.COLORS['card_bg']).pack(side=tk.LEFT)

        self.detail_count_label = tk.Label(
            detail_header, text="",
            font=('Microsoft YaHei', 9),
            fg=self.COLORS['text_light'], bg=self.COLORS['card_bg']
        )
        self.detail_count_label.pack(side=tk.RIGHT)

        # 详情列表（Treeview）
        tree_frame = tk.Frame(right_frame, bg=self.COLORS['card_bg'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        columns = ('path', 'size', 'desc')
        self.tree = ttk.Treeview(tree_frame, columns=columns,
                                 show='headings', height=12)

        self.tree.heading('path', text='文件路径')
        self.tree.heading('size', text='大小')
        self.tree.heading('desc', text='描述')

        self.tree.column('path', width=350, minwidth=200)
        self.tree.column('size', width=100, minwidth=80, anchor=tk.E)
        self.tree.column('desc', width=200, minwidth=120)

        # 滚动条
        tree_scrollbar = tk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                      command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ========== 底部状态栏 ==========
        bottom_frame = tk.Frame(main_container, bg=self.COLORS['card_bg'],
                                relief='solid', borderwidth=1, height=40)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        bottom_frame.pack_propagate(False)

        self.bottom_status = tk.Label(
            bottom_frame,
            text="💡 提示: 扫描前请关闭正在运行的程序以获得更准确的清理结果",
            font=('Microsoft YaHei', 9),
            fg=self.COLORS['text_light'], bg=self.COLORS['card_bg'],
            anchor=tk.W
        )
        self.bottom_status.pack(fill=tk.X, padx=15, pady=8)

    def _update_progress(self, current: int, total: int, message: str = ""):
        """更新进度显示"""
        if total > 0:
            pct = int(current / total * 100)
            self.progress_bar['value'] = pct
            self.progress_label.config(text=f"{message} ({current}/{total})")
        else:
            self.progress_label.config(text=message)
            self.progress_bar['value'] = 0
            self.progress_bar.start(10)

        self.root.update_idletasks()

    def _start_scan(self):
        """开始扫描"""
        if self.is_scanning:
            self.cleaner.stop()
            return

        # 清空旧数据
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.check_vars = {}
        self.categories = {}
        self.tree.delete(*self.tree.get_children())
        self.clean_btn.config(state=tk.DISABLED)
        self.detail_count_label.config(text="")

        self.is_scanning = True
        self.scan_btn.config(text="⏹ 停止扫描", bg=self.COLORS['danger'])
        self.status_var.set("正在扫描 C 盘，请稍候...")
        self.bottom_status.config(text="⏳ 正在扫描系统各分区...")
        self.progress_bar['value'] = 0

        def scan_thread():
            try:
                self.cleaner.scan_all(progress_callback=self._update_progress)
                self.root.after(0, self._on_scan_complete)
            except Exception as e:
                self.root.after(0, lambda: self._on_scan_error(str(e)))

        self.scan_thread = threading.Thread(target=scan_thread, daemon=True)
        self.scan_thread.start()

    def _on_scan_complete(self):
        """扫描完成回调"""
        self.is_scanning = False
        self.scan_btn.config(text="🔍 重新扫描", bg=self.COLORS['primary'])
        self.progress_bar.stop()
        self.progress_bar['value'] = 100

        self.categories = self.cleaner.categories
        if not self.categories:
            self.status_var.set("扫描完成，未发现可清理的垃圾文件 ✅")
            self.bottom_status.config(text="✅ 系统很干净，无需清理")
            return

        # 显示分类列表
        self._display_categories()

        # 统计
        total_items = sum(len(cat.items) for cat in self.categories.values())
        total_size = sum(cat.total_size for cat in self.categories.values())

        self.status_var.set(
            f"扫描完成！发现 {total_items} 项垃圾文件，共 {format_size(total_size)}"
        )
        self.bottom_status.config(
            text=f"✅ 扫描完成 | 共 {len(self.categories)} 个分类，"
                 f"{total_items} 个文件，可释放 {format_size(total_size)}"
        )
        self.clean_btn.config(state=tk.NORMAL)

    def _on_scan_error(self, error: str):
        """扫描错误回调"""
        self.is_scanning = False
        self.scan_btn.config(text="🔍 重新扫描", bg=self.COLORS['primary'])
        self.progress_bar.stop()
        self.status_var.set(f"扫描出错: {error}")
        self.bottom_status.config(text=f"❌ 扫描出错: {error}")

    def _display_categories(self):
        """显示分类列表"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        row = 0
        for cat_name, category in self.categories.items():
            if not category.items:
                continue

            # 分类卡片
            card = tk.Frame(self.scrollable_frame, bg=self.COLORS['white'],
                            relief='solid', borderwidth=1)
            card.pack(fill=tk.X, padx=4, pady=3)

            # 复选框 + 分类名 + 大小
            var = tk.BooleanVar(value=True)
            if cat_name not in self.check_vars:
                self.check_vars[cat_name] = {}

            cb = tk.Checkbutton(
                card, text=f"  {category.name}",
                variable=var,
                font=('Microsoft YaHei', 10),
                fg=self.COLORS['text'],
                bg=self.COLORS['white'],
                activebackground=self.COLORS['white'],
                selectcolor=self.COLORS['white'],
                command=lambda cn=cat_name: self._on_category_toggle(cn)
            )
            cb.pack(side=tk.LEFT, padx=(8, 0), pady=6)

            # 大小标签
            size_label = tk.Label(
                card,
                text=f"{format_size(category.total_size)}",
                font=('Microsoft YaHei', 9, 'bold'),
                fg=self.COLORS['primary'],
                bg=self.COLORS['white']
            )
            size_label.pack(side=tk.RIGHT, padx=(0, 12), pady=6)

            # 文件数量
            count_label = tk.Label(
                card,
                text=f"{len(category.items)} 项",
                font=('Microsoft YaHei', 8),
                fg=self.COLORS['text_light'],
                bg=self.COLORS['white']
            )
            count_label.pack(side=tk.RIGHT, padx=(0, 5), pady=6)

            # 点击卡片显示详情
            for item in category.items:
                self.check_vars[cat_name][item.path] = var

            card.bind('<Button-1>', lambda e, cn=cat_name: self._show_category_detail(cn))
            cb.bind('<Button-1>', lambda e, cn=cat_name: self._show_category_detail(cn))

            row += 1

    def _show_category_detail(self, cat_name: str):
        """显示分类详情"""
        self.tree.delete(*self.tree.get_children())
        category = self.categories.get(cat_name)
        if not category:
            return

        for item in category.items:
            self.tree.insert('', tk.END, values=(
                item.path,
                format_size(item.size),
                item.description
            ))

        self.detail_count_label.config(
            text=f"{len(category.items)} 项 | {format_size(category.total_size)}"
        )

    def _on_category_toggle(self, cat_name: str):
        """分类复选框切换"""
        pass  # 由 check_vars 自动管理

    def _toggle_all(self):
        """全选/取消全选"""
        all_selected = all(
            var.get()
            for cat_vars in self.check_vars.values()
            for var in cat_vars.values()
        )

        new_state = not all_selected
        for cat_vars in self.check_vars.values():
            for var in cat_vars.values():
                var.set(new_state)

        self.select_all_btn.config(
            text="☑️ 取消全选" if new_state else "☑️ 全选"
        )

    def _start_clean(self):
        """开始清理"""
        if self.is_cleaning:
            self.cleaner.stop()
            return

        # 收集选中的项目
        items_to_clean = []
        for cat_name, cat_vars in self.check_vars.items():
            category = self.categories.get(cat_name)
            if not category:
                continue
            for item in category.items:
                if cat_vars.get(item.path, tk.BooleanVar()).get():
                    items_to_clean.append(item)

        if not items_to_clean:
            messagebox.showinfo("提示", "请先选择要清理的项目")
            return

        total_size = sum(item.size for item in items_to_clean)

        # 确认对话框
        result = messagebox.askyesno(
            "确认清理",
            f"确定要清理 {len(items_to_clean)} 项文件吗？\n"
            f"预计释放空间: {format_size(total_size)}\n\n"
            f"⚠️ 清理后文件将无法恢复！"
        )
        if not result:
            return

        self.is_cleaning = True
        self.clean_btn.config(text="⏹ 停止清理", bg=self.COLORS['danger'])
        self.scan_btn.config(state=tk.DISABLED)
        self.status_var.set(f"正在清理 {len(items_to_clean)} 项文件...")
        self.progress_bar['value'] = 0

        def clean_thread():
            try:
                success, failed = self.cleaner.clean_items(
                    items_to_clean,
                    callback=lambda c, t, m: self.root.after(
                        0, lambda: self._update_progress(c, t, m)
                    )
                )
                self.root.after(0, lambda: self._on_clean_complete(
                    success, failed, len(items_to_clean)
                ))
            except Exception as e:
                self.root.after(0, lambda: self._on_clean_error(str(e)))

        self.clean_thread = threading.Thread(target=clean_thread, daemon=True)
        self.clean_thread.start()

    def _on_clean_complete(self, success: int, failed: int, total: int):
        """清理完成回调"""
        self.is_cleaning = False
        self.clean_btn.config(text="🗑️ 清理选中项", bg=self.COLORS['success'])
        self.scan_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 100

        freed_size = sum(
            item.size for cat in self.categories.values()
            for item in cat.items
        )

        self.status_var.set(
            f"清理完成！成功: {success}, 失败: {failed}"
        )
        self.bottom_status.config(
            text=f"✅ 清理完成 | 成功清理 {success}/{total} 项"
        )

        # 更新统计
        self.stats_label.config(
            text=f"上次清理: {datetime.now().strftime('%H:%M:%S')}"
        )

        if failed > 0:
            messagebox.showwarning(
                "清理结果",
                f"清理完成\n\n"
                f"✅ 成功: {success} 项\n"
                f"❌ 失败: {failed} 项\n\n"
                f"部分文件可能正在使用中，请关闭相关程序后重试"
            )
        else:
            messagebox.showinfo(
                "清理完成",
                f"✅ 成功清理 {success} 项垃圾文件！\n"
                f"💾 释放了宝贵的磁盘空间"
            )

        # 重新扫描
        self._start_scan()

    def _on_clean_error(self, error: str):
        """清理错误回调"""
        self.is_cleaning = False
        self.clean_btn.config(text="🗑️ 清理选中项", bg=self.COLORS['success'])
        self.scan_btn.config(state=tk.NORMAL)
        self.progress_bar.stop()
        self.status_var.set(f"清理出错: {error}")
        self.bottom_status.config(text=f"❌ 清理出错: {error}")

    def run(self):
        """运行主循环"""
        self.root.mainloop()


def main():
    """启动入口"""
    app = CleanerGUI()
    app.run()


if __name__ == '__main__':
    main()
