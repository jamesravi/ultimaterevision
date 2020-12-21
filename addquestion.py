from loginsignup import *
import json, operator, copy
from flask import Response

def diffdict(a, b):
    """Computes the difference between two dictionaries."""
    c = {}

    for key in a:
        if key not in b:
            # Removed
            c[key] = ""

    for key in b:
        if key in a:
            if a[key] == b[key]:
                # Identical
                pass
            else:
                # Modified
                c[key] = b[key]
        else:
            # Added
            c[key] = b[key]

    return c

@app.route("/search/<value>")
@app.route("/search/<value>/<tag>")
def search(tag=None, value=None):
    """Endpoint for a user to search for a value (or optionally a tag as well) on the question page."""
    value = "%" + value + "%"
    results = db.session.query(Tag.tag, Tag.value)
    if tag != None:
        results = results.filter_by(tag=tag)
    results = results.filter(~Tag.tag.in_(["question", "choices", "answerindex"])).filter(Tag.value.like(value)).distinct().all()
    return json.dumps([[tag.tag, tag.value] for tag in results])

@app.route("/questions")
def questionspage():
    """Endpoint for a user to search for a value (or optionally a tag as well) on the question page."""
    page = request.args.get("page", default=1, type=int)
    filters = request.args.get("filters", default=None)
    if filters != None:
        filters = json.loads(filters)
    questions, total = getallquestions(page, filters=filters)
    latest = {}
    for question in questions:
        latest[question] = max(questions[question].keys())
    return render_template("questions.html", questions=questions, latest=latest, total=total, page=page)

def getquestiontags(questionid, revisionid):
    """Recursively retrieves and compiles all the tags for a given question and revision from the revisions required from the question."""
    results = Tag.query.filter_by(questionid=questionid, revisionid=revisionid).all()
    tags = None
    if revisionid != results[0].question.previousrevisionid:
        tags = getquestiontags(questionid, results[0].question.previousrevisionid) #recursion occurs here
    newtags = {tag.tag:tag.value for tag in results}
    if tags == None:
        return newtags
    else:
        for key, value in newtags.items():
            if value != "":
                tags[key] = value
            else:
                del tags[key] #an empty value means the tag was deleted compared to the previous revision
        return tags #acts as base case if last revision reached

def getquestion(questionid, revisionid=None):
    """
    If a revision is specified, the question retrieves its information and its tags.
    Otherwise, it fetches the information and tags for every revision.
    """
    if revisionid == None:
        revisions = {}
        for revision in Question.query.filter_by(questionid=questionid):
            revisions[revision.revisionid] = getquestion(questionid, revisionid=revision.revisionid)
        return revisions
    else:
        question = Question.query.filter_by(questionid=questionid, revisionid=revisionid).one()
        question.tags = getquestiontags(questionid, revisionid)
        return question

def getallquestions(page=None, per_page=10, filters=None):
    """Gets all questions, with pagination and filter support."""
    if filters == None:
        questionids = db.session.query(Question.questionid).distinct().all()
        questionids = [item[0] for item in questionids]
    else:
        tags = db.session.query(Tag).filter(tuple_(Tag.tag, Tag.value).in_(filters)).all()
        questionids = sorted(set([tag.questionid for tag in tags]))
    total = len(questionids)
    if page != None:
        if page < 1:
            page = 1
        offset = (page-1)*per_page
        questionids = questionids[offset:offset+per_page]
    questions = {questionid:getquestion(questionid) for questionid in questionids}
    return questions, total

@app.route("/addquestion", methods=["GET", "POST"])
@app.route("/editquestion/<int:questionid>/<int:revisionid>", methods=["GET", "POST"])
def changequestion(questionid=None, revisionid=None):
    """Endpoint to allow a user to add a question or edit an existing one to create a new revision."""
    user = getuser()

    if "addquestion" in request.path:
        isedit = False
    elif "editquestion" in request.path:
        isedit = True
        lockededit = LockedFromEditing.query.filter_by(questionid=questionid).first()
        if lockededit != None and not user.isadmin:
            if lockededit.lockedfromediting:
                return """<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bulma@0.8.0/css/bulma.min.css\">
                <h1 class=\"subtitle is-4\">Locked from editing</h1>
                <p>This question is currently locked from editing.</p>""", 403
    else:
        raise Exception(request.path)

    if request.method == "GET":
        question = None
        if isedit:
            try:
                question = getquestiontags(questionid, revisionid)
            except IndexError:
                return "<h1>Not found</h1><p>The question or revision for this question doesn't exist.</p>", 404
            latest = Question.query.filter_by(questionid=questionid).order_by(Question.revisionid.desc()).first().revisionid
            if revisionid != latest:
                return "<h1>Not latest revision</h1><p>You can only edit the latest revision of a question.</p>", 403
        tags = [item[0] for item in db.session.query(Tag.tag).group_by(Tag.tag).order_by(desc(func.count(Tag.tag))).all()]
        return render_template("addquestion.html", rows=question, tags=tags)
    elif request.method == "POST":
        data = {item[0]:item[1] for item in request.get_json() if item[1] != ""}

        if isedit:
            prevquestion = getquestiontags(questionid, revisionid)
            data = diffdict(prevquestion, data)

        sendback = {"isvalid":True}
        if len(data) == 0:
            sendback["isvalid"] = False
            sendback["message"] = "No changed tags were recorded, so the question wasn't edited."
        else:
            if isedit:
                latest = Question.query.filter_by(questionid=questionid).order_by(Question.revisionid.desc()).first().revisionid
            else:
                latest = Question.query.order_by(Question.questionid.desc()).first()
                if latest is None:
                    latest = 0
                else:
                    latest = latest.questionid
            latest += 1

            if isedit:
                question = Question(questionid=questionid, previousrevisionid=revisionid, revisionid=latest)
                sendback["nextrevision"] = latest
            else:
                question = Question(questionid=latest)
            db.session.add(question)
            db.session.commit()

            for row in data:
                tagitem = Tag(questionid=question.questionid, revisionid=question.revisionid, tag=row, value=data[row])
                db.session.add(tagitem)

            db.session.commit()

            if isedit:
                message = "Question has been edited."
            else:
                message = "Thanks for adding a question!"
            flash(message, "is-success")
        sendback = json.dumps(sendback)
        return Response(sendback, status=200, mimetype="application/json")

def previousrevisionids(questionid, revisionid):
    """Recursively gets a list of previous revision ids linked to the given revision id for a question"""
    if type(revisionid) == int:
        revisionid = [revisionid]
    question = Question.query.filter_by(questionid=questionid, revisionid=revisionid).one()
    if revisionid != [question.previousrevisionid]: #if this is not the first revision
        return revisionid+previousrevisionids(questionid, question.previousrevisionid) #recursively add the next revisions to the list
    else:
        return revisionid #base case

@app.route("/deletequestion/<int:questionid>/<int:revisionid>", methods=["DELETE"])
def deletequestion(questionid, revisionid):
    """Endpoint for a user to delete a revision from a question"""
    user = getuser()
    if user.isadmin:
        latest = Question.query.filter_by(questionid=questionid).order_by(Question.revisionid.desc()).first()
        if revisionid == latest.revisionid:
            Tag.query.filter_by(questionid=questionid, revisionid=revisionid).delete()
            Question.query.filter_by(questionid=questionid, revisionid=revisionid).delete()
        else:
            #saves a copy of the selected revision's tags before they are deleted
            tags = getquestiontags(questionid, revisionid)
            prevrevisionids = previousrevisionids(questionid, revisionid)
            #removes the tags from every previous revision including the one selected
            for arevisionid in prevrevisionids:
                Tag.query.filter_by(questionid=questionid).filter_by(revisionid=arevisionid).delete()
            #removes every revision before except the one selected
            for arevisionid in prevrevisionids:
                if arevisionid != revisionid:
                    Question.query.filter_by(questionid=questionid).filter_by(revisionid=arevisionid).delete()
            question = Question.query.filter_by(questionid=questionid, revisionid=revisionid).first()
            question.previousrevisionid = question.revisionid
            #updates the selected revision with the cached tags
            for tag in tags:
                if tags[tag] != "":
                    tagitem = Tag(questionid=questionid, revisionid=revisionid, tag=tag, value=tags[tag])
                    db.session.add(tagitem)
        db.session.commit()
        return "OK"
    else:
        return "No.", 403

@app.route("/verifyquestion/<int:questionid>/<int:revisionid>")
def verifyquestion(questionid, revisionid):
    """Endpoint for a user to verifiy a revision from a question"""
    user = getuser()
    if user.isadmin:
        question = Question.query.filter_by(questionid=questionid, revisionid=revisionid).first()
        question.isverified = not question.isverified
        db.session.commit()
        return "OK"
    else:
        return "No.", 403

@app.route("/lockfromediting/<int:questionid>")
def lockquestionfromediting(questionid):
    """Endpoint for an admin to lock a question from editing"""
    user = getuser()
    if user.isadmin:
        lockededit = LockedFromEditing.query.filter_by(questionid=questionid).first()
        if lockededit == None:
            lockededit = LockedFromEditing(questionid=questionid, lockedfromediting=True)
            db.session.add(lockededit)
        else:
            lockededit.lockedfromediting = not lockededit.lockedfromediting
        db.session.commit()
        return "OK"
    else:
        return "No.", 403
