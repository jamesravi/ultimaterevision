from attemptquestion import *
import bisect

def confidencevote(pos, n):
    """
    Function that returns a rating for a comment based on likes and dislikes.
    Based on this article: http://www.evanmiller.org/how-not-to-sort-by-average-rating.html
    """
    if n == 0:
        return 0
    z = 1.2815515594600038 #confidence level of 80%
    phat = float(pos)/n
    first = phat + (z*z)/(2*n)
    second = ((phat*(1-phat)) + ((z*z)/(4*n)))/n
    second = z*(second**0.5)
    third = 1+((z*z)/n)
    return (first - second) / third

@app.route("/attempts/<int:questionid>")
@app.route("/attempts/<int:questionid>/<int:revisionid>")
def viewattempts(questionid, revisionid=None):
    """Endpoint for a user to view the attempts for a question"""
    if revisionid == None:
        revisionid = getverifiedrevision(questionid)
        if revisionid == None:
            return "Either the question doesn't exist or it doesn't have a verified revision.", 404
        tags = getquestiontags(questionid, revisionid)
    else:
        try:
            tags = getquestiontags(questionid, revisionid)
        except IndexError:
            return "The question or revision doesn't exist.", 404
    if "marks" in tags:
        marks = int(tags["marks"])
    else:
        marks = 1
    attempts = Attempt.query.filter_by(questionid=questionid, revisionid=revisionid)
    sortby = request.args.get("sortby", default="marks")
    order = [Attempt.marks.desc(), Attempt.timetaken.asc(), Attempt.starttime.desc()]
    if sortby == "timetaken":
        order = [Attempt.timetaken.asc(), Attempt.marks.desc(), Attempt.starttime.desc()]
    elif sortby == "timestarted":
        order = [Attempt.starttime.desc(), Attempt.marks.desc(), Attempt.timetaken.asc()]
    for item in order:
        attempts = attempts.order_by(item)
    attempts = attempts.all()
    inprogress, completed = [], {}
    for attempt in attempts:
        attempt.maxmarks = marks
        if attempt.useranswers != None and tags["type"] == "multiplechoice":
            attempt.useranswers = tags["choices"].split("\n")[int(attempt.useranswers)-1]
        if attempt.timetaken == None:
            inprogress.append(attempt)
        else:
            if attempt.useranswers not in completed:
                completed[attempt.useranswers] = []
            likes = Vote.query.filter_by(attemptid=attempt.attemptid, islike=True).count()
            dislikes = Vote.query.filter_by(attemptid=attempt.attemptid, isdislike=True).count()
            attempt.votes = confidencevote(likes, dislikes)
            completed[attempt.useranswers].append(attempt)
    if sortby == "votes":
        for key, value in completed.items():
            value.sort(key=lambda x: x.votes, reverse=True)
    return render_template("attempts.html", inprogress=inprogress, completed=completed)

@app.route("/attempt/<int:attemptid>")
def viewattempt(attemptid):
    """Endpoint for a user to view a particular attempt on a question"""
    user = getuser()
    attempt = Attempt.query.filter_by(attemptid=attemptid).one()
    tags = getquestiontags(attempt.questionid, attempt.revisionid)
    if "marks" in tags:
        maxmarks = int(tags["marks"])
    else:
        maxmarks = 1
    if attempt.useranswers != None and tags["type"] == "multiplechoice":
        attempt.useranswers = tags["choices"].split("\n")[int(attempt.useranswers)-1]
    attempt.maxmarks = maxmarks
    vote = Vote.query.filter_by(userid=user.userid, attemptid=attemptid).first()
    if vote != None:
        attempt.liked = vote.islike
        attempt.disliked = vote.isdislike
        attempt.reported = vote.isreport
    else:
        attempt.liked = False
        attempt.disliked = False
        attempt.reported = False
    return render_template("attempt.html", attempt=attempt)

@app.route("/leaderboard/<int:questionid>")
@app.route("/leaderboard/<int:questionid>/<int:revisionid>")
def leaderboard(questionid, revisionid=None):
    """Endpoint for a user to view leaderboards on a question"""
    user = getuser()
    if revisionid == None:
        revisionid = getverifiedrevision(questionid)
        if revisionid == None:
            return "Either the question doesn't exist or it doesn't have a verified revision.", 404
        tags = getquestiontags(questionid, revisionid)
    else:
        try:
            tags = getquestiontags(questionid, revisionid)
        except IndexError:
            return "The question or revision doesn't exist.", 404
    if "marks" in tags:
        marks = int(tags["marks"])
    else:
        marks = 1
    attempts = Attempt.query.filter_by(questionid=questionid, revisionid=revisionid)
    if request.args.get("publicorprivate", default="public") == "private":
        ids = [follower.followinguserid for follower in Follower.query.filter_by(userid=user.userid).all()] + [user.userid]
        attempts = attempts.filter(Attempt.userid.in_(ids))
    sortby = request.args.get("sortby", default="marks")
    order = [Attempt.marks.desc(), Attempt.timetaken.asc(), Attempt.starttime.desc()]
    if sortby == "timetaken":
        order = [Attempt.timetaken.asc(), Attempt.marks.desc(), Attempt.starttime.desc()]
    elif sortby == "timestarted":
        order = [Attempt.starttime.desc(), Attempt.marks.desc(), Attempt.timetaken.asc()]
    for item in order:
        attempts = attempts.order_by(item)
    attempts = attempts.all()
    attemptscache = []
    for attempt in attempts:
        attempt.maxmarks = marks
        if attempt.timetaken != None:
            vote = Vote.query.filter_by(userid=user.userid, attemptid=attempt.attemptid).first()
            if vote != None:
                attempt.liked = vote.islike
                attempt.disliked = vote.isdislike
            else:
                attempt.liked = False
                attempt.disliked = False
            likes = Vote.query.filter_by(attemptid=attempt.attemptid, islike=True).count()
            dislikes = Vote.query.filter_by(attemptid=attempt.attemptid, isdislike=True).count()
            attempt.votes = confidencevote(likes, dislikes)
            attemptscache.append(attempt)
    if sortby == "votes":
        attemptscache.sort(key=lambda x: x.votes, reverse=True)
    return render_template("leaderboard.html", attempts=attemptscache, questionid=questionid, revisionid=revisionid)
