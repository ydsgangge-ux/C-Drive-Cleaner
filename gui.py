"""
C盘清理大师 - 图形界面
基于 tkinter 的风险分级清理界面：safe 默认勾选、caution 手动勾选、
danger 禁用并拦截，删除前按风险汇总确认。
"""

import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from cleaner import (
    WindowsCleaner, CleanCategory, CleanItem,
    RISK_CAUTION, RISK_DANGER, RISK_LABELS, RISK_ORDER, RISK_SAFE,
    format_size, format_delete_summary, group_items_by_risk,
    is_admin, run_as_admin, summarize_risk,
)


class CleanerGUI:
    """C盘清理大师图形界面 - 风险分级版"""

    FONT_FAMILY = "Microsoft YaHei UI"

    COLORS = {
        'bg': '#EEF2F7',
        'card_bg': '#FFFFFF',
        'text': '#0F172A',
        'muted': '#64748B',
        'border': '#DBE3EC',
        'primary': '#2563EB',
        'primary_dark': '#1D4ED8',
        'primary_soft': '#DBEAFE',
        'safe': '#16A34A',
        'safe_soft': '#DCFCE7',
        'caution': '#EA580C',
        'caution_soft': '#FFEDD5',
        'danger': '#DC2626',
        'danger_soft': '#FEE2E2',
        'white': '#FFFFFF',
        'hover': '#F8FAFC',
        'disabled': '#94A3B8',
    }

    RISK_COLORS = {
        RISK_SAFE: COLORS['safe'],
        RISK_CAUTION: COLORS['caution'],
        RISK_DANGER: COLORS['danger'],
    }

    RISK_SOFT = {
        RISK_SAFE: COLORS['safe_soft'],
        RISK_CAUTION: COLORS['caution_soft'],
        RISK_DANGER: COLORS['danger_soft'],
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("C盘清理大师 - 风险分级版")
        self.root.geometry("1180x800")
        self.root.minsize(980, 680)
        self.root.configure(bg=self.COLORS['bg'])

        try:
            self.root.iconbitmap(default='')
        except Exception:
            pass

        self.cleaner = WindowsCleaner()
        self.categories: Dict[str, CleanCategory] = {}

        # 选择状态：bucket_key -> BooleanVar / 条目列表 / (risk, 分类名)
        self.bucket_vars: Dict[str, tk.BooleanVar] = {}
        self.bucket_items: Dict[str, List[CleanItem]] = {}
        self.bucket_meta: Dict[str, Tuple[str, str]] = {}
        self.bucket_frames: Dict[str, tk.Frame] = {}
        self.group_vars: Dict[str, tk.BooleanVar] = {}
        self.risk_chip_labels: Dict[str, tk.Label] = {}
        self.selected_bucket: Optional[str] = None
        self.tree_item_map: Dict[str, CleanItem] = {}
        self.bucket_card_labels: Dict[str, Tuple[tk.Label, tk.Label]] = {}
        self._ctx_item: Optional[CleanItem] = None

        self.is_scanning = False
        self.is_cleaning = False
        self.scan_thread = None
        self.clean_thread = None

        self._setup_styles()
        self._build_ui()
        self._center_window()

        if not is_admin():
            self._show_admin_warning()

    # ============================================================
    # 基础 UI
    # ============================================================
    def _show_admin_warning(self):
        """显示管理员权限提示"""
        warn_frame = tk.Frame(self.root, bg=self.COLORS['caution'], height=34)
        warn_frame.pack(fill=tk.X, side=tk.TOP)
        warn_frame.pack_propagate(False)

        lbl = tk.Label(
            warn_frame,
            text="⚠️ 建议以管理员身份运行以获得最佳清理效果  [点击以管理员身份重启]",
            bg=self.COLORS['caution'], fg=self.COLORS['white'],
            font=(self.FONT_FAMILY, 9, 'bold'), cursor='hand2'
        )
        lbl.pack(expand=True, fill=tk.BOTH)
        lbl.bind('<Button-1>', lambda e: run_as_admin())

    def _setup_styles(self):
        """配置 ttk 样式"""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        style.configure(
            'Modern.Horizontal.TProgressbar',
            background=self.COLORS['primary'],
            troughcolor='#E2E8F0',
            bordercolor='#E2E8F0',
            lightcolor=self.COLORS['primary'],
            darkcolor=self.COLORS['primary'],
            thickness=8,
        )
        style.configure(
            'Treeview',
            font=(self.FONT_FAMILY, 9),
            rowheight=30,
            background=self.COLORS['card_bg'],
            fieldbackground=self.COLORS['card_bg'],
            borderwidth=0,
        )
        style.configure(
            'Treeview.Heading',
            font=(self.FONT_FAMILY, 9, 'bold'),
            background=self.COLORS['primary_soft'],
            foreground=self.COLORS['primary_dark'],
            relief='flat',
            padding=(8, 7),
        )
        style.map(
            'Treeview',
            background=[('selected', self.COLORS['primary_soft'])],
            foreground=[('selected', self.COLORS['text'])],
        )
        style.configure('Vertical.TScrollbar', arrowsize=12)

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

    def _make_button(self, parent, text: str, bg: str, command,
                     fg: Optional[str] = None, state: str = tk.NORMAL,
                     hover: Optional[str] = None, outline: bool = False) -> tk.Button:
        """创建扁平风格按钮"""
        fg = fg or self.COLORS['white']
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg,
            activebackground=hover or bg,
            activeforeground=fg,
            font=(self.FONT_FAMILY, 10, 'bold'),
            padx=18, pady=8, bd=0, relief='flat', cursor='hand2',
            state=state, disabledforeground=self.COLORS['disabled'],
            highlightbackground=self.COLORS['border'],
            highlightthickness=1 if outline else 0,
        )

    def _build_ui(self):
        """构建主界面"""
        main = tk.Frame(self.root, bg=self.COLORS['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=18, pady=14)

        self._build_header(main)
        self._build_toolbar(main)
        self._build_progress(main)
        self._build_risk_chips(main)
        self._build_content(main)
        self._build_footer(main)

    def _build_header(self, parent):
        card = tk.Frame(
            parent, bg=self.COLORS['card_bg'],
            highlightbackground=self.COLORS['border'], highlightthickness=1
        )
        card.pack(fill=tk.X, pady=(0, 12))

        inner = tk.Frame(card, bg=self.COLORS['card_bg'])
        inner.pack(fill=tk.X, padx=22, pady=16)

        tk.Label(
            inner, text="🧹", font=('Segoe UI Emoji', 26),
            bg=self.COLORS['card_bg']
        ).pack(side=tk.LEFT, padx=(0, 14))

        text_frame = tk.Frame(inner, bg=self.COLORS['card_bg'])
        text_frame.pack(side=tk.LEFT)
        tk.Label(
            text_frame, text="C盘清理大师",
            font=(self.FONT_FAMILY, 19, 'bold'),
            fg=self.COLORS['primary_dark'], bg=self.COLORS['card_bg']
        ).pack(anchor=tk.W)
        tk.Label(
            text_frame, text="风险分级 · 精准清理 · 安全释放磁盘空间",
            font=(self.FONT_FAMILY, 9),
            fg=self.COLORS['muted'], bg=self.COLORS['card_bg']
        ).pack(anchor=tk.W)

        self.stats_label = tk.Label(
            inner, text="就绪 | 上次清理: 未执行",
            font=(self.FONT_FAMILY, 9),
            fg=self.COLORS['muted'], bg=self.COLORS['card_bg']
        )
        self.stats_label.pack(side=tk.RIGHT)

    def _build_toolbar(self, parent):
        toolbar = tk.Frame(parent, bg=self.COLORS['bg'])
        toolbar.pack(fill=tk.X, pady=(0, 10))

        self.scan_btn = self._make_button(
            toolbar, "🔍 开始扫描", self.COLORS['primary'],
            self._start_scan, hover=self.COLORS['primary_dark']
        )
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clean_btn = self._make_button(
            toolbar, "🗑 清理选中项", self.COLORS['safe'],
            self._start_clean, state=tk.DISABLED, hover='#15803D'
        )
        self.clean_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.reset_btn = self._make_button(
            toolbar, "↺ 恢复默认", self.COLORS['card_bg'],
            self._reset_selection, fg=self.COLORS['text'],
            hover=self.COLORS['hover'], outline=True
        )
        self.reset_btn.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="就绪，点击「开始扫描」分析 C 盘")
        tk.Label(
            toolbar, textvariable=self.status_var,
            font=(self.FONT_FAMILY, 9),
            fg=self.COLORS['muted'], bg=self.COLORS['bg']
        ).pack(side=tk.RIGHT, padx=(10, 0))

    def _build_progress(self, parent):
        wrap = tk.Frame(parent, bg=self.COLORS['bg'])
        wrap.pack(fill=tk.X, pady=(0, 6))

        self.progress_bar = ttk.Progressbar(
            wrap, mode='determinate', maximum=100,
            style='Modern.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = tk.Label(
            wrap, text="", font=(self.FONT_FAMILY, 8),
            fg=self.COLORS['muted'], bg=self.COLORS['bg']
        )
        self.progress_label.pack(anchor=tk.W, pady=(4, 0))

    def _build_risk_chips(self, parent):
        bar = tk.Frame(parent, bg=self.COLORS['bg'])
        bar.pack(fill=tk.X, pady=(0, 10))

        for risk in RISK_ORDER:
            chip = tk.Frame(
                bar, bg=self.RISK_SOFT[risk],
                highlightbackground=self.RISK_COLORS[risk], highlightthickness=1
            )
            chip.pack(side=tk.LEFT, padx=(0, 8))

            tk.Label(
                chip, text="●", font=(self.FONT_FAMILY, 9, 'bold'),
                fg=self.RISK_COLORS[risk], bg=self.RISK_SOFT[risk]
            ).pack(side=tk.LEFT, padx=(10, 4), pady=5)

            label = tk.Label(
                chip, text=f"{RISK_LABELS[risk]} 0 项 · 0 B",
                font=(self.FONT_FAMILY, 9),
                fg=self.COLORS['text'], bg=self.RISK_SOFT[risk]
            )
            label.pack(side=tk.LEFT, padx=(0, 10), pady=5)
            self.risk_chip_labels[risk] = label

        self.selection_label = tk.Label(
            bar, text="已选 0 项",
            font=(self.FONT_FAMILY, 9, 'bold'),
            fg=self.COLORS['muted'], bg=self.COLORS['bg']
        )
        self.selection_label.pack(side=tk.RIGHT)

    def _build_content(self, parent):
        content = tk.Frame(parent, bg=self.COLORS['bg'])
        content.pack(fill=tk.BOTH, expand=True)

        # ---------- 左侧：按风险分组的扫描结果 ----------
        left = tk.Frame(
            content, bg=self.COLORS['card_bg'], width=380,
            highlightbackground=self.COLORS['border'], highlightthickness=1
        )
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 12))
        left.pack_propagate(False)

        head = tk.Frame(left, bg=self.COLORS['card_bg'])
        head.pack(fill=tk.X, padx=16, pady=(14, 2))
        tk.Label(
            head, text="📋 扫描结果",
            font=(self.FONT_FAMILY, 12, 'bold'),
            fg=self.COLORS['text'], bg=self.COLORS['card_bg']
        ).pack(side=tk.LEFT)
        tk.Label(
            left, text="safe 默认勾选 · caution 需手动勾选 · danger 已禁用",
            font=(self.FONT_FAMILY, 8),
            fg=self.COLORS['muted'], bg=self.COLORS['card_bg']
        ).pack(anchor=tk.W, padx=16, pady=(0, 8))

        holder = tk.Frame(left, bg=self.COLORS['card_bg'])
        holder.pack(fill=tk.BOTH, expand=True, padx=(10, 4), pady=(0, 10))

        self.canvas = tk.Canvas(
            holder, bg=self.COLORS['card_bg'],
            highlightthickness=0, bd=0
        )
        scrollbar = ttk.Scrollbar(holder, orient=tk.VERTICAL, command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg=self.COLORS['card_bg'])
        self._canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor='nw'
        )
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._canvas_window, width=e.width)
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._bind_mousewheel(self.canvas, self.canvas)

        self._show_empty_hint("点击「开始扫描」后，结果会按风险等级分组显示在这里。")

        # ---------- 右侧：详情 ----------
        right = tk.Frame(
            content, bg=self.COLORS['card_bg'],
            highlightbackground=self.COLORS['border'], highlightthickness=1
        )
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        detail_head = tk.Frame(right, bg=self.COLORS['card_bg'])
        detail_head.pack(fill=tk.X, padx=16, pady=(14, 2))
        tk.Label(
            detail_head, text="📄 文件详情",
            font=(self.FONT_FAMILY, 12, 'bold'),
            fg=self.COLORS['text'], bg=self.COLORS['card_bg']
        ).pack(side=tk.LEFT)
        self.detail_count_label = tk.Label(
            detail_head, text="",
            font=(self.FONT_FAMILY, 9, 'bold'),
            fg=self.COLORS['muted'], bg=self.COLORS['card_bg']
        )
        self.detail_count_label.pack(side=tk.RIGHT)

        self.detail_scope_label = tk.Label(
            right, text="点击左侧分类查看具体文件",
            font=(self.FONT_FAMILY, 8),
            fg=self.COLORS['muted'], bg=self.COLORS['card_bg']
        )
        self.detail_scope_label.pack(anchor=tk.W, padx=16, pady=(0, 8))

        tree_frame = tk.Frame(right, bg=self.COLORS['card_bg'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        columns = ('risk', 'path', 'size', 'desc')
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show='headings', selectmode='browse'
        )
        self.tree.heading('risk', text='风险')
        self.tree.heading('path', text='文件路径')
        self.tree.heading('size', text='大小')
        self.tree.heading('desc', text='描述')

        self.tree.column('risk', width=105, minwidth=95, anchor=tk.CENTER, stretch=False)
        self.tree.column('path', width=360, minwidth=180, anchor=tk.W)
        self.tree.column('size', width=95, minwidth=80, anchor=tk.E, stretch=False)
        self.tree.column('desc', width=200, minwidth=130, anchor=tk.W)

        self.tree.tag_configure(RISK_SAFE, background='#F0FDF4')
        self.tree.tag_configure(RISK_CAUTION, background='#FFF7ED')
        self.tree.tag_configure(RISK_DANGER, background='#FEF2F2')

        tree_scrollbar = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._bind_mousewheel(self.tree, self.tree)

        # 右键菜单：资源管理器定位 / 删除单条
        self.ctx_menu = tk.Menu(self.root, tearoff=False, font=(self.FONT_FAMILY, 9))
        self.ctx_menu.add_command(
            label="📁 在资源管理器中显示", command=self._ctx_reveal_in_explorer
        )
        self.ctx_menu.add_command(
            label="🗑 删除此项...", command=self._ctx_delete_single
        )
        self.tree.bind('<Button-3>', self._on_tree_context_menu)

    def _build_footer(self, parent):
        footer = tk.Frame(
            parent, bg=self.COLORS['card_bg'],
            highlightbackground=self.COLORS['border'], highlightthickness=1
        )
        footer.pack(fill=tk.X, pady=(12, 0))

        self.bottom_status = tk.Label(
            footer,
            text="💡 提示：可放心删除项默认勾选；谨慎删除项请逐项确认；不建议删除项已禁用。",
            font=(self.FONT_FAMILY, 9), anchor=tk.W,
            fg=self.COLORS['muted'], bg=self.COLORS['card_bg']
        )
        self.bottom_status.pack(fill=tk.X, padx=16, pady=9)

    def _bind_mousewheel(self, widget, target):
        """鼠标进入控件时接管滚轮"""
        def on_wheel(event):
            target.yview_scroll(int(-event.delta / 120), 'units')

        widget.bind('<Enter>', lambda e: widget.bind_all('<MouseWheel>', on_wheel))
        widget.bind('<Leave>', lambda e: widget.unbind_all('<MouseWheel>'))

    def _show_empty_hint(self, text: str):
        for child in self.scrollable_frame.winfo_children():
            child.destroy()
        tk.Label(
            self.scrollable_frame, text=text,
            font=(self.FONT_FAMILY, 9), fg=self.COLORS['muted'],
            bg=self.COLORS['card_bg'], justify=tk.LEFT, wraplength=330
        ).pack(anchor=tk.W, padx=12, pady=22)

    # ============================================================
    # 进度与扫描
    # ============================================================
    def _update_progress(self, current: int, total: int, message: str = ""):
        """更新进度显示（仅在主线程调用）"""
        if total > 0:
            self.progress_bar['value'] = int(current / total * 100)
            self.progress_label.config(text=f"{message} ({current}/{total})")
        else:
            self.progress_label.config(text=message)
            self.progress_bar['value'] = 0
            self.progress_bar.start(10)

    def _start_scan(self):
        """开始 / 停止扫描"""
        if self.is_scanning:
            self.cleaner.stop()
            return

        for child in self.scrollable_frame.winfo_children():
            child.destroy()
        self.bucket_vars = {}
        self.bucket_items = {}
        self.bucket_meta = {}
        self.bucket_frames = {}
        self.group_vars = {}
        self.selected_bucket = None
        self.categories = {}
        self.tree.delete(*self.tree.get_children())
        self.tree_item_map = {}
        self.bucket_card_labels = {}
        self.clean_btn.config(state=tk.DISABLED, text="🗑 清理选中项")
        self.reset_btn.config(state=tk.DISABLED)
        self.detail_count_label.config(text="")
        self.detail_scope_label.config(text="扫描中，请稍候...")
        self._update_risk_chips(summarize_risk([]))
        self.selection_label.config(text="已选 0 项")

        self.is_scanning = True
        self.scan_btn.config(
            text="⏹ 停止扫描", bg=self.COLORS['danger'],
            activebackground='#B91C1C'
        )
        self.status_var.set("正在扫描 C 盘，请稍候...")
        self.bottom_status.config(text="⏳ 正在扫描系统各分区，请保持窗口打开...")
        self.progress_bar['value'] = 0
        self.progress_label.config(text="准备扫描...")

        def worker():
            try:
                self.cleaner.scan_all(
                    progress_callback=lambda c, t, m: self.root.after(
                        0, self._update_progress, c, t, m
                    )
                )
                self.root.after(0, self._on_scan_complete)
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda msg=msg: self._on_scan_error(msg))

        self.scan_thread = threading.Thread(target=worker, daemon=True)
        self.scan_thread.start()

    def _on_scan_complete(self):
        """扫描完成回调"""
        self.is_scanning = False
        self.scan_btn.config(
            text="🔍 重新扫描", bg=self.COLORS['primary'],
            activebackground=self.COLORS['primary_dark']
        )
        self.progress_bar.stop()
        self.progress_bar['value'] = 100

        self.categories = self.cleaner.categories or {}
        all_items = [item for cat in self.categories.values() for item in cat.items]
        self._update_risk_chips(summarize_risk(all_items))

        if not all_items:
            self._show_empty_hint("扫描完成，未发现可清理的垃圾文件。")
            self.detail_scope_label.config(text="暂无数据")
            self.status_var.set("扫描完成，未发现可清理的垃圾文件 ✅")
            self.bottom_status.config(text="✅ 系统很干净，无需清理")
            self.selection_label.config(text="已选 0 项")
            return

        self._display_categories()
        self._update_selection_summary()

        total_size = sum(item.size for item in all_items)
        self.progress_label.config(text="扫描完成")
        self.status_var.set(
            f"扫描完成：{len(all_items)} 项，可释放 {format_size(total_size)}"
        )
        self.bottom_status.config(
            text=f"✅ 扫描完成：{len(self.categories)} 个分类，{len(all_items)} 项，"
                 f"其中可放心删除项已默认勾选"
        )

    def _on_scan_error(self, error: str):
        """扫描错误回调"""
        self.is_scanning = False
        self.scan_btn.config(
            text="🔍 重新扫描", bg=self.COLORS['primary'],
            activebackground=self.COLORS['primary_dark']
        )
        self.progress_bar.stop()
        self.status_var.set(f"扫描出错: {error}")
        self.bottom_status.config(text=f"❌ 扫描出错: {error}")
        self.detail_scope_label.config(text="扫描失败")

    # ============================================================
    # 风险分组展示
    # ============================================================
    def _display_categories(self):
        """按风险等级分组渲染扫描结果"""
        for child in self.scrollable_frame.winfo_children():
            child.destroy()

        groups = group_items_by_risk(self.categories)
        if not any(groups[risk] for risk in RISK_ORDER):
            self._show_empty_hint("扫描完成，未发现可清理的垃圾文件。")
            return

        for risk in RISK_ORDER:
            if groups[risk]:
                self._build_risk_section(risk, groups[risk])

        self._sync_group_vars()
        first_key = next(iter(self.bucket_items), None)
        if first_key:
            self._show_bucket_detail(first_key)

    def _build_risk_section(self, risk: str, buckets: Dict[str, List[CleanItem]]):
        """渲染一个风险分组"""
        color = self.RISK_COLORS[risk]
        soft = self.RISK_SOFT[risk]

        section = tk.Frame(
            self.scrollable_frame, bg=soft,
            highlightbackground=color, highlightthickness=1
        )
        section.pack(fill=tk.X, padx=2, pady=(2, 10))

        head = tk.Frame(section, bg=soft)
        head.pack(fill=tk.X, padx=10, pady=(9, 2))

        badge = tk.Label(
            head, text=f" {RISK_LABELS[risk]} ",
            font=(self.FONT_FAMILY, 9, 'bold'),
            bg=color, fg=self.COLORS['white'], padx=6, pady=2
        )
        badge.pack(side=tk.LEFT)

        risk_items = [item for items in buckets.values() for item in items]
        risk_size = sum(item.size for item in risk_items)
        meta = tk.Label(
            head, text=f"{len(risk_items)} 项 · {format_size(risk_size)}",
            font=(self.FONT_FAMILY, 8),
            fg=self.COLORS['muted'], bg=soft
        )
        meta.pack(side=tk.LEFT, padx=(8, 0))

        group_var = tk.BooleanVar(value=(risk == RISK_SAFE))
        if risk == RISK_DANGER:
            tk.Checkbutton(
                head, text="已禁用", variable=group_var, state=tk.DISABLED,
                bg=soft, activebackground=soft, selectcolor=self.COLORS['white'],
                disabledforeground=self.COLORS['disabled'],
                font=(self.FONT_FAMILY, 8), bd=0, highlightthickness=0
            ).pack(side=tk.RIGHT)
        else:
            tk.Checkbutton(
                head, text="全选", variable=group_var,
                command=lambda r=risk: self._on_group_toggle(r),
                bg=soft, activebackground=soft, selectcolor=self.COLORS['white'],
                font=(self.FONT_FAMILY, 8), fg=self.COLORS['text'],
                bd=0, highlightthickness=0, cursor='hand2'
            ).pack(side=tk.RIGHT)
        self.group_vars[risk] = group_var

        desc_text = RISK_LABELS[risk] + "：" + {
            RISK_SAFE: "临时文件、缓存、回收站、日志等，可放心删除",
            RISK_CAUTION: "可能含用户数据，需手动勾选并确认",
            RISK_DANGER: "用户文档/下载/系统关键数据，禁止删除",
        }[risk]
        tk.Label(
            section, text=desc_text, font=(self.FONT_FAMILY, 8),
            fg=self.COLORS['muted'], bg=soft, anchor=tk.W, justify=tk.LEFT,
            wraplength=350
        ).pack(fill=tk.X, padx=10, pady=(0, 4))

        for cat_name, items in buckets.items():
            self._build_bucket_card(section, risk, cat_name, items)

        for widget in (badge, meta):
            widget.bind('<Button-1>', lambda e, r=risk: self._show_risk_detail(r))

    def _build_bucket_card(self, parent, risk: str, cat_name: str,
                           items: List[CleanItem]):
        """渲染单个分类卡片"""
        key = f"{risk}::{cat_name}"
        color = self.RISK_COLORS[risk]
        var = tk.BooleanVar(value=(risk == RISK_SAFE))

        self.bucket_vars[key] = var
        self.bucket_items[key] = list(items)
        self.bucket_meta[key] = (risk, cat_name)

        card = tk.Frame(
            parent, bg=self.COLORS['card_bg'],
            highlightbackground=self.COLORS['border'], highlightthickness=1
        )
        card.pack(fill=tk.X, padx=8, pady=3)
        self.bucket_frames[key] = card

        row = tk.Frame(card, bg=self.COLORS['card_bg'])
        row.pack(fill=tk.X, padx=6, pady=5)

        check = tk.Checkbutton(
            row, text="", variable=var,
            command=lambda k=key: self._on_bucket_click(k),
            bg=self.COLORS['card_bg'], activebackground=self.COLORS['card_bg'],
            selectcolor=self.COLORS['white'], bd=0, highlightthickness=0,
            cursor='hand2'
        )
        if risk == RISK_DANGER:
            check.config(state=tk.DISABLED, cursor='arrow')
        check.pack(side=tk.LEFT)

        total_size = sum(item.size for item in items)
        size_label = tk.Label(
            row, text=format_size(total_size),
            font=(self.FONT_FAMILY, 8, 'bold'),
            fg=color, bg=self.COLORS['card_bg']
        )
        size_label.pack(side=tk.RIGHT)

        count_label = tk.Label(
            row, text=f"{len(items)} 项",
            font=(self.FONT_FAMILY, 8),
            fg=self.COLORS['muted'], bg=self.COLORS['card_bg']
        )
        count_label.pack(side=tk.RIGHT, padx=(0, 8))

        self.bucket_card_labels[key] = (count_label, size_label)

        name_label = tk.Label(
            row, text=cat_name,
            font=(self.FONT_FAMILY, 9),
            fg=self.COLORS['text'], bg=self.COLORS['card_bg'], anchor=tk.W
        )
        name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        for widget in (card, row, name_label, size_label, count_label):
            widget.bind('<Button-1>', lambda e, k=key: self._on_bucket_click(k))

    def _on_group_toggle(self, risk: str):
        """风险分组全选"""
        if risk == RISK_DANGER:
            return
        state = self.group_vars[risk].get()
        for key, var in self.bucket_vars.items():
            if self.bucket_meta[key][0] == risk:
                var.set(state)
        self._update_selection_summary()

    def _sync_group_vars(self):
        """根据 bucket 勾选状态同步分组复选框"""
        for risk, group_var in self.group_vars.items():
            vars_ = [
                var for key, var in self.bucket_vars.items()
                if self.bucket_meta[key][0] == risk
            ]
            group_var.set(bool(vars_) and all(v.get() for v in vars_))

    def _on_bucket_click(self, key: str):
        """点击分类卡片"""
        risk = self.bucket_meta.get(key, (None, None))[0]
        for other_key, frame in self.bucket_frames.items():
            frame.configure(
                highlightbackground=self.COLORS['border'], highlightthickness=1
            )
        if key in self.bucket_frames and risk:
            self.bucket_frames[key].configure(
                highlightbackground=self.RISK_COLORS[risk], highlightthickness=1
            )
        self.selected_bucket = key
        self._show_bucket_detail(key)
        self._sync_group_vars()
        self._update_selection_summary()

    # ============================================================
    # 详情
    # ============================================================
    def _show_bucket_detail(self, key: str):
        meta = self.bucket_meta.get(key)
        if not meta:
            return
        risk, cat_name = meta
        items = sorted(
            self.bucket_items.get(key, []), key=lambda item: item.size, reverse=True
        )
        self._fill_tree(items, f"{cat_name} · {RISK_LABELS[risk]}")

    def _show_risk_detail(self, risk: str):
        items = []
        for key, bucket_items in self.bucket_items.items():
            if self.bucket_meta[key][0] == risk:
                items.extend(bucket_items)
        items.sort(key=lambda item: item.size, reverse=True)
        self._fill_tree(items, f"{RISK_LABELS[risk]} · 全部项目")

    def _fill_tree(self, items: List[CleanItem], scope: str):
        self.tree.delete(*self.tree.get_children())
        self.tree_item_map = {}
        for item in items:
            iid = self.tree.insert(
                '', tk.END,
                values=(
                    RISK_LABELS.get(item.risk_level, item.risk_level),
                    item.path,
                    format_size(item.size),
                    item.description,
                ),
                tags=(item.risk_level,)
            )
            self.tree_item_map[iid] = item
        total_size = sum(item.size for item in items)
        self.detail_count_label.config(
            text=f"{len(items)} 项 · {format_size(total_size)}"
        )
        self.detail_scope_label.config(text=scope)

    # ============================================================
    # 右键：资源管理器定位 / 删除单条
    # ============================================================
    @staticmethod
    def _item_identity(path: str) -> str:
        """条目路径归一化（dns_cache 等伪路径按原样处理）"""
        if path == 'dns_cache':
            return path
        return os.path.normcase(os.path.abspath(path))

    def _on_tree_context_menu(self, event):
        """右键列表行：选中该行并弹出菜单"""
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        item = self.tree_item_map.get(row)
        if item is None:
            return
        self._ctx_item = item

        # 非真实路径（如 dns_cache）无法在资源管理器定位
        revealable = os.path.isabs(item.path)
        # 扫描/清理中、不建议删除项、只读分类禁止单条删除
        deletable = (
            not self.is_scanning
            and not self.is_cleaning
            and item.risk_level != RISK_DANGER
            and item.category != "磁盘空间分析"
        )
        self.ctx_menu.entryconfig(0, state=tk.NORMAL if revealable else tk.DISABLED)
        self.ctx_menu.entryconfig(1, state=tk.NORMAL if deletable else tk.DISABLED)
        try:
            self.ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.ctx_menu.grab_release()

    def _ctx_reveal_in_explorer(self):
        """在资源管理器中定位并选中该文件/文件夹"""
        item = self._ctx_item
        self._ctx_item = None
        if item is None or not os.path.isabs(item.path):
            return
        try:
            path = os.path.normpath(item.path)
            target = path if os.path.exists(path) else os.path.dirname(path)
            subprocess.Popen(f'explorer /select,"{target}"')
        except Exception as e:
            messagebox.showerror("打开失败", f"无法在资源管理器中显示：\n{e}")

    def _ctx_delete_single(self):
        """删除列表中的单个条目（删除前二次确认）"""
        item = self._ctx_item
        self._ctx_item = None
        if item is None:
            return
        if self.is_scanning or self.is_cleaning:
            messagebox.showinfo("提示", "正在扫描或清理，请稍候再试")
            return
        if item.risk_level == RISK_DANGER:
            messagebox.showwarning("已拦截", "「不建议删除」项禁止删除")
            return
        if item.category == "磁盘空间分析":
            messagebox.showinfo("提示", "磁盘空间分析为只读分类，不可删除")
            return
        if not self._confirm_delete([item], summarize_risk([item])):
            return

        self.is_cleaning = True
        self.scan_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)
        name = (
            os.path.basename(item.path.rstrip('\\/'))
            if os.path.isabs(item.path) else item.path
        )
        self.status_var.set(f"正在删除: {name}")
        self.bottom_status.config(text=f"⏳ 正在删除: {item.path}")
        self.progress_bar['value'] = 0

        def worker():
            try:
                # 避免上一次“停止扫描”残留的停止标志中断本次删除
                self.cleaner._stop_flag = False
                success, failed = self.cleaner.clean_items(
                    [item],
                    callback=lambda c, t, m: self.root.after(
                        0, self._update_progress, c, t, m
                    ),
                    allow_danger=False,
                )
                self.root.after(
                    0, lambda: self._on_single_delete_done(item, success, failed)
                )
            except Exception as e:
                msg = str(e)
                self.root.after(
                    0, lambda msg=msg: self._on_single_delete_error(msg)
                )

        threading.Thread(target=worker, daemon=True).start()

    def _on_single_delete_done(self, item: CleanItem, success: int, failed: int):
        """单条删除完成回调"""
        self.is_cleaning = False
        self.scan_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 100

        if success:
            self._remove_item_everywhere(item)
            self.stats_label.config(
                text=f"上次清理: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.status_var.set("已删除 1 项")
            self.bottom_status.config(text=f"✅ 已删除: {item.path}")
        else:
            self.status_var.set("删除失败")
            self.bottom_status.config(text=f"❌ 删除失败: {item.path}")
            messagebox.showwarning(
                "删除失败",
                f"无法删除：\n{item.path}\n\n"
                "文件可能正在被占用或权限不足。"
            )
        self._update_selection_summary()

    def _on_single_delete_error(self, error: str):
        """单条删除出错回调"""
        self.is_cleaning = False
        self.scan_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.NORMAL)
        self.progress_bar.stop()
        self.status_var.set(f"删除出错: {error}")
        self.bottom_status.config(text=f"❌ 删除出错: {error}")

    def _remove_item_everywhere(self, item: CleanItem):
        """单条删除成功后：从详情列表、分类数据、卡片统计中移除"""
        def same(it: CleanItem) -> bool:
            return self._item_identity(it.path) == self._item_identity(item.path)

        # 1. 详情列表行
        for iid, it in list(self.tree_item_map.items()):
            if same(it):
                if self.tree.exists(iid):
                    self.tree.delete(iid)
                del self.tree_item_map[iid]

        # 2. 分类原始数据（与 cleaner.categories 共享对象）
        for cat in self.categories.values():
            cat.items[:] = [it for it in cat.items if not same(it)]

        # 3. 分类卡片数据与卡片上的计数/大小
        for key in list(self.bucket_items.keys()):
            self.bucket_items[key] = [
                it for it in self.bucket_items[key] if not same(it)
            ]
            labels = self.bucket_card_labels.get(key)
            if labels is None:
                continue
            count_label, size_label = labels
            remaining = self.bucket_items[key]
            if remaining:
                count_label.config(text=f"{len(remaining)} 项")
                size_label.config(
                    text=format_size(sum(i.size for i in remaining))
                )
            else:
                frame = self.bucket_frames.get(key)
                if frame is not None:
                    frame.pack_forget()
                self.bucket_vars[key].set(False)

        # 4. 详情计数、风险条、分组勾选状态
        remaining_in_view = list(self.tree_item_map.values())
        self.detail_count_label.config(
            text=(
                f"{len(remaining_in_view)} 项 · "
                f"{format_size(sum(i.size for i in remaining_in_view))}"
            )
        )
        all_items = [
            it for cat in self.categories.values() for it in cat.items
        ]
        self._update_risk_chips(summarize_risk(all_items))
        self._sync_group_vars()

    # ============================================================
    # 选择与清理
    # ============================================================
    def _selected_items(self) -> List[CleanItem]:
        """收集当前勾选的条目（按路径去重）"""
        selected: List[CleanItem] = []
        seen = set()
        for key, var in self.bucket_vars.items():
            if not var.get():
                continue
            for item in self.bucket_items.get(key, []):
                if item.path == 'dns_cache':
                    identity = item.path
                else:
                    identity = os.path.normcase(os.path.abspath(item.path))
                if identity in seen:
                    continue
                seen.add(identity)
                selected.append(item)
        return selected

    def _reset_selection(self):
        """恢复默认：仅勾选可放心删除项"""
        for key, var in self.bucket_vars.items():
            var.set(self.bucket_meta[key][0] == RISK_SAFE)
        self._sync_group_vars()
        self._update_selection_summary()

    def _update_risk_chips(self, summary: Dict[str, Dict[str, int]]):
        for risk in RISK_ORDER:
            data = summary.get(risk, {"count": 0, "size": 0})
            self.risk_chip_labels[risk].config(
                text=f"{RISK_LABELS[risk]} {data['count']} 项 · {format_size(data['size'])}"
            )

    def _update_selection_summary(self):
        items = self._selected_items()
        summary = summarize_risk(items)
        total = len(items)
        total_size = sum(item.size for item in items)
        safe_count = summary[RISK_SAFE]['count']
        caution_count = summary[RISK_CAUTION]['count']

        self.selection_label.config(
            text=(f"已选 {total} 项（可放心 {safe_count} / 谨慎 {caution_count}）"
                  f" · {format_size(total_size)}")
        )

        can_clean = total > 0 and not self.is_scanning and not self.is_cleaning
        self.clean_btn.config(
            state=tk.NORMAL if can_clean else tk.DISABLED,
            text=f"🗑 清理选中项 ({total})" if total else "🗑 清理选中项"
        )
        self.reset_btn.config(
            state=tk.NORMAL if self.bucket_vars and not self.is_cleaning
            else tk.DISABLED
        )

    def _start_clean(self):
        """开始清理"""
        if self.is_cleaning:
            self.cleaner.stop()
            return
        if self.is_scanning:
            return

        items_all = self._selected_items()
        if not items_all:
            messagebox.showinfo("提示", "请先勾选要清理的项目")
            return

        # danger 永不允许进入清理流程（双重保护）
        items = [item for item in items_all if item.risk_level != RISK_DANGER]
        if not items:
            messagebox.showinfo("提示", "选中的项目均为「不建议删除」，已阻止清理")
            return

        summary = summarize_risk(items)
        if not self._confirm_delete(items, summary):
            return

        self.is_cleaning = True
        self.clean_btn.config(
            text="⏹ 停止清理", bg=self.COLORS['danger'],
            activebackground='#B91C1C', state=tk.NORMAL
        )
        self.scan_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)
        self.status_var.set(f"正在清理 {len(items)} 项文件...")
        self.bottom_status.config(
            text=f"⏳ 正在清理，请勿关闭程序... {format_delete_summary(items)}"
        )
        self.progress_bar['value'] = 0

        def worker():
            try:
                success, failed = self.cleaner.clean_items(
                    items,
                    callback=lambda c, t, m: self.root.after(
                        0, self._update_progress, c, t, m
                    ),
                    allow_danger=False,
                )
                self.root.after(
                    0, lambda: self._on_clean_complete(success, failed, len(items))
                )
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda msg=msg: self._on_clean_error(msg))

        self.clean_thread = threading.Thread(target=worker, daemon=True)
        self.clean_thread.start()

    def _confirm_delete(self, items: List[CleanItem],
                        summary: Dict[str, Dict[str, int]]) -> bool:
        """删除前确认对话框：按风险汇总展示"""
        dialog = tk.Toplevel(self.root)
        dialog.title("确认删除")
        dialog.configure(bg=self.COLORS['card_bg'])
        dialog.resizable(False, False)

        body = tk.Frame(dialog, bg=self.COLORS['card_bg'], padx=26, pady=22)
        body.pack(fill=tk.BOTH, expand=True)

        head = tk.Frame(body, bg=self.COLORS['card_bg'])
        head.pack(fill=tk.X)
        tk.Label(
            head, text="⚠", font=(self.FONT_FAMILY, 18, 'bold'),
            fg=self.COLORS['danger'], bg=self.COLORS['card_bg']
        ).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(
            head, text="删除前确认",
            font=(self.FONT_FAMILY, 15, 'bold'),
            fg=self.COLORS['text'], bg=self.COLORS['card_bg']
        ).pack(side=tk.LEFT)

        tk.Label(
            body, text="以下内容将从磁盘永久删除，操作无法撤销。",
            font=(self.FONT_FAMILY, 9),
            fg=self.COLORS['muted'], bg=self.COLORS['card_bg']
        ).pack(anchor=tk.W, pady=(8, 12))

        summary_frame = tk.Frame(body, bg=self.COLORS['primary_soft'])
        summary_frame.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            summary_frame, text=format_delete_summary(items),
            font=(self.FONT_FAMILY, 10, 'bold'),
            fg=self.COLORS['primary_dark'], bg=self.COLORS['primary_soft'],
            anchor=tk.W, justify=tk.LEFT, wraplength=480
        ).pack(fill=tk.X, padx=14, pady=12)

        for risk in RISK_ORDER:
            data = summary.get(risk, {"count": 0, "size": 0})
            if not data['count']:
                continue
            row = tk.Frame(body, bg=self.COLORS['card_bg'])
            row.pack(fill=tk.X, pady=3)
            tk.Label(
                row, text=f" {RISK_LABELS[risk]} ",
                font=(self.FONT_FAMILY, 8, 'bold'),
                bg=self.RISK_COLORS[risk], fg=self.COLORS['white'],
                padx=6, pady=2
            ).pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(
                row, text=f"{data['count']} 项 · {format_size(data['size'])}",
                font=(self.FONT_FAMILY, 10),
                fg=self.COLORS['text'], bg=self.COLORS['card_bg']
            ).pack(side=tk.LEFT)

        caution_count = summary[RISK_CAUTION]['count']
        danger_count = summary[RISK_DANGER]['count']
        if caution_count:
            note = "橙色项可能包含用户数据或影响个别程序，请确认无误后再删除。"
            note_color = self.COLORS['caution']
        elif danger_count:
            note = "红色项为不建议删除内容，已被拦截，不会执行删除。"
            note_color = self.COLORS['danger']
        else:
            note = "绿色项均为临时文件/缓存，删除后不影响正常使用。"
            note_color = self.COLORS['safe']
        tk.Label(
            body, text=note, font=(self.FONT_FAMILY, 9),
            fg=note_color, bg=self.COLORS['card_bg'],
            anchor=tk.W, justify=tk.LEFT, wraplength=480
        ).pack(fill=tk.X, pady=(12, 0))

        result = {'ok': False}

        def cancel():
            dialog.destroy()

        def confirm():
            result['ok'] = True
            dialog.destroy()

        buttons = tk.Frame(body, bg=self.COLORS['card_bg'])
        buttons.pack(fill=tk.X, pady=(20, 0))

        confirm_color = (
            self.COLORS['caution'] if caution_count else self.COLORS['safe']
        )
        tk.Button(
            buttons, text="确认删除", command=confirm,
            bg=confirm_color, fg=self.COLORS['white'],
            activebackground=confirm_color, activeforeground=self.COLORS['white'],
            font=(self.FONT_FAMILY, 10, 'bold'),
            padx=22, pady=8, bd=0, relief='flat', cursor='hand2'
        ).pack(side=tk.RIGHT)
        tk.Button(
            buttons, text="取消", command=cancel,
            bg='#E2E8F0', fg=self.COLORS['text'],
            activebackground='#CBD5E1', activeforeground=self.COLORS['text'],
            font=(self.FONT_FAMILY, 10),
            padx=22, pady=8, bd=0, relief='flat', cursor='hand2'
        ).pack(side=tk.RIGHT, padx=(0, 10))

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.bind("<Escape>", lambda e: cancel())
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self.root.wait_window(dialog)
        return result['ok']

    def _on_clean_complete(self, success: int, failed: int, total: int):
        """清理完成回调"""
        self.is_cleaning = False
        self.clean_btn.config(
            text="🗑 清理选中项", bg=self.COLORS['safe'],
            activebackground='#15803D'
        )
        self.scan_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 100

        self.status_var.set(f"清理完成：成功 {success} 项，失败 {failed} 项")
        self.bottom_status.config(text=f"✅ 清理完成 | 成功 {success}/{total} 项")
        self.stats_label.config(
            text=f"上次清理: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if failed > 0:
            messagebox.showwarning(
                "清理结果",
                f"清理完成\n\n"
                f"✅ 成功: {success} 项\n"
                f"❌ 失败: {failed} 项\n\n"
                f"部分文件可能正在被占用、权限不足或属于不建议删除项，已跳过。"
            )
        else:
            messagebox.showinfo(
                "清理完成",
                f"✅ 成功清理 {success} 项文件！"
            )

        self._start_scan()

    def _on_clean_error(self, error: str):
        """清理错误回调"""
        self.is_cleaning = False
        self.clean_btn.config(
            text="🗑 清理选中项", bg=self.COLORS['safe'],
            activebackground='#15803D'
        )
        self.scan_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.NORMAL)
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