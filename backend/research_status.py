import time
from collections import Counter
from sqlalchemy import select,func
from database.models import Record,FuturesMarket
from backend.learning import snapshot as learning
from backend.futures_paper import config

def status(db,owner):
    rows=list(db.scalars(select(Record).where(Record.user_id==owner).order_by(Record.created.desc()).limit(250)))
    decisions=[r.payload for r in rows if r.kind=='decision']
    scans=next((r for r in rows if r.kind=='scan_summary'),None)
    counts=Counter(d.get('execution','not_requested') for d in decisions)
    blocks=Counter(d.get('execution_reason',d.get('reason','Unknown')) for d in decisions if d.get('execution')!='filled')
    return {'profile':config(db,owner).limits.get('profile','balanced'),
            'catalogue_count':db.scalar(select(func.count()).select_from(FuturesMarket).where(FuturesMarket.contract['state'].as_integer()==0)),
            'fresh_markets':db.scalar(select(func.count()).select_from(FuturesMarket).where(FuturesMarket.received>time.time()-15)),
            'scan':scans.payload if scans else None,'last_scan_at':scans.created if scans else None,
            'recent_evaluations':len(decisions),'entry_results':dict(counts),
            'top_wait_reasons':[{'reason':r,'count':n} for r,n in blocks.most_common(5)],
            'candidates':decisions[:12],'learning':learning(db,owner),'paper':True,'live_promotion':False}
