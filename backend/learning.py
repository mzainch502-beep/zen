"""Reproducible, bounded learning from completed simulated exposures."""
from decimal import Decimal
from sqlalchemy import select
from database.models import Record,record
from research.adaptive import outcomes,VERSION

def history(db,owner):
    entries=db.scalars(select(Record).where(Record.user_id==owner,Record.kind=='paper_learning_outcome').order_by(Record.created.desc()).limit(250)).all()
    return [e.payload for e in entries]

def snapshot(db,owner):
    rows=history(db,owner);weights=outcomes(rows)
    changes=db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='learning_update').order_by(Record.created.desc()).limit(1))
    return {'version':VERSION,'samples':len(rows),'weights':weights,'net':str(sum((Decimal(str(r['net'])) for r in rows),Decimal(0))),
            'status':'collecting outcomes' if len(rows)<5 else 'bounded paper adaptation',
            'last_change':changes.payload if changes else None,'calibration':None,
            'notice':'Updates can improve or worsen results. Live promotion and predictive accuracy are not established.'}

def completed(db,owner,position_id,context):
    if not context.get('strategy') or context.get('strategy')=='manual':return
    db.flush()
    if db.scalar(select(Record).where(Record.user_id==owner,Record.kind=='paper_learning_outcome',Record.payload['position_id'].as_string()==position_id)):return
    rows=list(db.scalars(select(Record).where(Record.user_id==owner,Record.kind.in_(['trade_evaluation','spot_realized']),Record.payload['position_id'].as_string()==position_id)))
    from decimal import Decimal
    net=sum((Decimal(str(r.payload['round_trip_net'])) for r in rows if 'round_trip_net' in r.payload),Decimal(0))
    payload={'position_id':position_id,'strategy':context['strategy'],'regime':context.get('regime','unknown'),
             'net':str(net),'initial_risk':context.get('initial_risk','0'),'completed':True,'closed_at':max(r.created for r in rows),'paper':True,'version':VERSION}
    before=snapshot(db,owner)['weights'];record(db,owner,'paper_learning_outcome',payload);db.flush()
    after=snapshot(db,owner)['weights']
    record(db,owner,'learning_update',{'version':VERSION,'position_id':position_id,'before':before,'after':after,'reason':'Completed exposure net outcome after both-side fees; weights bounded at ±0.25','paper':True})
