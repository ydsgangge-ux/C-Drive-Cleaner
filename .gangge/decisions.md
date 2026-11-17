# 决策记录

记录项目中的关键技术决策，防止重复犯错。

## 2026-11-17: GitHub 推送改用 SSH

- **背景**: HTTPS 推送需要每次输入账号/令牌，无法持久保存。
- **决策**: 生成 ED25519 密钥对，公钥添加到 GitHub 账号 ydsgangge-ux，
  将 origin 远程地址改为 `git@github.com:ydsgangge-ux/C-Drive-Cleaner.git`。
- **结果**: `git push origin master` 免密推送成功，`git ls-remote` 验证一致。
- **注意**: 密钥私钥保留在本机 `~/.ssh/id_ed25519`，不入库；`.gitignore`
  已屏蔽 `.gangge/logs/` 等内部文件。

## 2026-11-17: 清理项风险分级

- **决策**: 每个 CleanItem 标注 `safe` / `medium` / `danger` 三级，
  危险项（回收站、Cookie 等不可逆操作）默认不勾选，需用户手动确认。
- **验证**: `test_cleanup.py` 9 个用例覆盖分级与 GUI 确认逻辑。
