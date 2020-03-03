from database import *
from flask import redirect, render_template, request, abort, flash
from werkzeug.security import check_password_hash, generate_password_hash
import re, warnings

@app.before_request
def before_request():
    """Function that loads before each page request to stop non-logged in users viewing most pages"""
    if request.endpoint not in ["index", "logout", "login", "signup"]:
        user = getuser()
        if user == None:
            return redirect("/")
        elif user.isbanned:
            warnings.warn("user {} tried to load {} endpoint - but banned, fake error raised".format(user.username, request.endpoint))
            abort(500)

@app.context_processor
def inject_user():
    """Allows a user object to be made accessible to all templates."""
    return {"user":getuser()}

@app.route("/")
def index():
    """Endpoint for the login and signup page"""
    user = getuser()
    if user == None:
        return render_template("index.html")
    else:
        return redirect("/home")

@app.route("/logout")
def logout():
    """Endpoint that logs out a user and redirects them back to the login page"""
    Session.query.filter_by(sessionid=session["sessionid"]).delete()
    db.session.commit()
    session.pop("sessionid", None)
    return redirect("/")

@app.route("/login", methods=["POST"])
def login():
    """Endpoint that checks details entered and if valid logs in a user"""
    try:
        user = User.query.filter_by(username=request.form["username"]).one()
    except sqlerrors.NoResultFound:
        flash("The username you've entered doesn't match any account. Are you sure you've registered?", "is-danger")
        return render_template("index.html")

    if check_password_hash(user.password, request.form["password"]):
        usersession = Session(userid=user.userid)
        db.session.add(usersession)
        db.session.commit()
        session["sessionid"] = usersession.sessionid
        return redirect("/home")
    else:
        flash("Your password is incorrect, please try again.", "is-danger")
        return render_template("index.html")

@app.route("/signup", methods=["POST"])
def signup():
    """Endpoint that checks details entered and if valid signs up a user"""
    alreadysignedup = User.query.filter_by(username=request.form["username"]).count() > 0

    if alreadysignedup:
        flash("Someone has already signed up with that username, please try again.", "is-danger")
    else:
        """
        elif re.compile(r"\A[\w-]+\Z", re.UNICODE).match is None:
            message = "Letters, numbers, dashes, and underscores only in username."
        """
        if len(request.form["username"]) > 20 or len(request.form["username"]) < 3:
            flash("Username must be between 3 and 20 characters long.", "is-danger")
        else:
            newuser = User(username=request.form["username"], password=generate_password_hash(request.form["password"]))
            db.session.add(newuser)
            db.session.commit()
            flash("Signed up successfully, you may now login!", "is-success")

    return render_template("index.html")