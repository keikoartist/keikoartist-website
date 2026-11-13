#!/usr/bin/env python3
"""Upload the website to Rumahweb over FTP (replaces SamKirkland/FTP-Deploy-Action).

- Uploads only files that changed since the last deploy (sha256 list kept in
  .deploy-state.json on the server). The first run uploads everything once.
- Only touches files tracked in this repo. Files that exist only on the server
  (keikoarts-config.php, chat-data/, .htaccess, old WordPress files, ...) are
  never read, overwritten or deleted.
- A file is deleted on the server only if a previous run of this script
  uploaded it and it has since been removed from the repo.
- Every file upload retries with a fresh connection, so one slow moment on the
  shared host does not fail the whole deploy.
Env: FTP_SERVER, FTP_USERNAME, FTP_PASSWORD, FTP_DIR (default public_html/).
"""
import ftplib, hashlib, io, json, os, posixpath, subprocess, sys, time

STATE = '.deploy-state.json'
EXCLUDE_PREFIX = ('.github/', 'docs/', 'tools/')
EXCLUDE_FILES = {'README.md', '.gitignore', '.gitattributes'}

HOST = os.environ['FTP_SERVER']
USER = os.environ['FTP_USERNAME']
PWD = os.environ['FTP_PASSWORD']
ROOT = (os.environ.get('FTP_DIR') or 'public_html/').strip()
PORT = int(os.environ.get('FTP_PORT') or 21)


def tracked_files():
    out = subprocess.run(['git', 'ls-files', '-z'], capture_output=True, check=True).stdout
    files = [f.decode() for f in out.split(b'\0') if f]
    return sorted(f for f in files
                  if not f.startswith(EXCLUDE_PREFIX) and f not in EXCLUDE_FILES
                  and not posixpath.basename(f).startswith('.git') and os.path.isfile(f))


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


class Conn:
    def __init__(self):
        self.ftp = None
        self.made = set()

    def get(self):
        if self.ftp is None:
            f = ftplib.FTP(timeout=90)
            f.connect(HOST, PORT)
            f.login(USER, PWD)
            f.set_pasv(True)
            f.cwd(ROOT)
            self.ftp = f
        return self.ftp

    def drop(self):
        try:
            if self.ftp: self.ftp.close()
        except Exception:
            pass
        self.ftp = None

    def do(self, what, fn, tries=4):
        for i in range(tries):
            try:
                return fn(self.get())
            except ftplib.error_perm:
                raise
            except Exception as e:
                self.drop()
                if i == tries - 1:
                    raise
                wait = 10 * (i + 1)
                print(f'  retry {what} in {wait}s ({type(e).__name__}: {str(e)[:80]})', flush=True)
                time.sleep(wait)

    def mkdirs(self, d):
        parts = [p for p in d.split('/') if p]
        for i in range(1, len(parts) + 1):
            sub = '/'.join(parts[:i])
            if sub in self.made:
                continue
            def mk(f, sub=sub):
                try:
                    f.mkd(sub)
                except ftplib.error_perm:
                    pass  # already exists
            self.do('mkdir ' + sub, mk)
            self.made.add(sub)


def main():
    files = tracked_files()
    local = {f: sha(f) for f in files}
    c = Conn()

    buf = io.BytesIO()
    try:
        c.do('read state', lambda f: f.retrbinary('RETR ' + STATE, buf.write))
        old = json.loads(buf.getvalue() or b'{}').get('files', {})
    except ftplib.error_perm as e:
        if not str(e).startswith('550'):
            raise  # e.g. 530 wrong login: stop instead of re-uploading everything
        old = {}
    except ValueError:
        old = {}
    print(f'{len(files)} files in repo, {len(old)} in last deploy state', flush=True)

    changed = [f for f in files if old.get(f) != local[f]]
    removed = [f for f in old if f not in local]
    print(f'{len(changed)} to upload, {len(removed)} to delete', flush=True)

    t0 = time.time()
    for n, f in enumerate(changed, 1):
        d = posixpath.dirname(f)
        if d:
            c.mkdirs(d)
        def up(ftp, f=f):
            with open(f, 'rb') as fh:
                ftp.storbinary('STOR ' + f, fh)
        c.do('upload ' + f, up)
        print(f'  [{n}/{len(changed)}] {f} ({os.path.getsize(f) // 1024} KB)', flush=True)

    for f in removed:
        try:
            c.do('delete ' + f, lambda ftp, f=f: ftp.delete(f))
            print('  deleted ' + f, flush=True)
        except ftplib.error_perm as e:
            print(f'  (skip delete {f}: {str(e)[:60]})', flush=True)

    if changed or removed or not old:
        state = json.dumps({'note': 'written by tools/ftp_deploy.py', 'commit': os.environ.get('GITHUB_SHA', ''),
                            'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'files': local},
                           indent=0, sort_keys=True).encode()
        c.do('write state', lambda ftp: ftp.storbinary('STOR ' + STATE, io.BytesIO(state)))
    c.drop()
    print(f'Done in {time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'::error::FTP deploy failed: {type(e).__name__}: {str(e)[:200]}', flush=True)
        sys.exit(1)
