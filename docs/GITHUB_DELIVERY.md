# GitHub 发布执行说明

## 发布前门槛

只有在 `docs/DEMO_ACCEPTANCE.md` 必做项完成且 `docs/DEMO_COMPLETION_REPORT.md` 记录了真实测试结果后，才发布仓库。

当前团队策略已确定：`WangSibothunder/zgcHack` 是用于黑客松展示的 **public** synthetic demo 仓库。不得改成 private，不要创建替代仓库；公开的前提是仓库只包含合成数据、示例配置和可公开的工程代码。

## 发布前检查

```bash
git status --short
git ls-files | grep -Ei '(\.env|token|secret|credential|real[-_ ]?record|runtime|uploads|sqlite|\.db|cookie)' || true
git log --oneline --max-count=8
```

确保不追踪 `.venv/`、`node_modules/`、构建输出、环境文件、runtime 上传内容、OCR 缓存、数据库运行文件、日志和任何真实材料。

## 使用 GitHub CLI 推送 public 仓库

```bash
gh auth status
git init                           # 若仓库尚未初始化
git add .
git commit -m "feat: deliver synthetic transfer timeline demo"
git branch -M main
gh repo create zgcHack --public --source=. --remote=origin --push
```

若本地已有 Git 历史，只提交尚未提交的验证后变更，不要重复 `git init` 或破坏提交历史。

若远程 public 仓库已经存在，使用：

```bash
git remote add origin git@github.com:WangSibothunder/zgcHack.git  # 若尚未设置 origin
git push -u origin main
```

## Codex 输出要求

Codex 必须报告：
- 最终运行命令及测试结果；
- 创建仓库命令是否成功；
- `origin` 指向的仓库名称；
- 若认证失败，仅报告需要用户完成的 `gh auth login` 授权步骤，不得假称已经上传。
