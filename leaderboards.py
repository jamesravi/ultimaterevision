from comments import *

@app.route("/activitylog")
@app.route("/activitylog/following")
@app.route("/activitylog/<int:profileid>")
def activitylog(profileid=None):
    """Endpoint that shows the activity log site-wide, for the user's followers and for a particular user"""
    user = getuser()
    log = {}
    fetchthese = {Question:"timestampadded", Attempt:"starttime", Follower:"timefollowed"}
    for database, timestamp in fetchthese.items():
        items = database.query
        if profileid != None:
            items = items.filter(getattr(database, "userid")==profileid)
        if request.path.endswith("following"):
            ids = [follower.followinguserid for follower in Follower.query.filter_by(userid=user.userid).all()]
            items = items.filter(getattr(database, "userid").in_(ids))
        items = items.order_by(getattr(database, timestamp).desc())
        for item in items:
            adate = getattr(item, timestamp).date()
            tablename = database.__tablename__
            if adate not in log:
                log[adate] = {}
            if tablename not in log[adate]:
                log[adate][tablename] = {}
            username = User.query.filter(getattr(User, "userid")==item.userid).first()
            if username not in log[adate][tablename]:
                log[adate][tablename][username] = []
            log[adate][tablename][username].append(item)
    return render_template("activitylog.html", log=log)

@app.route("/globalactivitylog")
def globalactivitylog():
    return render_template("globalactivitylog.html")

@app.route("/viewquestion/<int:questionid>")
@app.route("/viewquestion/<int:questionid>/<int:revisionid>")
def viewquestion(questionid, revisionid=None):
    """Endpoint to allow a user to display a question"""
    if revisionid == None:
        revisionid = getlatestrevision(questionid)
        if revisionid == None:
            return "The question doesn't exist.", 404
        tags = getquestiontags(questionid, revisionid)
    else:
        try:
            tags = getquestiontags(questionid, revisionid)
        except IndexError:
            return "The question or revision doesn't exist.", 404
    question = Question.query.filter_by(questionid=questionid, revisionid=revisionid).first()
    return render_template("question.html", question=question, tags=tags)

