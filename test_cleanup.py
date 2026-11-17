# -*- coding: utf-8 -*-
"""C盘清理大师 - 风险分级与模块基本测试"""
import ast

import cleaner
import gui


# ---------- 语法与模块 ----------

def test_syntax_all_files():
    for f in ("cleaner.py", "gui.py", "main.py"):
        ast.parse(open(f, encoding="utf-8").read(), f)


# ---------- 风险分级 ----------

def _item(category, path):
    return cleaner.CleanItem(
        path=path, size=10, category=category, description="测试项",
    )


def test_clean_item_has_risk_level():
    item = _item("临时文件", "C:\\Windows\\Temp\\t.tmp")
    assert item.risk_level in ("safe", "caution", "danger")


def test_classify_risk_exists():
    assert callable(cleaner.classify_risk), "cleaner.py 应提供 classify_risk 分级函数"
    level = cleaner.classify_risk("临时文件清理", "C:\\Temp\\cache")
    assert level in cleaner.RISK_ORDER


def test_temp_file_is_safe():
    item = _item("Windows 临时文件清理", "C:\\Windows\\Temp\\a.tmp")
    assert item.risk_level == "safe"


def test_user_document_is_danger():
    item = _item("文档扫描", "C:\\Users\\me\\Documents\\报告.docx")
    assert item.risk_level == "danger"


def test_all_levels_covered_in_source():
    src = open("cleaner.py", encoding="utf-8").read()
    for lv in ("safe", "caution", "danger"):
        assert lv in src, f"cleaner.py 缺少 {lv} 分级"


def test_risk_summary_and_grouping():
    items = [
        _item("Windows 临时文件清理", "C:\\Windows\\Temp\\a.tmp"),
        _item("文档扫描", "C:\\Users\\me\\Documents\\b.docx"),
    ]
    summary = cleaner.summarize_risk(items)
    assert summary["safe"]["count"] >= 1
    assert summary["danger"]["count"] >= 1
    summary_text = cleaner.format_delete_summary(items)
    assert "可放心删除" in summary_text and "不建议删除" in summary_text


# ---------- GUI ----------

def test_gui_shows_risk_and_confirm():
    src = open("gui.py", encoding="utf-8").read()
    assert any(k in src for k in ("风险", "谨慎", "禁止删除", "risk")), "gui.py 未展示风险分级"
    assert "确认" in src, "gui.py 缺少删除前确认对话框"


def test_gui_class_exists():
    assert hasattr(gui, "CleanerGUI")
