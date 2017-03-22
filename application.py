from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir
from passlib.context import CryptContext
from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["euro"] = euro

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



# configure CS50 Library to use SQLite database
# db = SQL("sqlite:///finance.db")
db = SQL("sqlite:///perfi.db")

pwd_context = CryptContext(
    # Replace this list with the hash(es) you wish to support.
    # this example sets pbkdf2_sha256 as the default,
    # with additional support for reading legacy des_crypt hashes.
    schemes=["pbkdf2_sha256", "des_crypt"],

    # Automatically mark all but first hasher in list as deprecated.
    # (this will be the default in Passlib 2.0)
    deprecated="auto",

    # Optionally, set the number of rounds that should be used.
    # Appropriate values may vary for different schemes,
    # and the amount of time you wish it to take.
    # Leaving this alone is usually safe, and will use passlib's defaults.
    ## pbkdf2_sha256__rounds = 29000,
    )



@app.route("/")
@login_required
def index():
    return redirect(url_for("total"))

@app.route("/test", methods=["GET"])
@login_required
def test():
    user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
    username=user[0]["username"]

    categories = db.execute("SELECT * FROM category WHERE username = :username", username=username)
    catArray = []
    for cat in categories:
        catArray.append(cat["category"])

    transactions = db.execute("SELECT * FROM 'user_transactions' WHERE username = :username", username=username)


    totalsArray = []

    for tran in transactions:
        totalsArray.append(tran['transaction'])

    

    # for item in transactions:
    #     for cat in catArray:
    #         if item["category"] == cat:
    #             totalsDict[item['category']] = int(item['transaction'])

    # testDict = {
    #     "values": [20, 20, 20, 20, 20],
    #     "labels": catArray,
    #     "type": "pie"
    # }



    testDict = {
        "x": catArray,
        "y": ['1', '5', '3', '6', '4'],
        'type': 'bar'
    }


    return render_template("test.html",
            test=testDict,
            test3=transactions,
            #test4=catArray,
            test2=totalsArray
            )



@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Manage user settings"""

    user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
    username=user[0]["username"]

    if request.method == "POST":

        add_category = request.form["add-category"]
        add_company = request.form["add-company"]

        if (add_category == "" and
            add_company == ""):
            return apology("enter either a company or category name to add")
        else:
            if (not add_category == ""):
                db.execute("INSERT INTO category (username, category) VALUES (:username, :add_category)",
                username=username,
                add_category=add_category)

            if (not add_company == ""):
                db.execute("INSERT INTO company (username, company) VALUES (:username, :add_company)",
                username=username,
                add_company=add_company)

            return redirect(url_for("settings"))

        return render_template("settings.html")

    else:
        categories = db.execute("SELECT * FROM category WHERE username = :username", username = user[0]['username'])
        companies = db.execute("SELECT * FROM company WHERE username = :username", username = user[0]['username'])

        return render_template("settings.html", categories=categories,
        companies=companies)

@app.route("/total")
@login_required
def total():
    """View user total"""

    user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

    user_totals = db.execute("SELECT * FROM user_totals WHERE username = :user",
    user=user[0]['username'])

    user_total = user_totals[0]['bank_total'] + user_totals[0]['cash_total']

    return render_template("total.html", user=user,
    user_totals=user_totals,
    user_total=user_total)

@app.route("/transaction", methods=["GET", "POST"])
@login_required
def transaction():
    """Make a transaction"""

    user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
    if request.method == "POST":

        if (request.form["transaction"] == 0 or
        request.form["category"] == "" or
        request.form["company"] == ""):
            return apology("fill everything out yo")

        t_type = request.form["transaction_type"]
        t_tran = str(request.form["transaction"])
        print(t_tran)
        t_cat = request.form["category"]
        t_comp = request.form["company"]

        if request.form['transaction_type'] == "cash":
            db.execute("UPDATE user_totals SET cash_total = cash_total - :cash WHERE username = :user",
            cash=request.form['transaction'],
            user=user[0]['username'])

        if request.form['transaction_type'] == "bank":
            db.execute("UPDATE user_totals SET bank_total = bank_total - :bank WHERE username = :user",
            bank=request.form['transaction'],
            user=user[0]['username'])

        db.execute("INSERT INTO user_transactions VALUES (:user,:type, :tran, CURRENT_TIMESTAMP, :cat, :comp)",
        user=user[0]['username'],
        type=t_type,
        tran=t_tran,
        cat=t_cat,
        comp=t_comp)


        print(session['user_id'])

        return redirect(url_for("history"))
    else:
        categories = db.execute("SELECT * FROM category WHERE username = :username", username = user[0]['username'])
        companies = db.execute("SELECT * FROM company WHERE username = :username", username = user[0]['username'])

        return render_template("transaction.html", categories=categories,
        companies=companies)



@app.route("/history")
@login_required
def history():
    """View user histoy"""
    user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

    history = db.execute("SELECT * FROM user_transactions WHERE username = :name", name=user[0]['username'])

    return render_template("history.html", history=history,
    user=user)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":

        if request.form["username"] == "" or request.form["password"] == "" or request.form["confirm_password"] != request.form["password"]:
            return render_template("apology.html")



        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) >= 1:
            return apology("username already exists")

        # hash the users password
        pw_hash = pwd_context.hash(request.form["password"])

        # insert username and hased pw into db
        db.execute("INSERT INTO users (username, hash) VALUES(:username, :password)", username=request.form["username"], password=pw_hash)
        db.execute("INSERT INTO user_totals (username, bank_total, cash_total) VALUES (:username, :bank, :cash)",
        username=request.form['username'],
        bank=request.form['bank'],
        cash=request.form['cash'])

        # adding default category/company names for user to the db
        db.execute("INSERT INTO category (username, category) VALUES (:username, 'Food')", username=request.form['username'])
        db.execute("INSERT INTO category (username, category) VALUES (:username, 'Transport')", username=request.form['username'])
        db.execute("INSERT INTO company (username, company) VALUES (:username, 'Tesco')", username=request.form['username'])
        db.execute("INSERT INTO company (username, company) VALUES (:username, 'Lidl')", username=request.form['username'])
        db.execute("INSERT INTO company (username, company) VALUES (:username, 'Cost-Cutter')", username=request.form['username'])
        db.execute("INSERT INTO company (username, company) VALUES (:username, 'Wrights (Marino)')", username=request.form['username'])


        return redirect(url_for("index"))

    else:
        return render_template("register.html")


app.run(
host=app.config.get("HOST", '0.0.0.0'),
port=app.config.get("PORT", 9000),
debug=True
)
