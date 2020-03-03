from database import *

"""
from sqlalchemy.sql import func

#result = db.session.query(func.sum(Attempt.marks).label("sum")).filter_by(userid=1)
result = Attempt.query.with_entities(func.sum(Attempt.marks).label("sum")).filter_by(userid=1).first()[0]
print(type(result))
#db.session.query(Attempt).filter_by(userid=1).count()

attempts = db.session.query(Vote, Attempt).join(Attempt, Vote.attemptid == Attempt.attemptid).filter(Attempt.userid==1)
print(attempts.filter(Vote.islike==True).count())
print(attempts.filter(Vote.isdislike==True).count())
print(attempts.filter(Vote.isreport==True).count())
"""