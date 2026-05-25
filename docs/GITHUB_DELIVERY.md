# GitHub 发布执行说明

## 发布前门槛

只有在 `docs/DEMO_ACCEPTANCE.md` 必做项完成且 `docs/DEMO_COMPLETION_REPORT.md` 记录了真实测试结果后，才发布仓库。

医疗材料相关项目即使当前仅有合成数据，也默认创建为 **private**；团队明确同意公开后再调整可见性。

## 发布前检查

```bash
git status --short
git ls-files | grep -Ei '(\.env|token|secret|credential|patient|real[-_ ]?record)' || true
git log --oneline --max-count=8
```

确保不追踪 `.venv/`、`node_modules/`、构建输出、环境文件和任何真实材料。

## 使用 GitHub CLI 推送新仓库

```bash
gh auth status
git init                           # 若仓库尚未初始化
git add .
git commit -m "feat: deliver synthetic transfer timeline demo"
git branch -M main
gh repo create zgcHack --private --source=. --remote=origin --push
```

若本地已有 Git 历史，只提交尚未提交的验证后变更，不要重复 `git init` 或破坏提交历史。

## Codex 输出要求

Codex 必须报告：
- 最终运行命令及测试结果；
- 创建仓库命令是否成功；
- `origin` 指向的仓库名称；
- 若认证失败，仅报告需要用户完成的 `gh auth login` 授权步骤，不得假称已经上传。
