"""Owner-controlled entry automation. Disabling never disables protective exits."""
from backend.domain import Limits
from backend.futures_domain import FuturesLimits
from backend.futures_paper import config
from database.models import record


def status(db, user):
    cfg = config(db, user.id)
    futures = cfg.workspace in ['futures','combined']
    live = bool(cfg.activated) or user.mode == 'Live'
    requested = FuturesLimits.model_validate(cfg.limits).automatic if futures else Limits.model_validate(user.limits).automatic
    blocked = 'Live strategy promotion and private execution validation are pending' if live else 'Emergency stop is active' if user.mode == 'Emergency Stop' else 'Workspace is paused' if user.mode == 'Paused' else None
    return {'enabled': bool(requested and not blocked), 'requested': requested,
            'can_enable': blocked is None, 'blocked_reason': blocked,
            'product': cfg.workspace, 'mode': 'Live' if live else 'Paper',
            'research_trial': True, 'exits_remain_active': True}


def change(db, user, enabled):
    before = status(db, user)
    if enabled and not before['can_enable']:
        raise ValueError(before['blocked_reason'])
    cfg = config(db, user.id)
    # Keep a single switch for the active workspace; old settings cannot leave a
    # dormant workspace armed after a switch. All changes hold the owner lock.
    spot = Limits.model_validate(user.limits).model_dump(mode='json')
    future = FuturesLimits.model_validate(cfg.limits).model_dump(mode='json')
    spot['automatic'] = bool(enabled and cfg.workspace in ['spot','combined'])
    future['automatic'] = bool(enabled and cfg.workspace in ['futures','combined'])
    user.limits = spot
    cfg.limits = future
    after = status(db, user)
    if before != after:
        record(db, user.id, 'automation_changed', after)
    return after
