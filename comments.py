from attemptquestion import *
import bisect

def in_order(items, tree, depth=0):
    """Returns the items of a tree of comments in order recursively"""
    result = []
    for item in sorted(items, reverse=True):
        if type(item) == tuple:
            item = item[1]
        result.append((item, depth))
        if item in tree:
            result.extend(in_order(tree[item], tree, depth=depth+1)) #recursively gets replies to current comment
    return result

def returninorder(comments, sortbyvotes, type="comment"):
    """Returns comments in order using a tree structure, keeping replies together and sorting by votes at the same time"""
    tree = {}
    for comment in comments:
        replytocommentid = comment.replytocommentid
        if replytocommentid == None:
            replytocommentid = 0
        if replytocommentid not in tree:
            tree[replytocommentid] = []
        if sortbyvotes:
            likes = Vote.query.filter_by(commentid=comment.commentid, islike=True).count()
            dislikes = Vote.query.filter_by(commentid=comment.commentid, isdislike=True).count()
            votes = confidencevote(likes, dislikes)
            bisect.insort(tree[replytocommentid], (votes, comment.commentid))
        else:
            bisect.insort(tree[replytocommentid], comment.commentid)
    comments = {comment.commentid:comment for comment in comments}
    if len(comments) > 0:
        ordered = in_order(tree[0], tree)
        ordered = [(comments[item[0]], item[1]) for item in ordered]
        return ordered
    else:
        return []

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

@app.route("/comments/question/<int:questionid>", methods=["GET", "POST"])
@app.route("/comments/question/<int:questionid>/<int:revisionid>", methods=["GET", "POST"])
@app.route("/comments/profile/<int:profileid>", methods=["GET", "POST"])
@app.route("/comments/attempt/<int:attemptid>", methods=["GET", "POST"])
def commentspage(questionid=None, revisionid=None, profileid=None, attemptid=None):
    """Endpoint for a comments page"""
    user = getuser()
    if questionid != None and revisionid == None:
        revisionid = getverifiedrevision(questionid)
    if request.method == "POST":
        data = request.get_json()
        content = data["content"]
        replytocommentid = None
        if "replytocommentid" in data:
            replytocommentid = data["replytocommentid"]
        comment = Comment(questionid=questionid, revisionid=revisionid, profileid=profileid, attemptid=attemptid, content=content, replytocommentid=replytocommentid)
        db.session.add(comment)
        db.session.commit()
        return json.dumps({"valid":True})
    else:
        sortbyvotes = request.args.get("sortby", default="votes")
        if sortbyvotes == "votes":
            sortbyvotes = True
        else:
            sortbyvotes = False
        comments = Comment.query #db.session.query(Comment.content, Comment.timewritten, User.username)
        comments = comments.filter_by(questionid=questionid, revisionid=revisionid, profileid=profileid, attemptid=attemptid)
        comments = returninorder(comments.all(), sortbyvotes)
        for comment in comments:
            comment = comment[0]
            vote = Vote.query.filter_by(userid=user.userid, commentid=comment.commentid).first()
            if vote != None:
                comment.liked = vote.islike
                comment.disliked = vote.isdislike
                comment.reported = vote.isreport
            else:
                comment.liked = False
                comment.disliked = False
                comment.reported = False
            likes = Vote.query.filter_by(commentid=comment.commentid, islike=True).count()
            dislikes = Vote.query.filter_by(commentid=comment.commentid, isdislike=True).count()
            comment.votes = round(confidencevote(likes, dislikes)*(likes+dislikes))
            comment.reports = Vote.query.filter_by(commentid=comment.commentid, isreport=True).count()
        return render_template("comments.html", comments=comments)

@app.route("/deletecomment/<int:commentid>", methods=["DELETE"])
def deletecomment(commentid):
    """Endpoint for a user to delete a comment"""
    user = getuser()
    comment = Comment.query.filter_by(commentid=commentid).one()
    if comment.userid == user.userid or user.isadmin:
        try:
            Comment.query.filter_by(commentid=commentid).delete()
        except sqlerrors2.IntegrityError:
            comment.content = "*This comment has been deleted.*"
        db.session.commit()
        return "OK"
    else:
        return "No.", 403

@app.route("/vote/comment/<int:commentid>")
@app.route("/vote/attempt/<int:attemptid>")
@app.route("/vote/question/<int:questionid>")
@app.route("/vote/question/<int:questionid>/<int:revisionid>")
@app.route("/vote/profile/<int:profileid>")
def submitvote(questionid=None, revisionid=None, profileid=None, attemptid=None, commentid=None):
    """Endpoint for a user to vote on a comment, attempt, question or user profile"""
    user = getuser()
    if questionid != None and revisionid == None:
        revisionid = getverifiedrevision(questionid)
    vote = Vote.query.filter_by(userid=user.userid, questionid=questionid, revisionid=revisionid, profileid=profileid, attemptid=attemptid, commentid=commentid).first()
    didnotexist = vote == None
    if didnotexist:
        vote = Vote(userid=user.userid, questionid=questionid, revisionid=revisionid, profileid=profileid, attemptid=attemptid, commentid=commentid)
    thetype = request.args.get("type")
    if thetype == "like":
        vote.islike = not vote.islike
    elif thetype == "dislike":
        vote.isdislike = not vote.isdislike
    elif thetype == "report":
        vote.isreport = not vote.isreport
    else:
        raise Exception("Unknown vote type: {}".format(thetype))
    if didnotexist:
        db.session.add(vote)
    db.session.commit()
    return "Ok."

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
