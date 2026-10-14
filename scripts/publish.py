"""Explicit, source-first two-repository publication; dry run unless --push.

All assembly/commits happen in a fresh ignored run directory. No output is ever
copied into content/. Old public-only files remain archived at their old URLs.
"""
from contextlib import contextmanager
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import uuid
import urllib.parse


class PublishError(RuntimeError):
    pass


def run(args, cwd, env=None, check=True):
    result = subprocess.run([str(x) for x in args], cwd=cwd,
                            env=env, capture_output=True, encoding='utf-8',
                            errors='replace', timeout=180)
    if check and result.returncode:
        raise PublishError(f'{args[0]} {args[1]} failed ({result.returncode}):\n'
                           + result.stderr.strip() + '\n' + result.stdout.strip())
    return result


def git(root, *args, env=None, check=True):
    return run(['git', '-c', 'core.quotepath=false', '-c', 'core.longpaths=true', *args], root, env, check).stdout.strip()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def safe_relative(value):
    value = str(value).replace('\\', '/')
    path = PurePosixPath(value)
    if path.is_absolute() or not value or any(p in ('', '.', '..') or ':' in p for p in value.split('/')):
        raise PublishError('Unsafe relative path: ' + value)
    if any(p.lower() == '.git' for p in path.parts):
        raise PublishError('Git metadata cannot be selected: ' + value)
    return path.as_posix()


def file_map(folder, skip_git=True):
    result = {}
    for base, dirs, names in os.walk(folder):
        if skip_git:
            dirs[:] = [d for d in dirs if d != '.git']
        for name in dirs + names:
            if (Path(base) / name).is_symlink():
                raise PublishError('Symlink not allowed in publication: ' + str(Path(base) / name))
        for name in names:
            if skip_git and name == '.git':
                continue
            p = Path(base) / name
            rel = safe_relative(p.relative_to(folder).as_posix())
            result[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def settings(root):
    config = json.loads((root / 'scripts/publish-config.json').read_text(encoding='utf-8'))
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', PYTHONIOENCODING='utf-8')
    test_root = os.environ.get('BLOG_LOCAL_TEST_ROOT')
    if test_root:
        sandbox = Path(test_root).resolve()
        root.resolve().relative_to(sandbox)
        config = json.loads((root / '.blog/test-config.json').read_text(encoding='utf-8'))
        for key in ('source_fetch', 'source_push', 'public_fetch', 'public_push', 'theme_fetch'):
            endpoint = Path(config[key]).resolve()
            endpoint.relative_to(sandbox)
            if not endpoint.is_dir():
                raise PublishError('Local test endpoint missing: ' + str(endpoint))
        # Even a malicious redirect/config cannot let a fixture reach real remotes.
        env.update(GIT_ALLOW_PROTOCOL='file', GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_CONFIG_NOSYSTEM='1')
    else:
        allowed = {
            'source_fetch': 'https://github.com/jcq15/blog_hugo_githubpage.git',
            'source_push': 'git@github.com:jcq15/blog_hugo_githubpage.git',
            'public_fetch': 'https://github.com/jcq15/jcq15.github.io.git',
            'public_push': 'git@github.com:jcq15/jcq15.github.io.git',
            'theme_fetch': 'https://github.com/elkan1788/hugo-theme-next.git',
        }
        if any(config.get(k) != v for k, v in allowed.items()):
            raise PublishError('Production repository targets differ from the reviewed targets.')
        if config.get('site') != 'https://blog.shadiao.win/' or config.get('branch') != 'master':
            raise PublishError('Production domain/branch differs from the reviewed target.')
    return config, env, bool(test_root)


@contextmanager
def locked(root):
    folder = root / '.blog'
    folder.mkdir(exist_ok=True)
    lock = folder / 'publish.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise PublishError('Another operation or interrupted run holds .blog/publish.lock. '
                           'Check its PID before manually removing a stale lock.')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def assert_repo(root, env):
    if Path(git(root, 'rev-parse', '--show-toplevel', env=env)).resolve() != root.resolve():
        raise PublishError('Run in the source repository, not inside public/.')
    if not git(root, 'symbolic-ref', '-q', 'HEAD', env=env, check=False):
        raise PublishError('Detached HEAD: choose the source working branch first.')
    for marker in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply'):
        path = Path(git(root, 'rev-parse', '--git-path', marker, env=env))
        if not path.is_absolute():
            path = root / path
        if path.exists():
            raise PublishError('Finish the existing merge/rebase before publishing.')
    if git(root, 'diff', '--cached', '--name-only', env=env):
        raise PublishError('Index contains staged changes. Commit or unstage them deliberately first.')
    public = root / 'public'
    if (public / '.git').exists() and git(public, 'status', '--porcelain', env=env):
        raise PublishError('Existing public/ has local changes; preserve/resolve them before publishing.')


def fetch_source(root, config, env):
    git(root, 'fetch', '--no-tags', config['source_fetch'],
        config['branch'], env=env)
    return git(root, 'rev-parse', 'FETCH_HEAD', env=env)


def current_remote(root, url, branch, env):
    lines = git(root, 'ls-remote', '--exit-code', url, 'refs/heads/' + branch, env=env).splitlines()
    if len(lines) != 1:
        raise PublishError('Expected exactly one existing remote branch.')
    return lines[0].split()[0]


def source_changes(root, env):
    tracked = git(root, 'diff', '--name-only', '-z', env=env).split('\0')
    extra = git(root, 'ls-files', '--others', '--exclude-standard', '-z', env=env).split('\0')
    return sorted(set(x for x in tracked + extra if x))


def ensure_theme(root, source, config, env):
    tree = git(source, 'ls-tree', 'HEAD', 'themes/hugo-theme-next', env=env)
    if not tree.startswith('160000 commit '):
        raise PublishError('Expected the existing pinned Hugo theme submodule.')
    sha = tree.split()[2]
    theme = source / 'themes/hugo-theme-next'
    if theme.exists() and any(theme.iterdir()):
        raise PublishError('Unexpected files in isolated theme directory.')
    # Only the theme is materialized: public is assembled independently.
    git(source, 'clone', '--no-checkout', '--no-hardlinks', config['theme_fetch'], theme, env=env)
    git(theme, 'checkout', '--detach', sha, env=env)


def selection(root, args):
    selected, documents = set(), set()
    if args.site:
        manifest = json.loads((root / 'scripts/first-release.json').read_text(encoding='utf-8'))
        selected.update(safe_relative(x) for x in manifest['files'])
    for value in args.include:
        selected.add(safe_relative(value))
    for value in args.files:
        rel = safe_relative(value)
        parts = PurePosixPath(rel).parts
        if len(parts) < 4 or parts[:2] != ('content', 'zh-CN') or parts[2] not in ('post', 'moments') or not rel.endswith('.md'):
            raise PublishError('Select a Markdown file in content/zh-CN/post or moments.')
        documents.add(rel)
        selected.add(rel)
        p = root / rel
        if p.name == 'index.md':
            for image in p.parent.iterdir():
                if image.is_file() and image.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}:
                    selected.add(safe_relative(image.relative_to(root).as_posix()))
    forbidden = {'public', 'themes', 'build', 'resources', '.blog', '.agents', '.codex', '.aws'}
    for rel in selected:
        if PurePosixPath(rel).parts[0] in forbidden or PurePosixPath(rel).name in {'.env', 'publish.local.json'}:
            raise PublishError('Not a publishable source file: ' + rel)
        p = root / rel
        if not p.is_file() or p.is_symlink():
            raise PublishError('Selection must be an existing regular file: ' + rel)
        p.resolve().relative_to(root.resolve())
    return sorted(selected), documents


def ready_bytes(data):
    text = data.decode('utf-8')
    line = '\r\n' if '\r\n' in text else '\n'
    delimiter = text.splitlines()[0] if text else ''
    if delimiter not in ('---', '+++'):
        raise PublishError('Selected Markdown needs YAML or TOML front matter.')
    chunks = text.split(delimiter + line, 2)
    if len(chunks) != 3:
        raise PublishError('Malformed front matter in selected Markdown.')
    front = chunks[1]
    front = re.sub(r'(?m)^(draft[ \t]*[:=][ \t]*)true([ \t]*\r?)$', r'\g<1>false\g<2>', front)
    date = re.search(r'(?m)^date\s*[:=]\s*[\"\']?([^\r\n\"\']+)', front)
    if date:
        try:
            when = dt.datetime.fromisoformat(date.group(1).strip().replace('Z', '+00:00'))
            if when.tzinfo is None:
                when = when.replace(tzinfo=dt.timezone.utc)
            if when > dt.datetime.now(dt.timezone.utc):
                raise PublishError('Selected article is future-dated; correct its date before publishing.')
        except ValueError as exc:
            raise PublishError('Unrecognized article date; use ISO 8601.') from exc
    return (chunks[0] + delimiter + line + front + delimiter + line + chunks[2]).encode('utf-8')


def commit_if_changed(repo, message, identity, env):
    git(repo, 'add', '-A', env=env)
    if git(repo, 'diff', '--cached', '--name-only', env=env):
        git(repo, '-c', 'user.name=' + identity[0], '-c', 'user.email=' + identity[1],
            'commit', '-m', message, env=env)
    return git(repo, 'rev-parse', 'HEAD', env=env)


def assemble(source, public, candidate, config, env, documents=()):
    baseline = file_map(public)
    before_domain = public / 'CNAME'
    expected_domain = config['site'].split('://', 1)[1].rstrip('/')
    if before_domain.exists() and before_domain.read_text().strip() != expected_domain:
        raise PublishError('Published CNAME does not match the configured domain.')
    # Unique empty destination: a failed build can never reuse a previous release.
    run(['hugo', '--destination', candidate, '--baseURL', config['site']], source, env)
    built = file_map(candidate)
    if not all((candidate / p).is_file() for p in ('index.html', 'sitemap.xml', 'index.xml')):
        raise PublishError('Build is missing required root outputs.')
    if documents:
        listing = run(['hugo', 'list', 'all'], source, env).stdout
        rows = {r['path'].replace('\\', '/'): r for r in csv.DictReader(io.StringIO(listing))}
        for rel in documents:
            page = rows.get(rel)
            if not page or page['draft'].lower() != 'false':
                raise PublishError('Selected manuscript is still a draft or is not a rendered page: ' + rel)
            url_path = urllib.parse.unquote(urllib.parse.urlparse(page['permalink']).path).lstrip('/')
            output = safe_relative(url_path + 'index.html' if url_path.endswith('/') else url_path)
            # Check fresh Hugo output, before adding any archived old files.
            if output not in built:
                raise PublishError('Selected manuscript did not produce fresh HTML (future/expired/headless?): ' + rel)
    archived = []
    for rel in baseline:
        if rel not in built and rel != 'release.json':
            dest = candidate / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(public / rel, dest)
            archived.append(rel)
    (candidate / 'CNAME').write_text(expected_domain + '\n', encoding='utf-8', newline='\n')
    (candidate / '.nojekyll').write_text('', encoding='utf-8')
    legacy_file = source / 'data/legacy-routes.json'
    protected = json.loads(legacy_file.read_text(encoding='utf-8'))['published_html'] if legacy_file.exists() else []
    missing = [rel for rel in set(baseline) | set(protected) if not (candidate / rel).is_file() and rel != 'release.json']
    if missing:
        raise PublishError('Missing protected published paths: ' + ', '.join(sorted(missing)))
    return {'archived_files': archived, 'archived_html': [r for r in archived if r.endswith('.html')],
            'protected_baseline_files': len(baseline), 'protected_legacy_html': len(protected)}


def unchanged(root, start_head, captured, env):
    if git(root, 'rev-parse', 'HEAD', env=env) != start_head:
        raise PublishError('Local HEAD changed during the build. Nothing further will be pushed.')
    if git(root, 'diff', '--cached', '--name-only', env=env):
        raise PublishError('The index changed during the build. Nothing further will be pushed.')
    for rel, data in captured.items():
        if not (root / rel).exists() or (root / rel).read_bytes() != data:
            raise PublishError('A selected file changed during the build: ' + rel)


def integrate_source(root, source, sha, start_head, captured, updated, env):
    unchanged(root, start_head, captured, env)
    git(root, 'fetch', '--no-tags', str(source), sha, env=env)
    # The index was checked empty; unrelated unstaged/untracked files stay intact.
    for rel, data in updated.items():
        if data != captured[rel]:
            (root / rel).write_bytes(data)
    git(root, 'reset', '--mixed', sha, env=env)


def publish(root, args):
    report_path = root / 'build/prepare-report.json'
    journal = root / '.blog/pending-source.json'
    report = {'status': 'BLOCKED: not completed', 'mode': 'push' if args.push else 'dry-run',
              'source_pushed': False, 'public_pushed': False}
    with locked(root):
        save(report_path, report)
        try:
            config, env, testing = settings(root)
            report.update(simulation=testing, source_target=config['source_push'],
                          public_target=config['public_push'], branch=config['branch'], site=config['site'])
            previous = json.loads(journal.read_text(encoding='utf-8')) if journal.exists() else {}
            assert_repo(root, env)
            if args.push and not testing:
                local = root / '.blog/settings.json'
                approval = json.loads(local.read_text()) if local.exists() else {}
                if approval.get('pages_source') != 'master:/':
                    raise PublishError('First verify GitHub Pages = master / (root), then run setup --confirm-pages master:/.')
            selected, documents = selection(root, args)
            start_head = git(root, 'rev-parse', 'HEAD', env=env)
            source_base = fetch_source(root, config, env)
            # Recover a crash/uncertain response after the source push. Only the
            # exact prior transaction and unchanged selected bytes may advance.
            if (args.push and source_base != start_head
                    and previous.get('source_commit') == source_base
                    and previous.get('source_base') == start_head):
                prior_source = Path(previous['run']) / 'source'
                prior_source.resolve().relative_to((root / '.blog/runs').resolve())
                prior_captured = {rel: (root / rel).read_bytes() for rel in previous['selected']}
                if {k: hashlib.sha256(v).hexdigest() for k, v in prior_captured.items()} != previous['selected_sha256']:
                    raise PublishError('Interrupted source push found, but selected files changed. Reconcile manually.')
                prior_updated = {rel: (prior_source / rel).read_bytes() for rel in previous['selected']}
                if {k: hashlib.sha256(v).hexdigest() for k, v in prior_updated.items()} != previous['published_source_sha256']:
                    raise PublishError('Interrupted transaction snapshot was changed; reconcile manually.')
                integrate_source(root, prior_source, source_base, start_head, prior_captured, prior_updated, env)
                journal.unlink(missing_ok=True)
                start_head = source_base
                report['recovered_source_push'] = True
            if source_base != start_head:
                raise PublishError('Source HEAD differs from latest remote. Run sync with a clean workspace; '
                                   'ahead/diverged history requires deliberate reconciliation.')
            identity = (git(root, 'config', 'user.name', env=env, check=False),
                        git(root, 'config', 'user.email', env=env, check=False))
            if not all(identity):
                raise PublishError('Configure repository-local Git user.name and user.email first.')
            captured = {rel: (root / rel).read_bytes() for rel in selected}
            updated = {rel: ready_bytes(data) if rel in documents else data for rel, data in captured.items()}
            report.update(selected=selected, excluded_local_changes=[p for p in source_changes(root, env) if p not in selected], source_base=source_base,
                          selected_sha256={k: hashlib.sha256(v).hexdigest() for k, v in captured.items()},
                          published_source_sha256={k: hashlib.sha256(v).hexdigest() for k, v in updated.items()})
            run_dir = root / '.blog/runs' / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
            run_dir.mkdir(parents=True)
            source, public, candidate = run_dir / 'source', run_dir / 'public', run_dir / 'candidate'
            report.update(run=str(run_dir), candidate=str(candidate))
            save(report_path, report)
            git(root, 'clone', '--shared', '--no-checkout', str(root), source, env=env)
            git(source, 'config', 'core.autocrlf', 'false', env=env)
            git(source, 'checkout', '--detach', source_base, env=env)
            for rel, data in updated.items():
                dest = source / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            source_sha = commit_if_changed(source, 'Publish selected blog changes', identity, env)
            ensure_theme(root, source, config, env)
            clone_mode = ['--shared'] if testing else ['--depth', '1']
            git(root, 'clone', *clone_mode, '--single-branch', '--branch', config['branch'], config['public_fetch'], public, env=env)
            git(public, 'config', 'core.autocrlf', 'false', env=env)
            public_base = git(public, 'rev-parse', 'HEAD', env=env)
            report.update(source_commit=source_sha, public_base=public_base)
            report.update(assemble(source, public, candidate, config, env, documents=documents))
            # Traceable immutable source; no timestamps to cause no-op releases.
            digest = hashlib.sha256(json.dumps(file_map(candidate), sort_keys=True).encode()).hexdigest()
            save(candidate / 'release.json', {'source_commit': source_sha, 'files_sha256': digest})
            for rel in file_map(candidate):
                dest = public / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate / rel, dest)
            public_sha = commit_if_changed(public, 'Publish blog source ' + source_sha, identity, env)
            report.update(public_commit=public_sha, status='READY: dry-run only; no remote writes')
            unchanged(root, start_head, captured, env)
            # Fail closed if either machine has published since the initial fetch.
            if current_remote(root, config['source_fetch'], config['branch'], env) != source_base or current_remote(root, config['public_fetch'], config['branch'], env) != public_base:
                raise PublishError('A remote branch moved during the build; rerun from the latest baseline.')
            save(report_path, report)
            if args.push:
                report['status'] = 'PUSHING SOURCE; public not yet updated'
                save(report_path, report)
                save(journal, report)
                if source_sha != source_base:
                    git(source, 'push', config['source_push'], source_sha + ':refs/heads/' + config['branch'], env=env)
                report['source_pushed'] = True
                save(report_path, report)
                integrate_source(root, source, source_sha, start_head, captured, updated, env)
                journal.unlink(missing_ok=True)
                if current_remote(root, config['source_fetch'], config['branch'], env) != source_sha:
                    raise PublishError('Source advanced after its push; public was not pushed. Sync and rebuild.')
                if current_remote(root, config['public_fetch'], config['branch'], env) != public_base:
                    raise PublishError('Public advanced after the build; rerun to preserve the new baseline.')
                report['status'] = 'SOURCE SAVED; PUSHING PUBLIC'
                save(report_path, report)
                if public_sha != public_base:
                    git(public, 'push', config['public_push'], public_sha + ':refs/heads/' + config['branch'], env=env)
                report['public_pushed'] = True
                report['status'] = 'PUSHED: both repositories; hosting deployment not verified'
            save(report_path, report)
        except Exception as exc:
            report.update(status='BLOCKED: ' + str(exc), error=str(exc))
            save(report_path, report)
            raise
    print(report['status'])
    print('Target:', config['site'], '| source:', config['source_push'], '| public:', config['public_push'])
    print('Selected files:', len(report.get('selected', [])), '| excluded local changes:', len(report.get('excluded_local_changes', [])),
          '| archived HTML:', len(report.get('archived_html', [])))
    print('Source pushed:', report['source_pushed'], '| public pushed:', report['public_pushed'])
    print('Review report:', report_path)
    return report


def sync(root):
    config, env, _ = settings(root)
    with locked(root):
        assert_repo(root, env)
        if git(root, 'status', '--porcelain', env=env):
            raise PublishError('Sync requires a clean source workspace; save your draft before switching machines. No auto-stash/overwrite.')
        target = fetch_source(root, config, env)
        old = git(root, 'rev-parse', 'HEAD', env=env)
        if run(['git', 'merge-base', '--is-ancestor', old, target], root, env, False).returncode:
            raise PublishError('Source has local-only or divergent commits; reconcile manually. No reset or force push.')
        git(root, 'merge', '--ff-only', target, env=env)
    print('Source synchronized by fast-forward:', target)


def setup(root, args):
    config, env, _ = settings(root)
    assert_repo(root, env)
    if args.confirm_pages:
        if args.confirm_pages != 'master:/':
            raise PublishError('Only the reviewed Pages target master:/ is supported.')
        save(root / '.blog/settings.json', {'pages_source': args.confirm_pages})
    theme = root / 'themes/hugo-theme-next'
    if not (theme / 'theme.toml').exists():
        ensure_theme(root, root, config, env)
    print('Targets:', config['source_push'], '->', config['public_push'])
    print('Domain:', config['site'], '| branch:', config['branch'])
    print('Setup does not publish. Default publish is a dry run; --push is required.')
