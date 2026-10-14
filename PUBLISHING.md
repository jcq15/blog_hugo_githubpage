# 写作与发布

当前还没有把本次改造推送上线。下列 `--push` 是完成首次核对、得到上线确认后才使用的命令；省略它只演练。

## 固定工作目录

本机继续使用：

```powershell
cd 'C:\Users\shitter\Documents\Codex\2026-10-11\task\blog-preview'
```

不要在桌面旧副本和这个目录交替写作。`public` 是旧架构留下的子模块位置，发布工具不会要求你进入其中操作；它在忽略的 `.blog/runs/` 中建立独立临时发布仓库，保留其 `.git`。源码远端与生成页面远端仍是两个仓库。

## 日常最短路径

开始写作前，在没有未保存 Git 改动的情况下同步：

```powershell
python scripts/blog.py sync
```

长文章或短动态选一条创建，再打开命令输出的 `index.md` 编辑：

```powershell
python scripts/blog.py new post --title "今天想写的题目"
python scripts/blog.py new moment --title "今天的一点小事" --body "在这里写一句话。"
python scripts/blog.py new moment --title "今天的一张照片" --image "C:\你的照片目录\photo.jpg"
```

`--image` 对长文章也适用，复制图片到文章目录并插入 Markdown。多图直接放在同一目录，在正文写 `![说明](./图片.jpg)`。发布时自动选择同目录的 jpg/jpeg/png/gif/webp/svg 图片；不要把不想公开的图片放在这篇文章的目录里。其他附件用一次 `--include "相对文件路径"` 显式加入。

预览沿用 `python scripts/blog.py preview`，打开 <http://localhost:1313/>；已开着时刷新即可。草稿会出现在预览中。

写好后，使用真实路径替换下面的示例。无需先执行 `ready`：

```powershell
# 演练：构建已选稿件，不修改原稿，不推送
python scripts/blog.py publish "content/zh-CN/post/实际目录/index.md"

# 确认要公开以后：同一条命令加 --push
python scripts/blog.py publish "content/zh-CN/post/实际目录/index.md" --push
```

短动态同理，路径中的 `post` 换成 `moments`。一次可指定多个 Markdown 路径。选中的新稿会在发布快照中变成 `draft: false`；真实源码推送成功后才同步回本地。其他本地改动、其他未发布草稿不会自动提交。已提交到源码仓库的非草稿内容当然仍参与构建。`ready` 仍可单独使用，但不会发布。

`prepare` 是同一演练流程的只读远端版本，支持同样的稿件参数、`--site`、`--include`，不接受 `--push`。

## 首次上线

1. 检查 GitHub 仓库 `jcq15/jcq15.github.io` 的 Settings → Pages，确认来源确实是 `master` 分支的根目录 `/`。公开 API 当前返回 404，本地工具没有替你确认，也没有修改账号权限。若设置不同，先停止，按真实设置调整并复核工具。
2. 确认本机已有 Git/Hugo/Python，以及访问两个仓库的现有 SSH 权限。在源码仓库配置你自己的 `git config user.name` 和 `git config user.email`。本脚本不会安装软件、创建密钥或改变账号权限。
3. 确认 Pages 设置后记录一次本机设置（不发布）：

   ```powershell
   python scripts/blog.py setup --confirm-pages master:/
   ```

4. 本次外观改造和发布工具的首发文件已经逐项列在 `scripts/first-release.json`；不会把旧工作区的全部改动一锅提交。先演练、看 `build/prepare-report.json` 的 `selected` 和 `excluded_local_changes`：

   ```powershell
   python scripts/blog.py publish --site
   ```

5. 用户明确确认首次上线后，才运行：

   ```powershell
   python scripts/blog.py publish --site --push
   ```

源码目标固定为 `jcq15/blog_hugo_githubpage` 的 `master`，发布目标为 `jcq15/jcq15.github.io` 的 `master`，域名为 `blog.shadiao.win`。工具使用配置中的明确地址，原安全副本的 `origin` 与 `DISABLED` 推送地址不需要改动。禁止绕过脚本对着旧 `public` 盲推。

## 历史地址如何保留

每次先读取最新发布仓库，再把新 Hugo 输出没有生成的旧文件按原路径保留下来。旧 18 个示例/目录地址和真正的“域名变更”文章因此继续能访问；保留的是原 HTML 和资源，不是伪造 Markdown，也不会加入新首页、文章列表或主 RSS。已有兼容跳转照常工作。源码和旧发布内容没有互相反向覆盖。

保留策略也意味着：删除一个源稿不会自动从网上删除旧页面。真要撤稿或清理旧文件，需要单独明确处理，不能靠发布时顺手删除。工具核对所有最新发布文件与原 218 个 HTML 路径，补齐 `CNAME` 和 `.nojekyll`，不删除发布仓库的 `.git`。

## 两台电脑

首次上线并把工具保存进源码仓库后，在另一台已有 Git/Hugo/Python 的电脑选固定目录：

```powershell
git clone git@github.com:jcq15/blog_hugo_githubpage.git blog
cd blog
python scripts/blog.py setup
python scripts/blog.py sync
```

`setup` 只准备原主题，不下载/覆盖旧 `public`，不发布。那台电脑首次真正发布前也需核对 Pages，并执行 `setup --confirm-pages master:/`。每次写前同步，发布后另一台再同步；不要让两台同时改同一稿件后直接发布。

`sync` 只允许干净工作区快进；不自动 stash、合并、重置或覆盖。未完成的私人草稿不会由发布命令同步到另一台；如需转移私人草稿，使用自己明确选择的安全传输方式，不要为了同步而把不想公开的内容加入公开源码仓库。遇到脏工作区、暂存内容、落后或分叉，先保留并处理自己的改动，再同步。

## 失败与重试

- 每次均生成全新的候选目录，构建或核对失败就停止，不使用上次产物。报告在 `build/prepare-report.json`。
- 两个仓库无法做跨仓库原子事务，所以先推源码，再推产物。报告精确区分 `source_pushed` 和 `public_pushed`。
- 如果源码已保存、产物推送失败，排除网络/权限问题后运行 `python scripts/blog.py publish --push`；它会重新获取基线、重新构建，保留其他电脑期间新增的发布文件。不要手动推旧候选。
- 如果在源码推送后、同步本地前中断，保持文稿不变并重跑原命令；工具只在远端版本、事务记录和文件哈希都吻合时恢复。若文稿又变了，停止并人工处理。
- 源码或发布远端在构建期间发生更新会阻止继续推送；不用强制推送。源码同步后再重试。
- `.blog/publish.lock` 防止本机并发；若异常断电留下锁，先确认锁内 PID 已不运行，再手动删除这个锁文件。
- 产物根目录 `release.json` 记录源码提交和文件摘要。双仓库推送成功不等于 GitHub Pages 部署已完成；上线后检查 Pages 状态及网站、文章、短动态、旧链接、RSS。

## 本地模拟验证

`scripts/test_publish.py` 使用真实 Hugo 和 Git，只向临时本地 bare 仓库提交推送。三项参数必须是本机已有仓库；测试配置约束路径，Git 网络协议也被限制为 `file`：

```powershell
python scripts/test_publish.py --source "C:\Users\shitter\Desktop\blog" --public "C:\Users\shitter\Desktop\blog\public" --theme "C:\Users\shitter\Desktop\blog\themes\hugo-theme-next"
```

结果为 `build/publish-test-report.json`，隔离样本保留在 `build/publish-tests-*`。旧 `test_authoring_e2e.py` 针对旧版的“19 地址阻止发布”规则，已由新测试覆盖当前作者流程与发布事务，不用于这版验收。
