from database import *
from flask import redirect, render_template, request, abort, flash
from werkzeug.security import check_password_hash, generate_password_hash
import re, warnings

@app.context_processor
def inject_user():
    """Allows a user object to be made accessible to all templates."""
    return {"user":getuser()}
