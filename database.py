from flask import Flask, session
import datetime, socket
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, desc
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy import tuple_
import sqlalchemy.orm.exc as sqlerrors
import sqlalchemy.exc as sqlerrors2

app = Flask(__name__)
app.secret_key = b"?"
url = "???"
app.config["SQLALCHEMY_POOL_RECYCLE"] = 280
app.config["SQLALCHEMY_DATABASE_URI"] = url
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = "users"
    userid = db.Column(db.Integer, primary_key=True)
    isadmin = db.Column(db.Boolean, nullable=False, default=False)
    isbanned = db.Column(db.Boolean, nullable=False, default=False)
    banreason = db.Column(db.String(280))
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(93), nullable=False)
    timesignedup = db.Column(db.DateTime, default=datetime.datetime.utcnow)

def getuser():
    if "sessionid" in session:
        try:
            usersession = Session.query.filter_by(sessionid=session["sessionid"]).one()
            return usersession.user
        except sqlerrors.NoResultFound:
            pass
    return None

def getuserid():
    return getuser().userid

class Session(db.Model):
    __tablename__ = "sessions"
    sessionid = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False, default=getuserid)
    timeloggedin = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship(User)

class Question(db.Model):
    __tablename__ = "questions"
    questionid = db.Column(db.Integer, nullable=False, primary_key=True)
    revisionid = db.Column(db.Integer, nullable=False, default=1, primary_key=True)
    previousrevisionid = db.Column(db.Integer, nullable=False, default=1)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False, default=getuserid)
    timestampadded = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    isverified = db.Column(db.Boolean, nullable=False, default=False)

class LockedFromEditing(db.Model):
    __tablename__ = "lockedquestions"
    questionid = db.Column(db.Integer, nullable=False, primary_key=True)
    lockedfromediting = db.Column(db.Boolean, nullable=False, default=False, primary_key=True)

class Tag(db.Model):
    __tablename__ = "tags"
    tagid = db.Column(db.Integer, primary_key=True)
    questionid = db.Column(db.Integer, nullable=False)
    revisionid = db.Column(db.Integer, nullable=False, default=1)
    tag = db.Column(db.String(255), nullable=False)
    value = db.Column(db.Text(65565), nullable=False)
    __table_args__ = (db.ForeignKeyConstraint(["questionid", "revisionid"], ["questions.questionid", "questions.revisionid"]),)
    question = db.relationship(Question, foreign_keys=[questionid, revisionid])

class Attempt(db.Model):
    __tablename__ = "attempts"
    attemptid = db.Column(db.Integer, primary_key=True)
    starttime = db.Column(DATETIME(fsp=6), default=datetime.datetime.utcnow)
    timetaken = db.Column(db.DECIMAL(10, 6))
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False, default=getuserid)
    questionid = db.Column(db.Integer, nullable=False)
    revisionid = db.Column(db.Integer, nullable=False, default=1)
    useranswers = db.Column(db.Text(65565))
    marks = db.Column(db.Integer, default=1)
    user = db.relationship(User)

class Comment(db.Model):
    __tablename__ = "comments"
    commentid = db.Column(db.Integer, primary_key=True)
    questionid = db.Column(db.Integer)
    revisionid = db.Column(db.Integer)
    profileid = db.Column(db.Integer, db.ForeignKey("users.userid"))
    attemptid = db.Column(db.Integer, db.ForeignKey("attempts.attemptid"))
    timewritten = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    replytocommentid = db.Column(db.Integer, db.ForeignKey("comments.commentid"))
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False, default=getuserid)
    content = db.Column(db.Text(65565), nullable=False)
    user = db.relationship(User, primaryjoin=userid==User.userid)
    profile = db.relationship(User, primaryjoin=profileid==User.userid)
    attempt = db.relationship(Attempt)

class Vote(db.Model):
    __tablename__ = "votes"
    voteid = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False, default=getuserid)
    commentid = db.Column(db.Integer, db.ForeignKey("comments.commentid"))
    questionid = db.Column(db.Integer)
    revisionid = db.Column(db.Integer)
    profileid = db.Column(db.Integer, db.ForeignKey("users.userid"))
    attemptid = db.Column(db.Integer, db.ForeignKey("attempts.attemptid"))
    islike = db.Column(db.Boolean, nullable=False, default=False)
    isdislike = db.Column(db.Boolean, nullable=False, default=False)
    isreport = db.Column(db.Boolean, nullable=False, default=False)

class Follower(db.Model):
    __tablename__ = "followers"
    followerid = db.Column(db.Integer, primary_key=True)
    timefollowed = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False, default=getuserid)
    followinguserid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False)
    follower = db.relationship(User, primaryjoin=userid==User.userid)
    followered = db.relationship(User, primaryjoin=followinguserid==User.userid)

class ReadNotification(db.Model):
    __tablename__ = "readnotifications"
    readnotificationid = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False, default=getuserid)
    commentid = db.Column(db.Integer, db.ForeignKey("comments.commentid"), nullable=False)