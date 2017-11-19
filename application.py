import sqlite3
import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify, g

from wtforms import Form, StringField, PasswordField, validators

from passlib.hash import sha256_crypt

#from flask_session import Session
#from passlib.apps import custom_app_context as pwd_context

# configure application
app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('flask.cfg')

#NOTE: include secret_key
#app.secret_key='dev'

#configure database
DATABASE = 'lftracker.db'

# easy connect to database
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # present data as dictionaries
        db.row_factory = make_dicts
        # OR use Row objects rather than dicts to return the results of queries
        # however, returns row memory address when query for the whole data
        #db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# db querying helper
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# db commit helper
def commit_db(query, args=()):
    cur = get_db().execute(query, args)
    get_db().commit()
    cur.close()

# make database return dictionaries
def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

"""# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)"""

# login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Must log in first!", "error")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# index page
@app.route("/")
def index():
    return render_template("index.html")

# wtforms calss validator for signup page
class RegistrationForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25)], render_kw={"placeholder": "Username"})
    password = PasswordField('New Password', [validators.DataRequired(), validators.EqualTo('confirm', message='Passwords do not match')], render_kw={"placeholder": "Password"})
    confirm = PasswordField('Confirm Password', render_kw={"placeholder": "Confirm Password"})

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        date = str(datetime.datetime.now())
        commit_db("INSERT INTO users VALUES (?, ?, ?)", [form.username.data, sha256_crypt.encrypt(str(form.password.data)), date])
        flash('Thank you for registering. Please log in.', 'message-success')
        return redirect(url_for('login'))
    return render_template("signup.html", form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        try_password = request.form['password']
        # query database
        rows = query_db("SELECT * FROM users WHERE username = (?)", [username])

        if rows:
            password = rows[0]['password']
            if sha256_crypt.verify(try_password, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You have logged in', 'message-success')
                return redirect(url_for('dashboard'))
            error = 'Incorrect username or password'
            return render_template('login.html', error=error)
        error = 'Incorrect username or password'
        return render_template('login.html', error=error)
    return render_template("login.html")

#wtforms for activity intake modal
"""class ActivityModal(Form):
    activity = SelectField('Select Activity:', choices=[('Sleep', 'Sleep'), ('Feeding', 'Feeding'), ('Playing', 'Playing'), ('Bathing', 'Bathing'), ('Diaper Change', 'Diaper Change')])
    start = DateTimeField([validators.DataRequired()])
    end = DateTimeField([validators.DataRequired()])"""

#convert string hours into decimals helper function
def string_to_decimal(time):
    hours_minutes = time.split(":")
    return round(float(hours_minutes[0]) + float(hours_minutes[1])/60.0, 2)

@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    #form = ActivityModal(request.form)

    # submit new activity from a modal form
    if request.method == 'POST':
        user = session["username"]
        activity = request.form.get("activities")
        start_time = request.form.get("start")
        end_time = request.form.get("end")
        note = request.form.get("note")
        date = str(datetime.datetime.now())
        date = date.split(' ')
        date = date[0]

        #calculate total time
        total_time = string_to_decimal(end_time) - string_to_decimal(start_time)
        if total_time < 0:
            total_time = abs(24%total_time)
        total_time = round(total_time, 2)

        commit_db("INSERT INTO activities VALUES (?, ?, ?, ?, ?, ?, ?)", [user, activity, start_time, end_time, note, total_time, date])
        return redirect(url_for('dashboard'))

    # get total hours and total count from db
    totals = query_db("SELECT activity, SUM(total_time) total_time, COUNT(activity) total_count FROM activities WHERE user = (?) GROUP BY activity", [session["username"]])
    return render_template("dashboard-home.html", totals = totals)

@app.route("/history", methods=['GET', 'POST'])
@login_required
def history():

    # submit new activity from a modal form
    if request.method == 'POST':
        user = session["username"]
        activity = request.form.get("activities")
        start_time = request.form.get("start")
        end_time = request.form.get("end")
        note = request.form.get("note")
        date = str(datetime.datetime.now())
        date = date.split(' ')
        date = date[0] 

        #calculate total time
        total_time = string_to_decimal(end_time) - string_to_decimal(start_time)
        if total_time < 0:
            total_time = abs(24%total_time)
        total_time = round(total_time, 2)
        commit_db("INSERT INTO activities VALUES (?, ?, ?, ?, ?, ?, ?)", [user, activity, start_time, end_time, note, total_time, date])
        return redirect(url_for('history'))

    # get activity values from database
    activities_sums = query_db("SELECT activity, SUM(total_time) total, COUNT(activity) count, date FROM activities WHERE user = (?) GROUP BY date, activity ORDER BY date DESC", [session["username"]])
    # get dates from database
    dates = query_db("SELECT date FROM activities WHERE user = (?) GROUP BY date ORDER BY date DESC", [session["username"]])
    # get notes from database
    notes = query_db("SELECT note, date FROM activities WHERE user = (?)", [session["username"]])

    """modify data structure (order might vary): 
        [{'date': .., 'activities': [{'name': .., 'hours': .., 'count': ..}, {..} ..]}, {..}]"""
    for date in dates:
        date['activities'] = []
        for activity in activities_sums:
            if activity['date'] == date['date']:
                date['activities'].append({'name': activity['activity'], 'hours': activity['total'], 'count': activity['count']})

    return render_template("history.html", dates=dates, notes=notes)

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have logged out.", "message-success")
    return redirect(url_for('login'))

@app.route("/activities")
@login_required
def activities():
    rows = query_db("SELECT SUM(activity) activity, SUM(total_time) total, COUNT(activity) count, date FROM activities WHERE user = (?) GROUP BY date", [session["username"]])
    return jsonify(rows)

if __name__ == "__main__":
    app.config['SESSION_TYPE'] = 'filesystem'

    sess.init_app(app)

app.run()