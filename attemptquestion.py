from addquestion import *
from flask import make_response
import random, math

def getverifiedrevision(questionid):
    """Gets the latest verified revision id from a question, if one exists."""
    results = Question.query.filter_by(questionid=questionid, isverified=True).order_by(Question.revisionid.desc()).all()
    if len(results) != 0:
        return results[0].revisionid

def getlatestrevision(questionid):
    """Gets the latest revision id from a question, if one exists."""
    revision = Question.query.filter_by(questionid=questionid).order_by(Question.revisionid.desc()).first()
    if revision != None:
        return revision.revisionid

@app.route("/attemptquestion/<int:questionid>", methods=["GET", "POST"])
@app.route("/attemptquestion/<int:questionid>/<int:revisionid>", methods=["GET", "POST"])
def attemptquestion(questionid, revisionid=None):
    """Endpoint to allow a user to attempt a question."""
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
    if request.method == "GET":
        alreadythere = Attempt.query.filter_by(questionid=questionid, revisionid=revisionid).order_by(Attempt.starttime.desc()).first()
        if alreadythere == None:
            attempt = Attempt(questionid=questionid, revisionid=revisionid)
            db.session.add(attempt)
            db.session.commit()
        elif alreadythere.timetaken != None:
            attempt = Attempt(questionid=questionid, revisionid=revisionid)
            db.session.add(attempt)
            db.session.commit()
    if tags["type"] == "multiplechoice":
        if request.method == "GET":
            return render_template("attemptquestion.html", type="multiplechoice", choices=tags["choices"].split("\n"), question=tags["question"])
        elif request.method == "POST":
            useranswer = request.get_json()["multiplechoice"]
            iscorrect = useranswer == str(tags["answerindex"])
            if iscorrect:
                if "marks" in tags:
                    marks = int(tags["marks"])
                else:
                    marks = 1
            else:
                marks = 0
            attempt = Attempt.query.filter_by(questionid=questionid, revisionid=revisionid).order_by(Attempt.starttime.desc()).first()
            if attempt.timetaken == None:
                attempt.useranswers = useranswer
                attempt.marks = marks
                attempt.timetaken = (datetime.datetime.utcnow() - attempt.starttime).total_seconds()
                db.session.commit()
                reply = {"correct":iscorrect, "correctanswer":tags["answerindex"], "marks":marks, "timetaken":float(attempt.timetaken), "valid":True}
            else:
                reply = {"valid":False, "message":"You have already submitted an answer for this question recently."}
            return json.dumps(reply)
    elif tags["type"] == "written":
        if request.method == "GET":
            return render_template("attemptquestion.html", type="written", question=tags["question"])
        elif request.method == "POST":
            useranswer = request.get_json()["answer"]
            attempt = Attempt.query.filter_by(questionid=questionid, revisionid=revisionid).order_by(Attempt.starttime.desc()).first()
            if attempt.timetaken == None:
                attempt.useranswers = useranswer
                attempt.timetaken = (datetime.datetime.utcnow() - attempt.starttime).total_seconds()
                db.session.commit()
                if "marks" in tags:
                    marks = int(tags["marks"])
                else:
                    marks = 1
                reply = {"markscheme":tags["markscheme"], "attemptid":attempt.attemptid, "marks":marks, "timetaken":float(attempt.timetaken), "valid":True}
            else:
                reply = {"valid":False, "message":"You have already submitted an answer for this question recently."}
            return json.dumps(reply)
    else:
        return "The question doesn't have a valid type.", 404

@app.route("/setmark/<attemptid>/<marks>")
def setmark(attemptid, marks):
    """Endpoint to allow a user to set marks for an attempt on a question they did."""
    user = getuser()
    attempt = Attempt.query.filter_by(attemptid=attemptid).first()
    if user.userid == attempt.userid:
        tags = getquestiontags(attempt.questionid, attempt.revisionid)
        if "marks" in tags:
            maxmarks = int(tags["marks"])
        else:
            maxmarks = 1
        if attempt.marks <= maxmarks:
            attempt.marks = marks
            db.session.commit()
            return "OK"
    return "No.", 403

def get_weakest_topics(tag, userid):
    """Returns a dictionary of values with ratings reflecting how secure they are for a tag and user."""
    tags = Tag.query.filter_by(tag=tag).all()
    questionidvalues = {}
    questionids = []
    for tag in tags:
        if tag.value not in questionidvalues:
            questionidvalues[tag.value] = []
        if tag.questionid not in questionidvalues[tag.value]:
            questionidvalues[tag.value].append(tag.questionid)
        questionids.append(tag.questionid)
    questionids = list(set(questionids))
    attempts = Attempt.query.filter(Attempt.questionid.in_(questionids), Attempt.useranswers != None, Attempt.userid == userid).order_by(Attempt.starttime.asc()).all()
    results = {}
    for attempt in attempts:
        if attempt.questionid not in results:
            verifiedrevision = getverifiedrevision(attempt.questionid)
            if verifiedrevision == None:
                continue
            maxmarks = getquestiontags(attempt.questionid, verifiedrevision)
            if "marks" in maxmarks:
                maxmarks = maxmarks["marks"]
            else:
                maxmarks = 1
            results[attempt.questionid] = {"maxmarks":maxmarks, "marks":[]}
        results[attempt.questionid]["marks"].append(attempt.marks)
    for questionid in results:
        correct = results[questionid]["marks"].count(results[questionid]["maxmarks"])
        score = correct - (len(results[questionid]["marks"]) - correct)
        if score > 0:
            score = 1
        else:
            score = 0
        results[questionid] = score
    extra = list(set(questionids) - set(results))
    for item in extra:
        results[item] = 0
    for value in questionidvalues:
        scores = [results[i] for i in questionidvalues[value]]
        questionidvalues[value] = sum(scores)/len(scores)
    return questionidvalues

@app.route("/progress/<tag>")
def progress(tag):
    """Endpoint to return the values with ratings reflecting how secure they are for a tag and user."""
    user = getuser()
    return json.dumps(get_weakest_topics(tag, user.userid))

def getxpfromlevel(level):
    """Gets the XP required for a given level."""
    return (5*(level**2)) + (30*level)

def getlevelfromxp(xp):
    """Gets the level for a given amount of XP."""
    return -3 + math.sqrt((xp/5)+9)

def getlevelxpstats(xp):
    """Gets the level and the amount of XP required to get to the next level for a given amount of XP."""
    level = getlevelfromxp(xp)
    xptonextlevel = getxpfromlevel(int(level)+1)-xp
    return level, xptonextlevel

def getxprepforuser(userid):
    """Gets the XP and level statistics for a given user."""
    # marks gained on completing questions
    xp = Attempt.query.with_entities(func.sum(Attempt.marks).label("sum")).filter_by(userid=userid).first()[0]
    if xp == None:
        xp = 0

    # rep for getting questions verified
    rep = Question.query.filter_by(userid=userid, isverified=True).count()
    # number of followers the user has
    rep += Follower.query.filter_by(followinguserid=userid).count()

    if rep < 0:
        rep = 0

    xplevelstats = getlevelxpstats(xp)
    replevelstats = getlevelxpstats(rep)
    result = {"xp":xp, "xplevel":xplevelstats[0], "xptonextlevel":xplevelstats[1],
    "rep":rep, "replevel":replevelstats[0], "reptonextlevel":replevelstats[1]}
    return result

@app.route("/")
def home():
    """Endpoint for the homepage."""
    user = getuser()
    tags = [item[0] for item in db.session.query(Tag.tag).filter(~Tag.tag.in_(["question", "choices", "answerindex"])).group_by(Tag.tag).order_by(desc(func.count(Tag.tag))).all()]
    return render_template("home.html", tags=tags)

def variancelike(scores):
    """Returns a score reflecting how variable the values passed in to the function are."""
    mean = sum(scores)/len(scores)
    variancescore = 0
    for item in scores:
        if mean - item < 0:
            factor = -1
        else:
            factor = 1
        variancescore += factor*((mean - item)**2)
    return variancescore

def learningsystem(questionids, userid):
    """Sorts a list of questions for a user based on how weak the user is at them."""
    attempts = Attempt.query.filter(Attempt.questionid.in_(questionids), Attempt.useranswers != None, Attempt.userid == userid).order_by(Attempt.starttime.asc()).all()
    results = {}
    for attempt in attempts:
        if attempt.questionid not in results:
            verifiedrevision = getverifiedrevision(attempt.questionid)
            if verifiedrevision == None:
                if getallquestions in questionids:
                    questionids.remove(attempt.questionid)
                continue
            maxmarks = getquestiontags(attempt.questionid, verifiedrevision)
            if "marks" in maxmarks:
                maxmarks = maxmarks["marks"]
            else:
                maxmarks = 1
            results[attempt.questionid] = {"maxmarks":maxmarks, "marks":[], "timetaken":[], "timestamps":[]}
        results[attempt.questionid]["marks"].append(attempt.marks)
        results[attempt.questionid]["timetaken"].append(attempt.timetaken)
        results[attempt.questionid]["timestamps"].append(attempt.starttime)
    for questionid in results:
        #score = sum(results[questionid]["marks"])/(results[questionid]["maxmarks"]*len(results[questionid]["marks"]))
        correct = results[questionid]["marks"].count(results[questionid]["maxmarks"])
        score = correct - (len(results[questionid]["marks"]) - correct)
        variancetime = variancelike(results[questionid]["timetaken"])
        results[questionid] = (score, variancetime, max(results[questionid]["timestamps"]))
    results = [i[0] for i in sorted(results.items(), key=lambda x: x)]
    extra = list(set(questionids) - set(results))
    random.shuffle(extra)
    results = extra + results
    return results

@app.route("/practice")
def practice():
    """Endpoint for a user to start a practice session."""
    filters = request.args.get("filters", default=None)
    resp = make_response(render_template("practice.html"))
    if filters != None:
        user = getuser()
        filters = json.loads(filters)
        questionids = list(getallquestions(filters=filters)[0].keys())
        questionids = learningsystem(questionids, user.userid)
        resp.set_cookie("questioncache", ".".join(str(i) for i in questionids))
    else:
        if "questioncache" in request.cookies:
            questioncache = request.cookies.get("questioncache").split(".")
            questioncache = list(filter(lambda x: x.strip() != "", questioncache))
            finished = len(questioncache) == 0
        else:
            finished = True
        if finished:
            return redirect("/home")
    return resp
