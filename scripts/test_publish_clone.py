"""Regression: inherited Windows autocrlf must not change public archive bytes."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import publish

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'build').mkdir(exist_ok=True)
sandbox = Path(tempfile.mkdtemp(prefix='clone-eol-test-', dir=ROOT / 'build'))
env = dict(os.environ, GIT_ALLOW_PROTOCOL='file', GIT_CONFIG_GLOBAL=os.devnull,
           GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_COUNT='1',
           GIT_CONFIG_KEY_0='core.autocrlf', GIT_CONFIG_VALUE_0='true')
def git(repo, *args):
    return subprocess.check_output(['git','-c','core.autocrlf=false',*args],cwd=repo,env=env)
seed = sandbox / 'seed'
seed.mkdir()
git(seed,'init','-b','master')
git(seed,'config','user.name','Local test')
git(seed,'config','user.email','test@example.invalid')
files = {'old-lf.html':b'<p>archived LF</p>\n', 'old-crlf.html':b'<p>archived CRLF</p>\r\n',
         'mixed.txt':b'one\r\ntwo\nthree\r\n'}
for rel,data in files.items(): (seed / rel).write_bytes(data)
git(seed,'add','-A')
git(seed,'commit','-m','Local archive fixture')
bare = sandbox / 'public.git'
git(sandbox,'clone','--bare',str(seed),str(bare))
for testing in (False, True):
    target = sandbox / ('checkout-' + str(testing))
    publish.clone_public(sandbox,target,{'branch':'master','public_fetch':str(bare)},env,testing)
    for rel,data in files.items():
        assert (target / rel).read_bytes() == data, (testing, rel)
        assert git(target,'show','HEAD:' + rel) == data
    assert not git(target,'diff','--name-only').strip()
result = {'status':'PASS','real_remote_access':False,'inherited_autocrlf':True,
          'both_clone_modes_preserve_exact_archive_bytes':True,'fixture':str(sandbox)}
(ROOT / 'build/clone-eol-test-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
