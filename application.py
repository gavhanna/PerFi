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

    return render_template("index.html",)

@app.route("/total")
@login_required
def total():

    user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

    user_totals = db.execute("SELECT * FROM user_totals WHERE username = :user",
    user=user[0]['username'])

    user_total = user_totals[0]['bank_total'] + user_totals[0]['cash_total']

    return render_template("test.html", user=user,
    user_totals=user_totals,
    user_total=user_total)

@app.route("/transaction", methods=["GET", "POST"])
@login_required
def transaction():
    if request.method == "POST":
        user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

        if (request.form["transaction"] == 0 or
        request.form["category"] == "" or
        request.form["company"] == ""):
            return apology("fill everything out yo")

        t_type = request.form["transaction_type"]
        t_tran = request.form["transaction"]
        t_cat = request.form["category"]
        t_comp = request.form["company"]

        if request.form['transaction_type'] == "cash":
            db.execute("UPDATE user_totals SET cash_total = cash_total + :cash WHERE username = :user",
            cash=request.form['transaction'],
            user=user[0]['username'])

        if request.form['transaction_type'] == "bank":
            db.execute("UPDATE user_totals SET cash_total = bank_total + :bank WHERE username = :user",
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
        return render_template("transaction.html")



@app.route("/history")
@login_required
def history():
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


        return redirect(url_for("index"))

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        if request.form["symbol"] == "" or request.form["shares"] == "":
            return apology("please enter both a symbol and amount of shares")

        query = lookup(request.form["symbol"])
        if isinstance(query, dict) == False:
            return apology("not a valid symbol")

        user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        user_cash = user[0]["cash"]
        portfolio = db.execute("SELECT * FROM portfolio WHERE id = :id", id=session["user_id"])
        symbol = query["symbol"]
        name = query["name"]
        stock_price = query["price"]
        shares = int(request.form["shares"])
        user_id = session["user_id"]
        transaction = float("{0:.2f}".format(shares * stock_price))

        current_portfolio = db.execute("SELECT * FROM portfolio WHERE id = :id AND symbol = :symbol",
                                        id=session["user_id"],
                                        symbol=symbol)
        current_shares = current_portfolio[0]["shares"]

        if (current_shares - shares) < 0:
            return apology("can't sell more than you have...")

        if shares > 0:

            if any(d['symbol'] == symbol for d in portfolio):
                db.execute('UPDATE portfolio SET "transaction" = "transaction" - :transaction, shares = shares - :shares WHERE symbol = :symbol AND id = :id;',
                            transaction=transaction,
                            shares=shares,
                            symbol=symbol,
                            id=user_id)

                db.execute("UPDATE users SET cash = cash + :transaction WHERE id = :user_id",
                            transaction=transaction,
                            user_id=user_id)



            elif not any(d["symbol"] == symbol for d in portfolio):

                return apology("you don't have any stocks in " + symbol)


            db.execute("INSERT INTO 'history' ('id','transaction','symbol','name','shares','price') VALUES (:user_id,:transaction,:symbol,:name,-:shares,:price)",
                            user_id=int(user_id),
                            transaction=(float(transaction)),
                            symbol=symbol,
                            name=str(name),
                            shares=int(shares),
                            price=float(stock_price))

            return redirect(url_for("index"))

        else:
            apology("you don't have any money..")

        return redirect(url_for("index"))
    else:
        return render_template("sell.html")


app.run(
host=app.config.get("HOST", '0.0.0.0'),
port=app.config.get("PORT", 9000),
debug=True
)
