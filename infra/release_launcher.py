"""Pinned-source launcher for a public Python image when repo integration is unavailable.

SOURCE_COMMIT and SOURCE_SHA256 are deployment settings, not credentials. No mutable
branch is executed. API and worker share PostgreSQL, not the container filesystem.
"""
import hashlib, io, os, pathlib, subprocess, sys, time, urllib.request, zipfile

def launch():
    commit=os.environ['SOURCE_COMMIT']
    expected=os.environ['SOURCE_SHA256']
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit): raise ValueError('Invalid source commit')
    url='https://codeload.github.com/mzainch502-beep/zen/zip/'+commit
    raw=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=30) as response: raw=response.read(20_000_001)
            break
        except OSError:
            if attempt==2: raise
            time.sleep(2**attempt)
    if not raw or len(raw)>20_000_000: raise ValueError('Invalid release archive size')
    if hashlib.sha256(raw).hexdigest()!=expected: raise ValueError('Release integrity mismatch')
    target=pathlib.Path('/tmp/zen-release')
    target.mkdir(mode=0o755,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names=archive.namelist()
        if any(pathlib.PurePosixPath(name).is_absolute() or '..' in pathlib.PurePosixPath(name).parts for name in names): raise ValueError('Unsafe archive path')
        roots={name.split('/')[0] for name in names}
        if len(roots)!=1: raise ValueError('Unexpected archive layout')
        archive.extractall(target)
    app=target/roots.pop()
    os.chdir(app)
    subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--no-cache-dir','-r','requirements.txt'],check=True)
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    os.environ['PYTHONUNBUFFERED']='1'
    if os.getuid()==0:
        os.setgid(10001)
        os.setuid(10001)
    print('Starting verified ZEN release '+commit,flush=True)
    if os.environ.get('ZEN_PROCESS')=='worker':
        os.execv(sys.executable,[sys.executable,'-m','backend.worker'])
    else:
        subprocess.run([sys.executable,'-m','alembic','-c','database/alembic.ini','upgrade','head'],check=True)
        os.execv(sys.executable,[sys.executable,'-m','uvicorn','backend.api:app','--host','0.0.0.0','--port',os.getenv('PORT','8080')])
if __name__=='__main__':launch()
