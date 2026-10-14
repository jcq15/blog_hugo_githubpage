"""Local menu tests. Actual publishing is mocked; no sample is uploaded."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import writer

ROOT = Path(__file__).resolve().parents[1]


def main():
    (ROOT / 'build').mkdir(exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix='writer-test-', dir=ROOT / 'build'))
    (fixture / 'scripts').mkdir()
    for name in ('blog.py','publish.py'):
        shutil.copy2(ROOT / 'scripts' / name, fixture / 'scripts' / name)
    for section in ('post','moments'):
        (fixture / 'content/zh-CN' / section).mkdir(parents=True)
    checks = []
    original_root = writer.ROOT
    writer.ROOT = fixture
    quiet = io.StringIO()
    try:
        with redirect_stdout(quiet), patch('builtins.input', side_effect=['菜单测试长文','']), patch.object(writer, 'open_editor') as editor:
            article = writer.create('post')
            editor.assert_called_once_with(article)
        assert article.is_file() and 'draft: true' in article.read_text(encoding='utf-8')
        assert writer.current() == article
        checks.append('Real draft creation + remembered selection + editor action (editor mocked)')

        with redirect_stdout(quiet), patch('builtins.input', side_effect=['菜单测试图片',str(ROOT / 'static/img/avatar.png')]), patch.object(writer, 'open_editor'):
            moment = writer.create('moment')
        assert (moment.parent / 'photo.png').read_bytes() == (ROOT / 'static/img/avatar.png').read_bytes()
        assert writer.info(moment)[0] == '菜单测试图片'
        checks.append('Real short-moment creation with local image; files stay inside fixture')

        with redirect_stdout(quiet), patch('builtins.input', side_effect=['菜单测试长文','1']), patch.object(writer,'open_editor'):
            assert writer.choose() == article
        checks.append('Search and select an existing manuscript')

        calls = []
        def fake_cli(*args, capture=False):
            calls.append(args)
            (fixture / 'build').mkdir(exist_ok=True)
            (fixture / 'build/prepare-report.json').write_text(json.dumps({'selected':[article.relative_to(fixture).as_posix()]}))
            return SimpleNamespace(returncode=0)
        with redirect_stdout(quiet), patch.object(writer,'run_cli',side_effect=fake_cli), patch('builtins.input',return_value=''):
            assert not writer.publish_current()
        assert len(calls) == 1 and '--push' not in calls[0]
        checks.append('Cancel after dry-run: no push command')
        calls.clear()
        with redirect_stdout(quiet), patch.object(writer,'run_cli',side_effect=fake_cli), patch('builtins.input',return_value='发布'):
            assert writer.publish_current()
        assert len(calls) == 2 and '--push' in calls[1]
        assert calls[1][1] == article.relative_to(fixture).as_posix()
        checks.append('Explicit confirmation selects only current manuscript; actual push mocked')
        with redirect_stdout(quiet), patch.object(writer,'run_cli',return_value=SimpleNamespace(returncode=1)) as command, patch('builtins.input') as prompt:
            assert not writer.publish_current()
            assert command.call_count == 1 and not prompt.called
        checks.append('Failed dry-run never asks to push or executes push')
        try:
            writer.select(ROOT / 'content/zh-CN/post/AImath.md')
            raise AssertionError('Outside path accepted')
        except ValueError:
            pass
        checks.append('Selection cannot escape the source content directory')
    finally:
        writer.ROOT = original_root

    with patch.object(writer.webbrowser,'open') as browser, redirect_stdout(quiet):
        try:
            port = writer.preview()
            assert 1313 <= port < 1324
            assert writer.preview() == port
            assert browser.call_count == 2
        finally:
            writer.close_preview()
    assert writer.PREVIEW is None
    checks.append('Real desktop Hugo preview starts on free port, reuses its own process, then closes only that process')

    launcher = subprocess.run(['cmd.exe','/d','/c',str(ROOT / 'write-blog.cmd')], cwd=ROOT,
                              input='0\n',capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert launcher.returncode == 0, launcher.stderr
    assert '新建长文章' in launcher.stdout
    checks.append('Double-click command launcher enters menu and exits cleanly')
    report = {'status':'PASS','sample_published':False,'real_push_executed':False,'checks':checks,'fixture':str(fixture)}
    (ROOT / 'build/writer-test-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
