async function loadGitHubComments(section) {
  const { repo, issue, hiddenIds } = section.dataset;
  const ignored = new Set(hiddenIds.split(','));
  const status = section.querySelector('[data-comment-status]');
  const list = section.querySelector('[data-comment-list]');
  const comments = document.createDocumentFragment();
  const endpoint = new URL(`https://api.github.com/repos/${repo}/issues/${issue}/comments`);
  endpoint.searchParams.set('per_page', '100');
  let count = 0;

  status.textContent = '正在加载评论…';
  try {
    for (let page = 1; ; page += 1) {
      endpoint.searchParams.set('page', String(page));
      const response = await fetch(endpoint, {
        headers: { Accept: 'application/vnd.github+json' },
      });
      if (!response.ok) throw new Error(`GitHub API: ${response.status}`);

      const batch = await response.json();
      for (const comment of batch) {
        if (ignored.has(String(comment.id))) continue;

        const article = document.createElement('article');
        const author = document.createElement('a');
        const body = document.createElement('p');
        author.href = `https://github.com/${repo}/issues/${issue}#issuecomment-${comment.id}`;
        author.textContent = comment.user?.login ?? 'GitHub 用户';
        body.textContent = comment.body;
        body.style.whiteSpace = 'pre-wrap';
        body.style.overflowWrap = 'anywhere';
        article.append(author, body);
        comments.append(article);
        count += 1;
      }
      if (!response.headers.get('Link')?.includes('rel="next"')) break;
    }
    list.replaceChildren(comments);
    status.textContent = count ? '' : '暂无评论。';
  } catch {
    status.textContent = '暂时无法加载评论，可以前往 GitHub 查看。';
  }
}

document.querySelectorAll('[data-github-comments]').forEach(loadGitHubComments);
