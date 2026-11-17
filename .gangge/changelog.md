# 变更日志

## 2025-06-20: 全面升级为 C盘清理大师 专业版

### 变更内容
- 全面重写 cleaner.py: 从 3 个扫描模块扩展到 16 个专业清理模块
- 全面重写 gui.py: 全新现代 UI 界面，支持分类展示、详情查看、进度显示
- 保持 main.py 不变

### 新增功能模块
1. Windows 临时文件清理 — 扫描系统临时目录
2. 回收站清理 — 清空 $Recycle.Bin
3. 浏览器缓存清理 — Chrome/Edge/Firefox
4. 系统日志清理 — .log/.etl 文件
5. Windows 更新缓存清理 — SoftwareDistribution
6. 预读文件清理 (Prefetch)
7. 字体缓存清理
8. 缩略图缓存清理
9. 剪贴板历史清理
10. DNS 缓存清理
11. 空文件夹清理
12. 软件卸载残留清理
13. 大文件扫描 (>100MB)
14. 重复文件检测
15. 无效快捷方式检测
16. 磁盘空间分析

### 涉及文件
- cleaner.py (重写, 883 行)
- gui.py (重写, 675 行)
- main.py (未变)

### 风险事项
- 扫描大文件和重复文件时可能较慢（已限制数量）
- 部分功能需要管理员权限才能完全生效
- 无效快捷方式检测依赖 PowerShell

## 2026-11-17 11:13 (第7轮自动记录)
- 已完成: `test_cleanup.py`

## 2026-11-17 11:13 (第8轮自动记录)
- 已完成: `test_cleanup.py`

## 2026-11-17 11:14 (第12轮自动记录)
- 已完成: `test_cleanup.py`

## 2026-11-17 11:14 (第14轮自动记录)
- 已完成: `test_cleanup.py`

## 2026-11-17 11:20 (第18轮)
- GitHub SSH 推送任务完成：
  - 生成 ED25519 密钥对，公钥已添加到 GitHub 账号 ydsgangge-ux
  - 远程 origin 从 HTTPS 切换为 `git@github.com:ydsgangge-ux/C-Drive-Cleaner.git`
  - `git push origin master` 成功，`git ls-remote` 验证远程与本地一致（ad5653f）
- README.md 更新并推送：
  - 新增「🛡️ 风险分级保护」功能章节
  - 克隆地址改为 SSH 方式
  - 项目结构补充 test_cleanup.py
  - 使用说明中勾选逻辑改为「安全默认勾选，危险需手动勾选」
- 测试验证: `pytest test_cleanup.py` 9 个用例全部通过

## 2026-11-17 11:29 (第14轮自动记录)
- 已完成: `.gangge/progress.md`

## 2026-11-17 11:30 (第17轮自动记录)
- 已完成: `.gangge/progress.md`
