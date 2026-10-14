"""Small double-click writing menu; publishing still uses the tested CLI."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import tomllib
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = None
PREVIEW_PORT = None
PREVIEW_LOG = None


def run_cli(*args, capture=False):
    return subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts/blog.py'), *args],
                          cwd=ROOT, text=True, encoding='utf-8', capture_output=capture)


def safe_article(path):
    path = Path(path).resolve()
    relative = path.relative_to((ROOT / 'content/zh-CN').resolve())
    if relative.parts[0] not in ('post', 'moments') or path.suffix != '.md' or path.name == '_index.md' or not path.is_file():
        raise ValueError('请选择一篇长文章或短动态的 Markdown 文件。')
    return path


def select(path):
    path = safe_article(path)
    state = ROOT / '.blog/writer-state.json'
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({'selected':path.relative_to(ROOT).as_posix()}, ensure_ascii=False), encoding='utf-8')
    return path


def current():
    try:
        state = json.loads((ROOT / '.blog/writer-state.json').read_text(encoding='utf-8'))
        return safe_article(ROOT / state['selected'])
    except (OSError, ValueError, KeyError, IndexError):
        return None


def info(path):
    text = path.read_text(encoding='utf-8-sig')
    title, draft, date = path.stem, False, ''
    if text.startswith('+++'):
        try:
            front = tomllib.loads(text.split('+++', 2)[1])
            return str(front.get('title', title)), bool(front.get('draft', False)), str(front.get('date', ''))
        except (ValueError, IndexError):
            pass
    elif text.startswith('---'):
        front = text.split('---', 2)[1]
        for line in front.splitlines():
            key, sep, value = line.partition(':')
            if not sep: continue
            value = value.strip()
            if key == 'title':
                try: title = json.loads(value)
                except ValueError: title = value.strip("'\"")
            elif key == 'draft': draft = value.split('#', 1)[0].strip().lower() == 'true'
            elif key == 'date': date = value.strip("'\"")
    return str(title), draft, date


def open_editor(path):
    try:
        os.startfile(str(path))
    except OSError:
        subprocess.Popen(['notepad.exe', str(path)])


def create(kind):
    title = input('标题（回车取消）：').strip()
    if not title: return None
    photo = input('可选配图：把图片拖到这里；没有就直接回车：').strip().strip('"')
    args = ['new', kind, '--title', title]
    if photo: args.extend(['--image', photo])
    result = run_cli(*args, capture=True)
    if result.returncode:
        print(result.stderr or result.stdout)
        return None
    path = select(result.stdout.splitlines()[0])
    print('草稿已创建并打开。写好保存后，回到这里选 4 预览、5 发布。')
    open_editor(path)
    return path


def choose():
    query = input('搜索标题（回车显示最近 20 篇）：').strip().casefold()
    articles = []
    for section in ('post', 'moments'):
        for path in (ROOT / 'content/zh-CN' / section).rglob('*.md'):
            if path.name == '_index.md': continue
            title, draft, date = info(path)
            if not query or query in title.casefold():
                articles.append((path, title, draft, date))
    articles.sort(key=lambda item:(item[3],item[0].stat().st_mtime), reverse=True)
    if not query: articles = articles[:20]
    if not articles:
        print('没有找到文章。'); return None
    for number, (_, title, draft, _) in enumerate(articles, 1):
        print(f'{number:>2}. {"[草稿] " if draft else ""}{title}')
    answer = input('输入序号打开（回车取消）：').strip()
    if not answer: return None
    if not answer.isdecimal() or not 1 <= int(answer) <= len(articles):
        print('序号无效，没有修改任何稿件。'); return None
    path = select(articles[int(answer)-1][0])
    open_editor(path)
    return path


def publish_current():
    path = current()
    if path is None:
        print('请先新建或选择一篇稿件。'); return False
    title = info(path)[0]
    print(f'\n准备检查《{title}》。仅发布这篇稿件及同目录图片。')
    print('请先在编辑器中保存文件。')
    relative = path.relative_to(ROOT).as_posix()
    if run_cli('publish', relative).returncode:
        print('检查未通过，没有上线。原稿保留，请按上面的提示处理。')
        return False
    report = json.loads((ROOT / 'build/prepare-report.json').read_text(encoding='utf-8'))
    print('\n此次选中的文件：')
    for name in report['selected']: print('  ' + name)
    if input('\n输入“发布”才真正上线（回车取消）：').strip() != '发布':
        print('已取消，仅完成检查，没有上线。'); return False
    ok = run_cli('publish', relative, '--push').returncode == 0
    if ok:
        print('源码和网页已推送。Pages 更新通常还需要一点时间。')
        print('网站：https://blog.shadiao.win/')
    else:
        print('没有完成发布，请保留稿件并查看上面的错误及 build/prepare-report.json。')
    return ok


def preview():
    global PREVIEW, PREVIEW_PORT, PREVIEW_LOG
    if PREVIEW is not None and PREVIEW.poll() is None:
        webbrowser.open(f'http://localhost:{PREVIEW_PORT}/')
        return PREVIEW_PORT
    executable = shutil.which('hugo')
    if not executable: raise RuntimeError('没有找到 Hugo；请使用原来已配置好的写作电脑。')
    for port in range(1313, 1324):
        try:
            with socket.socket() as probe: probe.bind(('127.0.0.1', port))
        except OSError: continue
        PREVIEW_PORT = port
        break
    else: raise RuntimeError('本地预览端口正在使用，请先关闭不再需要的预览。')
    (ROOT / '.blog').mkdir(exist_ok=True)
    PREVIEW_LOG = (ROOT / '.blog/writer-preview.log').open('w', encoding='utf-8')
    PREVIEW = subprocess.Popen([executable, 'server', '--source', str(ROOT), '--bind', '127.0.0.1',
        '--port', str(PREVIEW_PORT), '--baseURL', f'http://localhost:{PREVIEW_PORT}/',
        '--buildDrafts', '--buildFuture', '--destination', str(ROOT / 'build/preview'), '--disableFastRender'],
        cwd=ROOT, stdout=PREVIEW_LOG, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    for _ in range(60):
        if PREVIEW.poll() is not None: break
        try:
            with urllib.request.urlopen(f'http://localhost:{PREVIEW_PORT}/', timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(f'http://localhost:{PREVIEW_PORT}/')
                    print(f'预览已打开：http://localhost:{PREVIEW_PORT}/。预览期间保持此窗口打开。')
                    return PREVIEW_PORT
        except OSError: time.sleep(.2)
    close_preview()
    raise RuntimeError('预览未能启动，详见 .blog/writer-preview.log。')


def close_preview():
    global PREVIEW, PREVIEW_LOG
    if PREVIEW is not None and PREVIEW.poll() is None:
        PREVIEW.terminate()
        try: PREVIEW.wait(timeout=5)
        except subprocess.TimeoutExpired: PREVIEW.kill(); PREVIEW.wait()
    PREVIEW = None
    if PREVIEW_LOG is not None: PREVIEW_LOG.close(); PREVIEW_LOG = None


def main():
    print('沙雕园 · 写博客\n文稿和设置都保存在：' + str(ROOT))
    try:
        while True:
            path = current()
            print('\n当前稿件：' + (info(path)[0] if path else '尚未选择'))
            print('1 新建长文章    2 新建短动态    3 选择/打开已有稿件')
            print('4 本地预览      5 发布当前稿件  6 写作前同步')
            print('7 打开文稿文件夹               0 退出')
            choice = input('请选择：').strip()
            try:
                if choice == '0': break
                elif choice == '1': create('post')
                elif choice == '2': create('moment')
                elif choice == '3': choose()
                elif choice == '4': preview()
                elif choice == '5': publish_current()
                elif choice == '6':
                    print('只同步干净工作区；已有未发布改动时会停下，不自动覆盖。')
                    run_cli('sync')
                elif choice == '7': os.startfile(str(ROOT / 'content/zh-CN'))
                else: print('请输入 0～7。')
            except (OSError, ValueError, RuntimeError) as exc:
                print('操作未完成：' + str(exc))
    except (KeyboardInterrupt, EOFError):
        print('\n已退出。')
    finally:
        close_preview()


if __name__ == '__main__':
    main()
