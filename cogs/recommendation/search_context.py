from pyrebase.pyrebase import Database
from typing import Dict


def get_search_context(db: Database, user):
    return db.child("contexts").child(str(user.id)).get()


def set_search_context(db: Database, user, ctx: Dict):
    db.child("contexts").child(str(user.id)).set(ctx)


def clear_search_context(db: Database, user):
    db.child("contexts").child(str(user.id)).remove()
