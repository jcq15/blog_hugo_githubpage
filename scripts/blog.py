"""Write/preview locally; publishing defaults to a dry run, --push is explicit."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import publish as release

ROOT = Path(__file__).resolve().parents[1]

def hugo(*args):
    exe = shutil.which('hugo')
    if not exe:
        raise RuntimeError('Hugo not found. Add Hugo to PATH first.')
    subprocess.run([exe, *args], cwd=ROOT, check=True)

def create(args):
    if not args.title.strip():
        raise RuntimeError('Title must not be empty.')
    now = dt.datetime.now(dt.timezone.utc)
    slug = now.strftime('%Y%m%d-%H%M%S') + '-' + hashlib.sha256(args.title.encode()).hexdigest()[:6]
    section = 'post' if args.kind == 'post' else 'moments'
    folder = ROOT / 'content' / 'zh-CN' / section / slug
    folder.mkdir(parents=True, exist_ok=False)
    body = args.body or ('从这里开始写。' if section == 'post' else '记下一点今天的事。')
    if args.image:
        source = Path(args.image).resolve()
        if not source.is_file() or source.suffix.lower() not in {'.jpg','.jpeg','.png','.webp','.gif'}:
            folder.rmdir()
            raise RuntimeError('Image must be an existing jpg/png/webp/gif file.')
        target = folder / ('photo' + source.suffix.lower())
        shutil.copy2(source, target)
        body += '\n\n![照片](./' + target.name + ')'
    text = '---\ntitle: ' + json.dumps(args.title, ensure_ascii=False) + '\ndate: ' + now.isoformat() + '\ndraft: true\n---\n\n' + body + '\n'
    path = folder / 'index.md'
    path.write_text(text, encoding='utf-8')
    print(path)
    print('Draft created. Preview includes drafts. Publish dry run: python scripts/blog.py publish "' + str(path.relative_to(ROOT)) + '"')

def ready(args):
    path = (ROOT / args.file).resolve()
    path.relative_to((ROOT / 'content' / 'zh-CN').resolve())
    if path.suffix != '.md':
        raise RuntimeError('Choose a Markdown file under content/zh-CN.')
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise RuntimeError('This command supports drafts created with the new command.')
    front, body = text[4:].split('\n---\n', 1)
    if not re.search(r'^draft: true$', front, re.M):
        raise RuntimeError('This file is not an unpublished draft.')
    front = re.sub(r'^draft: true$', 'draft: false', front, flags=re.M)
    path.write_text('---\n' + front + '\n---\n' + body, encoding='utf-8')
    print('Marked ready locally; nothing was uploaded:', path)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    new = sub.add_parser('new', help='Create Markdown with automatic metadata')
    new.add_argument('kind', choices=['post','moment'])
    new.add_argument('--title', required=True)
    new.add_argument('--body')
    new.add_argument('--image')
    draft = sub.add_parser('ready', help='Mark one draft ready locally, without uploading')
    draft.add_argument('file')
    preview = sub.add_parser('preview', help='Local preview, including drafts')
    preview.add_argument('--port', type=int, default=1313)
    for name in ('prepare', 'publish'):
        publication = sub.add_parser(name, help='Build selected source; dry run unless --push')
        publication.add_argument('files', nargs='*', help='Markdown paths to mark ready and publish, including bundle images')
        publication.add_argument('--site', action='store_true', help='Include the reviewed first-release file manifest')
        publication.add_argument('--include', action='append', default=[], help='One additional explicit source file (repeatable)')
        if name == 'publish':
            publication.add_argument('--push', action='store_true', help='Actually push source, then public; requires setup confirmation')
        else:
            publication.set_defaults(push=False)
    sub.add_parser('sync', help='Fast-forward a clean source workspace from the configured source remote')
    setup = sub.add_parser('setup', help='Initialize only the theme; display targets; never publish')
    setup.add_argument('--confirm-pages', choices=['master:/'], help='Record your verification of GitHub Pages branch/folder')
    args = parser.parse_args()
    if args.action == 'new': create(args)
    elif args.action == 'ready': ready(args)
    elif args.action in ('prepare', 'publish'): release.publish(ROOT, args)
    elif args.action == 'sync': release.sync(ROOT)
    elif args.action == 'setup': release.setup(ROOT, args)
    else: hugo('server', '--bind', '127.0.0.1', '--port', str(args.port), '--baseURL', 'http://localhost:' + str(args.port) + '/', '--buildDrafts', '--buildFuture', '--destination', 'build/preview', '--disableFastRender')

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        raise SystemExit(1)
