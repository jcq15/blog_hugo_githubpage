"""Real Hugo + real Git pushes, strictly to local bare fixtures. No GitHub writes.

python scripts/test_publish.py --source <local source repo> --public <local public repo>
                             --theme <local initialized theme repo>
All fixture repositories, hooks, outputs and reports stay under build/.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

import publish as release

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'public', 'theme'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    for repository in (args.source, args.public, args.theme):
        if not repository.is_dir() or '://' in str(repository):
            parser.error('Fixtures must be existing local repositories.')
    sandbox = ROOT / 'build' / ('publish-tests-' + str(time.time_ns()))
    sandbox.mkdir(parents=True)
    env = dict(os.environ, BLOG_LOCAL_TEST_ROOT=str(sandbox), GIT_ALLOW_PROTOCOL='file',
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', PYTHONIOENCODING='utf-8')
    checks = []

    def cmd(argv, cwd=sandbox, expected=0):
        result = subprocess.run([str(a) for a in argv], cwd=cwd, env=env,
                                capture_output=True, encoding='utf-8', errors='replace', timeout=180)
        if result.returncode != expected:
            raise AssertionError(f'{argv}\nexit {result.returncode}, expected {expected}\n{result.stdout}\n{result.stderr}')
        return result.stdout.strip()

    def git(repo, *argv):
        return cmd(['git', '-c', 'core.quotepath=false', *argv], repo)

    def cli(repo, *argv, expected=0):
        return cmd([sys.executable, 'scripts/blog.py', *argv], repo, expected)

    def checked(name):
        checks.append(name)
        print('PASS:', name, flush=True)

    def report(repo):
        return json.loads((repo / 'build/prepare-report.json').read_text(encoding='utf-8'))

    def sha(remote):
        return git(remote, 'rev-parse', 'refs/heads/master')

    def blob(remote, commit, name):
        return subprocess.run(['git', 'show', commit + ':' + name], cwd=remote, env=env,
                              capture_output=True, check=True).stdout

    config = json.loads((ROOT / 'scripts/publish-config.json').read_text())
    config['site'] = 'https://blog.example.invalid/'
    for name in ('source', 'public', 'theme'):
        remote = sandbox / (name + '.git')
        cmd(['git', 'clone', '--bare', '--no-hardlinks', getattr(args, name).resolve(), remote])
        config[name + '_fetch'] = str(remote)
        if name != 'theme':
            config[name + '_push'] = str(remote)
    source_remote, public_remote = sandbox / 'source.git', sandbox / 'public.git'
    # Make the fixture domain explicit, keeping the real public repository untouched.
    pub_seed = sandbox / 'public-seed'
    cmd(['git', 'clone', public_remote, pub_seed])
    for key, val in [('user.name', 'Local Test'), ('user.email', 'test@example.invalid'), ('core.autocrlf', 'false')]:
        git(pub_seed, 'config', key, val)
    (pub_seed / 'CNAME').write_text('blog.example.invalid\n')
    git(pub_seed, 'add', 'CNAME')
    git(pub_seed, 'commit', '-m', 'Local-only test domain')
    git(pub_seed, 'push', 'origin', 'master')

    def machine(name):
        work = sandbox / name
        cmd(['git', 'clone', '--no-hardlinks', source_remote, work])
        for key, val in [('user.name', 'Local Test'), ('user.email', 'test@example.invalid'), ('core.autocrlf', 'false')]:
            git(work, 'config', key, val)
        (work / '.blog').mkdir()
        (work / '.blog/test-config.json').write_text(json.dumps(config), encoding='utf-8')
        return work

    a = machine('desktop')
    manifest = json.loads((ROOT / 'scripts/first-release.json').read_text(encoding='utf-8'))
    for rel in manifest['files']:
        destination = a / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, destination)
    initial_source, initial_public = sha(source_remote), sha(public_remote)
    cli(a, 'publish', '--site')
    dry = report(a)
    assert dry['status'].startswith('READY:') and sha(source_remote) == initial_source and sha(public_remote) == initial_public
    assert git(a, 'rev-parse', 'HEAD') == initial_source
    legacy = json.loads((ROOT / 'data/legacy-routes.json').read_text(encoding='utf-8'))
    retained = legacy['unresolved'] if 'unresolved' in legacy else legacy['original_unresolved']
    for rel in retained:
        assert (Path(dry['candidate']) / rel).is_file()
    assert 'post/newurlandregularlyupdate/index.html' in dry['archived_html']
    assert 'post/markdown-syntax/index.html' in dry['archived_html']
    assert b'newurlandregularlyupdate' not in (Path(dry['candidate']) / 'index.html').read_bytes()
    assert b'markdown-syntax' not in (Path(dry['candidate']) / 'index.html').read_bytes()
    assert (Path(dry['candidate']) / 'moments/index.html').is_file()
    assert (Path(dry['candidate']) / 'moments/index.xml').is_file()
    checked('Initial migration dry-run: real Hugo, no pushes; historical HTML retained outside new home feed')

    # A rejected source push must not touch public or apply draft changes locally.
    source_hook = source_remote / 'hooks/pre-receive'
    source_hook.write_text('#!/bin/sh\nexit 1\n', newline='\n')
    cli(a, 'publish', '--site', '--push', expected=1)
    assert sha(source_remote) == initial_source and sha(public_remote) == initial_public
    assert report(a)['status'].startswith('BLOCKED:')
    source_hook.unlink()
    checked('Source push rejection: no public push and no local HEAD movement')

    cli(a, 'publish', '--site', '--push')
    first = report(a)
    assert first['source_pushed'] and first['public_pushed']
    assert first['source_commit'] == sha(source_remote) == git(a, 'rev-parse', 'HEAD')
    assert json.loads(blob(public_remote, 'master', 'release.json'))['source_commit'] == sha(source_remote)
    for rel in first['archived_html']:
        assert blob(public_remote, 'master', rel) == blob(public_remote, initial_public, rel)
    assert blob(public_remote, 'master', 'CNAME') == b'blog.example.invalid\n'
    assert (Path(first['run']) / 'public/.git').is_dir()
    assert '.blog/' not in git(source_remote, 'ls-tree', '-r', '--name-only', 'master')
    checked('Local dual-repository bootstrap push: source/artifact SHA agree, CNAME and .git retained, archived HTML byte-identical')

    b = machine('laptop')
    title = '中文 "引号" : # & <script>测试'
    created = Path(cli(a, 'new', 'post', '--title', title, '--body', 'ONLY_SELECTED_POST').splitlines()[0])
    relative = created.relative_to(a).as_posix()
    untouched = Path(cli(a, 'new', 'moment', '--title', 'PRIVATE_DRAFT', '--body', 'DO_NOT_PUBLISH').splitlines()[0])
    private_bytes = untouched.read_bytes()
    cli(a, 'new', 'moment', '--title', 'bad-image', '--image', 'missing.jpg', expected=1)
    cli(a, 'new', 'post', '--title', ' ', expected=1)
    moment = Path(cli(a, 'new', 'moment', '--title', 'PHOTO_MOMENT', '--image', str(a / 'static/img/avatar.png')).splitlines()[0])
    moment_rel = moment.relative_to(a).as_posix()
    cli(a, 'publish', relative, moment_rel)
    assert b'draft: true' in created.read_bytes()
    assert b'draft: true' in moment.read_bytes()
    candidate = Path(report(a)['candidate'])
    assert (candidate / 'post' / created.parent.name / 'index.html').exists()
    assert (candidate / 'moments' / moment.parent.name / 'photo.png').read_bytes() == (a / 'static/img/avatar.png').read_bytes()
    assert not (candidate / 'moments' / untouched.parent.name).exists()
    checked('Selected Markdown + adjacent image dry-run; other private draft excluded; originals stay drafts; invalid input rejected')

    public_before = sha(public_remote)
    public_hook = public_remote / 'hooks/pre-receive'
    public_hook.write_text('#!/bin/sh\nexit 1\n', newline='\n')
    cli(a, 'publish', relative, moment_rel, '--push', expected=1)
    partial = report(a)
    assert partial['source_pushed'] and not partial['public_pushed']
    assert sha(public_remote) == public_before
    assert b'draft: false' in created.read_bytes() and untouched.read_bytes() == private_bytes
    published_source = sha(source_remote)
    public_hook.unlink()
    cli(a, 'publish', '--push')
    assert sha(source_remote) == published_source
    assert json.loads(blob(public_remote, 'master', 'release.json'))['source_commit'] == published_source
    checked('Public push failure/retry: source saved first, same source reused, fresh build, unrelated draft preserved')

    cli(b, 'sync')
    assert git(b, 'rev-parse', 'HEAD') == published_source
    assert (b / relative).read_bytes() == created.read_bytes()
    assert not (b / untouched.relative_to(a)).exists()
    checked('Second machine fast-forwards to published source including article and tooling, never downloads generated HTML into content')

    # Dirty/staged protections and a real source race between machines.
    laptop_article = b / relative
    laptop_article.write_bytes(laptop_article.read_bytes() + b'\nLAPTOP_UNSAVED\n')
    laptop_saved = laptop_article.read_bytes()
    cli(b, 'sync', expected=1)
    created.write_bytes(created.read_bytes() + b'\nDESKTOP_UPDATE\n')
    cli(a, 'publish', relative, '--push')
    cli(b, 'publish', relative, '--push', expected=1)
    assert laptop_article.read_bytes() == laptop_saved
    assert 'differs from latest remote' in report(b)['status']
    laptop_article.write_bytes(blob(source_remote, published_source, relative))
    cli(b, 'sync')
    assert b'DESKTOP_UPDATE' in laptop_article.read_bytes()
    laptop_article.write_bytes(laptop_article.read_bytes() + b'\nLOCAL_ONLY_COMMIT\n')
    git(b, 'add', relative)
    cli(b, 'publish', relative, '--push', expected=1)
    assert 'staged' in report(b)['status']
    git(b, 'commit', '-m', 'Local-only notebook commit')
    cli(b, 'sync', expected=1)
    cli(b, 'publish', relative, '--push', expected=1)
    checked('Dirty sync, stale source edits, staged index and local-only/divergent history all block without losing files')

    # No stale candidate can be reused after a compiler failure.
    baseline = (sha(source_remote), sha(public_remote))
    template = a / 'layouts/index.html'
    good_template = template.read_bytes()
    previous_candidate = report(a)['candidate']
    template.write_text('{{ THIS_IS_INVALID }}', encoding='utf-8')
    cli(a, 'publish', '--include', 'layouts/index.html', '--push', expected=1)
    assert (sha(source_remote), sha(public_remote)) == baseline
    assert report(a)['candidate'] != previous_candidate
    assert report(a)['status'].startswith('BLOCKED:')
    template.write_bytes(good_template)
    checked('Real Hugo failure overwrites success status, leaves both remotes unchanged, never publishes stale output')

    future = created.read_text(encoding='utf-8')
    created.write_text(future.replace('date: ', 'date: 2999-01-01 # ', 1), encoding='utf-8')
    cli(a, 'publish', relative, '--push', expected=1)
    assert (sha(source_remote), sha(public_remote)) == baseline
    created.write_text(future, encoding='utf-8')
    created.write_text(re.sub(r'(?m)^date:.*$', 'date: 2999-01-01T00:00:00Z', future), encoding='utf-8')
    cli(a, 'publish', relative, '--push', expected=1)
    assert (sha(source_remote), sha(public_remote)) == baseline
    created.write_text(future, encoding='utf-8')
    checked('Malformed/future selected article date is rejected before pushing')

    created.write_text(future.replace('draft: false', 'draft: true # preserve this draft'), encoding='utf-8')
    cli(a, 'publish', relative, '--push', expected=1)
    assert (sha(source_remote), sha(public_remote)) == baseline
    assert 'still a draft' in report(a)['status']
    created.write_text(future, encoding='utf-8')
    checked('Selected file must produce fresh non-draft HTML; archived old HTML cannot hide an unpublished manuscript')

    @contextmanager
    def test_environment():
        old = dict(os.environ)
        os.environ.update(env)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(old)

    # Crash after source push, before local reconciliation; exact journal recovery.
    crash = Path(cli(a, 'new', 'post', '--title', 'RECOVER_AFTER_SOURCE_PUSH').splitlines()[0])
    crash_rel = crash.relative_to(a).as_posix()
    opts = SimpleNamespace(files=[crash_rel], include=[], site=False, push=True)
    with test_environment(), patch.object(release, 'integrate_source', side_effect=RuntimeError('simulated crash after source push')):
        try:
            release.publish(a, opts)
            raise AssertionError('Crash was not injected')
        except RuntimeError as exc:
            assert 'simulated crash' in str(exc)
    assert report(a)['source_pushed'] and b'draft: true' in crash.read_bytes()
    cli(a, 'publish', crash_rel, '--push')
    assert report(a).get('recovered_source_push')
    assert b'draft: false' in crash.read_bytes()
    assert json.loads(blob(public_remote, 'master', 'release.json'))['source_commit'] == sha(source_remote)
    checked('Interrupted source-push journal resumes only from matching remote commit and unchanged manuscript')

    # A late public update must be detected and preserved, not overwritten.
    original_assemble = release.assemble
    public_prior = sha(public_remote)
    git(pub_seed, 'pull', '--ff-only')
    def race(*arguments, **kwargs):
        result = original_assemble(*arguments, **kwargs)
        (pub_seed / 'other-machine.txt').write_text('KEEP_THIS', encoding='utf-8')
        git(pub_seed, 'add', 'other-machine.txt')
        git(pub_seed, 'commit', '-m', 'Concurrent local publication')
        git(pub_seed, 'push', 'origin', 'master')
        return result
    with test_environment(), patch.object(release, 'assemble', side_effect=race):
        try:
            release.publish(a, SimpleNamespace(files=[], include=[], site=False, push=True))
            raise AssertionError('Race did not block')
        except release.PublishError as exc:
            assert 'remote branch moved' in str(exc)
    assert sha(public_remote) != public_prior
    cli(a, 'publish', '--push')
    assert blob(public_remote, 'master', 'other-machine.txt') == b'KEEP_THIS'
    checked('Concurrent public update blocks the stale attempt; retry includes latest baseline without force push')

    selected_before = crash.read_bytes()
    remote_before = (sha(source_remote), sha(public_remote))
    def editing_race(*arguments, **kwargs):
        result = original_assemble(*arguments, **kwargs)
        crash.write_bytes(selected_before + b'\nNEW_EDIT_DURING_BUILD\n')
        return result
    with test_environment(), patch.object(release, 'assemble', side_effect=editing_race):
        try:
            release.publish(a, SimpleNamespace(files=[crash_rel], include=[], site=False, push=True))
            raise AssertionError('Concurrent edit did not block')
        except release.PublishError as exc:
            assert 'selected file changed' in str(exc)
    assert (sha(source_remote), sha(public_remote)) == remote_before
    assert b'NEW_EDIT_DURING_BUILD' in crash.read_bytes()
    crash.write_bytes(selected_before)
    checked('Editing a selected manuscript during the build blocks both pushes and preserves the new edit')

    # Production-mode gate is checked before fetch. Git remains file-only here,
    # so even a regression cannot contact the production URLs in this fixture.
    local_test_root = env.pop('BLOG_LOCAL_TEST_ROOT')
    try:
        cli(a, 'publish', '--push', expected=1)
        assert 'First verify GitHub Pages' in report(a)['status']
    finally:
        env['BLOG_LOCAL_TEST_ROOT'] = local_test_root
    assert (sha(source_remote), sha(public_remote)) == remote_before
    checked('Production push is blocked before any remote access until Pages configuration is explicitly confirmed')

    # Test configuration must reject any nonlocal endpoint before any operation.
    test_config = a / '.blog/test-config.json'
    original_config = test_config.read_bytes()
    wrong = dict(config, public_push='https://github.com/should-never-be-contacted/repo.git')
    test_config.write_text(json.dumps(wrong))
    (a / 'build/prepare-report.json').write_text('{"status":"READY: old report","public_pushed":true}')
    cli(a, 'publish', '--push', expected=1)
    assert report(a)['status'].startswith('BLOCKED:') and not report(a)['public_pushed']
    test_config.write_bytes(original_config)
    checked('Test-mode endpoint validation + Git file-only protocol prevent real-remote access')

    result = {'status': 'PASS', 'simulation_only': True, 'real_remote_writes': False,
              'sandbox': str(sandbox), 'checks': checks,
              'source_commit': sha(source_remote), 'public_commit': sha(public_remote),
              'archived_html_count': len(first['archived_html'])}
    (ROOT / 'build/publish-test-report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
