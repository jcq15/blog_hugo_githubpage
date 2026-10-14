# 沙雕园：本地写作与发布

工作目录：`C:\Users\shitter\Documents\Codex\2026-10-11\task\blog-preview`。

完整操作指南：[PUBLISHING.md](PUBLISHING.md)。保留 Hugo、Markdown 与源码/产物双仓库架构；已认可的页面外观和“全部 / 长文章 / 短动态”导航保持不变。

## 常用命令

```powershell
python scripts/blog.py sync
python scripts/blog.py new post --title "文章题目"
python scripts/blog.py new moment --title "今天的一点小事" --body "随手记一句。"
python scripts/blog.py preview
python scripts/blog.py publish "content/zh-CN/post/实际目录/index.md"
```

`sync` 要求干净工作区，只快进，不自动合并或覆盖。`new` 返回可编辑的 Markdown 路径。预览在 <http://localhost:1313/>，包含草稿；也可双击 `preview.cmd`。`publish` 默认只演练，选中稿件及同目录图片，其他本地改动不自动提交。`prepare` 是不接受 `--push` 的同一演练入口。

正式发布需先核对 Pages 设置并记录 `setup --confirm-pages master:/`；得到上线确认后，给同一 `publish` 命令加 `--push`。首次改造上线使用 `publish --site` 演练，文件清单见 `scripts/first-release.json`。本次尚未向真实远端推送或改变线上内容。

## 发布保护

- 目标固定：源码 `jcq15/blog_hugo_githubpage`、产物 `jcq15/jcq15.github.io`、分支 `master`、域名 `blog.shadiao.win`。
- 安全副本的 `origin` 仍指向桌面原仓库，push URL 仍为 `DISABLED`；新工具使用经过检查的明确目标，不依赖这个 origin。
- 每次读取最新源码和发布基线，在 `.blog/runs/` 中独立构建；不把生成网页反向写入 Markdown 源码，也不要求初始化旧 `public`。
- 先推源码，再推产物，产物 `release.json` 标明源码提交。构建/冲突失败时停止；部分推送失败有报告和重试路径，不复用旧产物。
- 所有发布基线文件保留，补齐 CNAME、`.nojekyll`，保留临时发布仓库 `.git`。原 19 个旧地址保留为原路径 HTML 与资源，不重新加入新首页或主 RSS。历史分析见 [LEGACY-REVIEW.md](LEGACY-REVIEW.md)，其中“待决策/旧检查阻止发布”是改造前的记录。
- 本地已有的未选择改动和示例草稿均不自动清理；如需在这台电脑执行 `sync`，先明确保存这些本地工作。新电脑按操作指南从已发布源码仓库克隆，避免混用多个副本。

## 验证

最新测试：`scripts/test_publish.py`，使用真实 Hugo/Git，但只向隔离的本地 bare 仓库推送，报告位于 `build/publish-test-report.json`。测试覆盖首发、选稿/配图、历史页保留、失败重试、中断恢复、两台电脑同步及冲突。

真实目标的演练报告：`build/prepare-report.json`，默认不推送。首次线上发布前还需确认 GitHub Pages 为 `master` 根目录；公开 API 返回 404，本次没有改变权限或创建凭证。

旧版页面验证保留于 `build/verification.json`、`build/browser-verification.json`。本机已有 Hugo 0.101.0；没有换框架、安装软件或改动原主题。旧版 `test_authoring_e2e.py` 验证的是旧发布检查规则，当前流程以新的本地双仓库测试为准。
