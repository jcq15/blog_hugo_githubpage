# 博客 SEO 维护

保留现有 Hugo 0.101 和发布入口；发布时自动生成元数据，无需逐篇手填。

- `description` 可选：不填时自动摘取正文摘要，截断为 160 字符；不改文章标题。
- `date` 延续原来的排序用途。只有确认真实时间后才填写 `actualPublished`、`actualModified`（ISO 8601，例如 `2026-11-02T15:00:00+08:00`）。未知就留空，禁止用本次构建时间批量充当发表或修改时间。页面、结构化数据、RSS、sitemap 统一采用确认后的字段。闭社导入的 date 为原动态时间，不等于博客首次发布时间。
- 有真实内容的片刻默认允许收录。个别不适合搜索的页面可以添加 `noindex: true`（TOML 为 `noindex = true`），自动从 sitemap 排除，仍允许爬虫读取 noindex。
- 英文内容目前全为示例，统一 noindex，并从 sitemap 索引排除。开始认真写英文站时需同时修改 seo、sitemap 和 sitemapindex 三处语言策略。
- `images` 可选列表：填写能代表文章的绝对图片 URL。片刻自动使用第一张导入配图；没有合适图片的文章不伪造图片。不要把作者头像当文章插图。
- Google/Bing 公开验证值位于 config/_default/params.toml 的 SEO 部分。
- 线上已发现 Cloudflare 自动注入 beacon 并请求 /cdn-cgi/rum；cloudflareToken 保持为空，避免重复统计。只有确认自动注入关闭后才填写手动统计 token。
- 发布器会保留历史网址，并为旧 HTML 修正 canonical，历史英文/模板示例禁止索引；不会删除旧文章正文。
- Search Console 和 Bing 提交 https://blog.shadiao.win/sitemap.xml。每月查看一次站点地图、索引错误、自然搜索点击及引荐来源即可。

## 尚需处理

- Cloudflare：仅 blog.shadiao.win 的 HTTP 请求做 301 到对应 HTTPS 路径，保留查询字符串；旧域名需要先确认控制权和 TLS，再保留路径 301。不能通过 Hugo 实现服务器级重定向。
- 10 个旧图片引用的源文件在源码和当前线上仓库中均缺失。保留原文引用，待作者提供原图恢复；清单见本轮审计报告。
- 核实长文真实发表/修改日期；不要从排序日期或导入日期推断。
- 原创性保护另列待办：稳定内容哈希、Ed25519 或 RSA-PSS 签名、独立可信时间戳、版本证明与公钥轮换。本轮不生成密钥、不实施签名。
