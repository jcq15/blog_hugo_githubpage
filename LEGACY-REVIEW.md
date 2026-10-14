# 历史页面核对与第二轮验证

本轮只修改安全副本。原 `public` 发布仓库没有删除、提交或推送。源码已更新到 `8a4f4a5`，发布仓库已更新到 `f501d4d`。

## 20 个历史地址的逐项结论

下表的每个 URL 对应一个原发布 HTML 文件。它们不在当前正常 Hugo 构建输出中，不等于可以删除。

| # | 旧 URL | 证据与判断 | 本轮处理 |
|---|---|---|---|
| 1 | `/post/markdown-syntax/` | 主题 Markdown 示例；当前中文源文件明确 `draft = true` | 不改草稿状态，待决定是否保留旧版只读档案 |
| 2 | `/categories/syntax/` | 只列出上述中文示例 | 同上 |
| 3 | `/categories/syntax/p/1/` | 上一地址的第一页跳转 | 随所属目录处理 |
| 4 | `/categories/themes/` | 只列出上述中文示例 | 随示例处理 |
| 5 | `/categories/themes/p/1/` | 上一地址的第一页跳转 | 随所属目录处理 |
| 6 | `/tags/css/` | 只列出上述中文示例 | 随示例处理 |
| 7 | `/tags/css/p/1/` | 上一地址的第一页跳转 | 随所属目录处理 |
| 8 | `/tags/html/` | 只列出上述中文示例 | 随示例处理 |
| 9 | `/tags/html/p/1/` | 上一地址的第一页跳转 | 随所属目录处理 |
| 10 | `/tags/markdown/` | 只列出上述中文示例 | 随示例处理 |
| 11 | `/tags/markdown/p/1/` | 上一地址的第一页跳转 | 随所属目录处理 |
| 12 | `/tags/马克当/` | 只列出上述中文示例 | 随示例处理 |
| 13 | `/tags/马克当/p/1/` | 上一地址的第一页跳转 | 随所属目录处理 |
| 14 | `/en/post/rich-content/` | Hugo 富文本/短代码示例，原始 Markdown 在历史提交 `21d3ec7`；于 `92e1961` 删除 | 不擅自重新发布，可从 Git 找回原稿供归档 |
| 15 | `/en/tags/privacy/` | 只列出上述英文示例 | 随示例处理 |
| 16 | `/en/tags/privacy/p/1/` | 上一地址的第一页跳转 | 随所属目录处理 |
| 17 | `/en/tags/shortcodes/` | 只列出上述英文示例 | 随示例处理 |
| 18 | `/en/tags/shortcodes/p/1/` | 上一地址的第一页跳转 | 随所属目录处理 |
| 19 | `/post/newurlandregularlyupdate/` | 真正的用户文章：《【重要】域名变更、定期更新及其他说明》，约 1140 字，涉及域名迁移、定期更新计划及公众号说明 | 应保留。当前源码及所有可达 Git 历史均未找到原稿；单独保存发布 HTML 为待核对材料 |
| 20 | `/post/大学敢想-副本/` | 文件名容易误导，正文实际为电信诈骗通报；`999c1df` 中的原 Markdown 与现有 `电信诈骗.md` 除换行标准化外完全一致，旧副本在 `c2fdba5` 删除 | 已在副本添加到 `/post/电信诈骗/` 的兼容跳转，评论标题关联不变 |

因此，20 个地址中：13 个属于中文示例及目录，5 个属于英文示例及目录，1 个是真实缺源旧文章，1 个是可确定对应的旧文章地址。已修好最后一项，剩余 **19 个**仍受发布检查保护。

早先说明里把最后一项误写成“数学基础-逻辑”，是终端字符显示导致的误判；实际路径为 **大学敢想-副本**，这里已按 UTF-8 原文件和 Git 证据纠正。

## 最小决策建议

1. 对两组主题示例，建议继续不放回首页/时间流；如果要严格保留所有旧链接，可做单独的只读历史档案。中文源文件已标记为草稿、英文源文件已删除，不能仅因旧 HTML 尚在就重新作为正常文章发布。这一选择同时处理 18 个地址，无须逐条决定。
2. 对“域名变更”文章，建议保留其原地址和文章内容。先找笔记本上的 Markdown；如果确实只剩发布 HTML，再依据单独保存的材料整理待核对稿，确认后纳入。当前没有用 HTML 代替源码。材料：`review-materials/newurlandregularlyupdate.published.html`，原发布仓库的原件也仍在。
3. 不需要对“大学敢想-副本”再做决定，内容对应已验证并修复。

证据文件：`build/legacy-audit.json`（每页标题、正文摘要、旧文章链接、HTML 哈希与源码历史）；`data/legacy-routes.json`（218 个发布路径、47 个兼容跳转、19 个待决策地址）。

## 真实浏览器验证

原 CUA 工具在执行 `getState()` 之前就退出，重置后仍返回：`MXC launcher: cannot locate required Windows platform directory: HRESULT 0x80070003`。这是工具运行时初始化失败，没有收到权限拒绝，也没有绕过安全提示。

替代路线使用电脑**已经安装**的 Edge 无界面模式、独立 `build/qa-edge-*` 配置与现有 Node v24 内置 WebSocket。没有安装浏览器、扩展或依赖；未读取用户浏览器会话。调试端口仅在本机，截图后已关闭测试浏览器。

通过 DevTools 精确设置视口，测试了 1440px 桌面首页/文章、390px 手机首页/文章/片刻。初次 `--window-size` 截图有 Edge 最小窗口宽度造成的裁切，因此改用真实视口设置后重拍并以 DOM 宽度复核；交付截图是重拍后的版本。

- 所有 5 个页面无横向溢出，无坏图；手机导航均落在视口内。
- 最新数学文章桌面和手机均实际生成 8 个 MathJax 数学块。
- 已人工查看桌面首页、桌面文章、手机首页、手机片刻截图。
- 结果：`build/browser-verification.json`。
- 截图：`build/desktop-home.png`、`build/mobile-home.png`、`build/desktop-article.png`、`build/mobile-article.png`、`build/mobile-moments.png`。

## 创作与构建保护

`scripts/blog.py` 不包含 Git commit、push 或部署调用；唯一外部程序调用是 Hugo，联网只读获取线上 sitemap。`new` 只写新 bundle，`ready` 只修改指定源稿的草稿标记，`prepare` 只写全新的候选输出目录和检查报告。

本轮修复了一个实质问题：原先 Hugo 失败可能留下上次成功报告。现在每次准备开始就先写入“未完成/阻止发布”，构建错误时写入明确失败报告并返回非零状态，不能误用旧成功结果。

完整测试在 `build/authoring-test-*` 隔离副本中运行，测试文稿不会进入用户当前预览或源码。运行命令：

```powershell
python scripts/test_authoring_e2e.py
python scripts/blog.py prepare
python scripts/verify_local.py
```

端到端测试实际执行：创建文章和带图动态 → 在 1314 端口启动预览并访问新页面/图片 → 正式候选构建排除草稿 → `ready` 后正式候选包含文章和图片 → 历史 URL 检查阻止发布 → 人为破坏测试副本的 Hugo 模板，确认失败覆盖旧成功报告。还覆盖中文、单双引号、冒号、井号、HTML 符号和换行标题，以及空标题、不存在图片和越界文件路径。实际参数与返回码见 `build/authoring-e2e.json`。

1314 测试预览已停止，用户的 1313 预览保持运行。线上站点未改动。
