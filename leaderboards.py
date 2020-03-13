from comments import *

@app.route("/activitylog")
@app.route("/activitylog/following")
@app.route("/activitylog/<int:profileid>")
def activitylog(profileid=None):
    """Endpoint that shows the activity log site-wide, for the user's followers and for a particular user"""
    user = getuser()
    log = {}
    fetchthese = {Comment:"timewritten", Question:"timestampadded", Attempt:"starttime", Follower:"timefollowed"}
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

@app.route("/profile/<int:profileid>")
def viewprofile(profileid=None):
    """Endpoint that shows the profile for a given user"""
    user = getuser()
    profile = User.query.filter_by(userid=profileid).first()
    if profile == None:
        return "The user doesn't exist.", 404
    followed = Follower.query.filter_by(userid=user.userid, followinguserid=profileid).first() != None
    return render_template("profile.html", profile=profile, followed=followed)

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

@app.route("/follow/<int:profileid>")
def follow(profileid):
    """Endpoint to allow a user to follow another user"""
    user = getuser()
    follower = Follower.query.filter_by(userid=user.userid, followinguserid=profileid).first()
    if follower == None:
        follower = Follower(followinguserid=profileid)
        db.session.add(follower)
    else:
        db.session.delete(follower)
    db.session.commit()
    return "Ok."

@app.route("/ban/<int:profileid>", methods=["POST"])
def ban(profileid):
    """Endpoint to allow an admin to ban a user"""
    user = getuser()
    if user.isadmin:
        profile = User.query.filter_by(userid=profileid).first()
        profile.isbanned = not profile.isbanned
        profile.banreason = request.data.decode("ascii")
        db.session.commit()
        return "OK"
    else:
        return "No.", 403

@app.route("/notifications", methods=["GET", "POST"])
def notifications():
    """Endpoint to allow a user to view notifications and mark them as read/unread"""
    user = getuser()
    if request.method == "GET":
        comments = []
        for comment in Comment.query.filter_by(userid=user.userid).all():
            for reply in Comment.query.filter_by(replytocommentid=comment.commentid).all():
                comments.append(reply)
        for comment in Comment.query.all():
            for word in comment.content.split(" "):
                if word.startswith("@"):
                    if word[1:] == user.username:
                        comments.append(comment)
        for attempt in Attempt.query.filter_by(userid=user.userid).all():
            for comment in Comment.query.filter_by(attemptid=attempt.attemptid).all():
                comments.append(comment)
        for comment in Comment.query.filter_by(profileid=user.userid).all(): #profileid=attempt.attemptid
            comments.append(comment)
        log = {}
        readcomments = set([i.commentid for i in ReadNotification.query.filter_by(userid=user.userid).all()])
        for comment in comments:
            if comment.commentid in readcomments:
                key = "Read"
            else:
                key = "Unread"
            if key not in log:
                log[key] = {}
            adate = comment.timewritten.date()
            if adate not in log[key]:
                log[key][adate] = {}
            username = comment.user.username
            if username not in log[key][adate]:
                log[key][adate][username] = []
            log[key][adate][username].append(comment)
        return render_template("notifications.html", log=log)
    else:
        for item in request.data.decode("ascii").split(","):
            notification = ReadNotification.query.filter_by(userid=user.userid, commentid=int(item)).first()
            if notification == None:
                notification = ReadNotification(commentid=int(item))
                db.session.add(notification)
            else:
                db.session.delete(notification)
        db.session.commit()
        return "Ok."

@app.route("/users")
def viewusers():
    """Endpoint to view a list of users on the site"""
    user = getuser()
    if user.isadmin:
        users = User.query.order_by(User.timesignedup.desc()).all()
        return render_template("users.html", users=users)
    else:
        abort(404)