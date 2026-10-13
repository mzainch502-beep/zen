"""Untrusted public headline metadata. Never an order authority."""
import asyncio,time,re,email.utils
from urllib.parse import urlparse
import httpx
from defusedxml.ElementTree import fromstring
from sqlalchemy import select
from database.models import Record,record
from backend.security import digest
SOURCES=[('Federal Reserve','https://www.federalreserve.gov/feeds/press_all.xml',('federalreserve.gov',)),('BBC World','https://feeds.bbci.co.uk/news/world/rss.xml',('bbc.com','bbc.co.uk'))]

def parse_feed(raw,source,domains):
    if len(raw)>524288:raise ValueError('Feed exceeds size bound')
    root=fromstring(raw);events=[]
    for item in root.findall('.//item')[:20]:
        title=(item.findtext('title') or '').strip()[:200];url=(item.findtext('link') or '').strip()
        parsed=urlparse(url);host=parsed.hostname or ''
        if not title or parsed.scheme!='https' or not any(host==d or host.endswith('.'+d) for d in domains):continue
        try:published=email.utils.parsedate_to_datetime(item.findtext('pubDate') or '').timestamp()
        except (ValueError,TypeError):published=None
        review=bool(re.search(r'\b(inflation|interest rates?|war|sanctions|attack|monetary policy)\b',title,re.I))
        events.append({'source':source,'title':title,'url':url,'published':published,'review_flag':review,'event_id':digest(source+url+title),
            'trust':'Publisher metadata; headline content is untrusted','authority':'Research context only'})
    return events

def snapshot(db):
    rows=db.scalars(select(Record).where(Record.kind=='context_event').order_by(Record.created.desc()).limit(40)).all()
    sources=[]
    for name,_,_ in SOURCES:
        state=db.scalar(select(Record).where(Record.kind=='context_source',Record.payload['source'].as_string()==name).order_by(Record.created.desc()).limit(1))
        sources.append({'source':name,'state':state.payload if state else {'available':False,'reason':'First poll pending'},'received':state.created if state else None})
    return {'events':[r.payload for r in rows],'sources':sources,'notice':'Limited monitored sources; no claim of comprehensive geopolitical coverage'}

async def run(db):
    async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
        while True:
            for name,url,domains in SOURCES:
                try:
                    async with client.stream('GET',url) as response:
                        response.raise_for_status();raw=b''
                        async for chunk in response.aiter_bytes():
                            raw+=chunk
                            if len(raw)>524288:raise ValueError('Feed exceeds size bound')
                    events=parse_feed(raw,name,domains)
                    with db.sessions() as s:
                        for e in events:
                            if not s.scalar(select(Record).where(Record.kind=='context_event',Record.payload['event_id'].as_string()==e['event_id'])):record(s,None,'context_event',e)
                        record(s,None,'context_source',{'source':name,'available':True,'items':len(events)});s.commit()
                except Exception as e:
                    with db.sessions() as s:record(s,None,'context_source',{'source':name,'available':False,'error_type':type(e).__name__});s.commit()
            await asyncio.sleep(900)
