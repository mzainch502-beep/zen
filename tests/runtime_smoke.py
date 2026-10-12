"""Opt-in real process/market-worker smoke check, isolated temporary database."""
import json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from sqlalchemy import select
from database.models import Database, Market

def main():
    with tempfile.TemporaryDirectory() as tmp:
        url='sqlite:///'+str(Path(tmp)/'runtime.db');db=Database(url);db.create_dev()
        env={**os.environ,'DATABASE_URL':url,'MARKET_EXCHANGE':'bitget'}
        api=subprocess.Popen([sys.executable,'-m','uvicorn','backend.api:app','--host','127.0.0.1','--port','8097'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        worker=subprocess.Popen([sys.executable,'-m','backend.worker'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            result=None
            for _ in range(125):
                if api.poll() is not None or worker.poll() is not None:raise RuntimeError('Runtime process exited')
                try:
                    health=json.load(urllib.request.urlopen('http://127.0.0.1:8097/health',timeout=2))
                    with db.sessions() as s: symbols=[m.symbol for m in s.scalars(select(Market))]
                    if health['worker_online'] and len(symbols)==3:
                        result={'health':health,'symbols':symbols,'cloud_deployed':False,'test':'independent server and worker processes with real public data'};break
                except (OSError,ValueError):pass
                time.sleep(.2)
            if result is None:raise RuntimeError('Worker did not ingest all real market quotes')
            Path('docs/runtime-smoke.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
        finally:
            for proc in [api,worker]:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':main()
