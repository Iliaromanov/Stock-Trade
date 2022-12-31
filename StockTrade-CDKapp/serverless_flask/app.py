import os
from datetime import datetime

from flask import Blueprint, render_template, redirect, request, session, flash
import psycopg2
from psycopg2.sql import SQL
import psycopg2.extras
from werkzeug.exceptions import (
    default_exceptions,
    HTTPException,
    InternalServerError,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .helpers import apology, login_required, lookup, usd

app = Blueprint(
    "SockTradeApp",
    __name__,
    template_folder="./templates",
    static_folder="./styles",
    static_url_path="/styles",
)


# Get database credentials saved in Heroku env
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    db = psycopg2.connect(
        database=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
    )
    c = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Query db for users current cash
    cash_query = """
                 SELECT cash
                 FROM users
                 WHERE id = %s
                 """
    c.execute(cash_query, (user_id,))
    cash = c.fetchone()[0]

    # Query db for users owned stocks
    stocks_info_query = """
                        SELECT stock, shares
                        FROM ownedstocks
                        WHERE user_id = %s
                        ORDER BY shares DESC
                        """
    c.execute(stocks_info_query, (user_id,))
    stocks_info = c.fetchall()

    # Create a list of dictionaries containing info
    #  on each stock the user owns
    portfolio = []

    for stock in stocks_info:
        stock_portfolio = {}
        stock_info = lookup(stock["stock"])

        stock_portfolio["symbol"] = stock["stock"]
        stock_portfolio["name"] = stock_info["name"]
        stock_portfolio["share_count"] = stock["shares"]
        stock_portfolio["percent"] = stock_info["percent"]
        stock_portfolio["price"] = stock_info["price"]
        stock_portfolio["total"] = (
            stock_portfolio["share_count"] * stock_portfolio["price"]
        )

        portfolio.append(stock_portfolio)

    # Calculate user account net worth
    total_wealth = cash
    for stock_portfolio in portfolio:
        total_wealth += stock_portfolio["total"]

    # Convert to USD
    for stock in portfolio:
        stock["total"] = usd(stock["total"])
        stock["price"] = usd(stock["price"])
    db.close()
    c.close()
    return render_template(
        "index.html",
        portfolio=portfolio,
        cash=usd(cash),
        total=usd(total_wealth),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        db = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
        )
        c = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)

        # Query database for username
        query = SQL(
            """
                    SELECT *
                    FROM users
                    WHERE username = %s
                    """
        )
        c.execute(query, (username,))
        rows = c.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], password
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        db.close()
        c.close()

        flash(f"Welcome back, {username}!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    db = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
    )
    c = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm-password")

        # Ensure username was submitted.
        if not username:
            return apology("Please enter a Username to register.", 403)

        # Ensure password was submitted.
        if not password:
            return apology("Please enter a Password to register.", 403)

        # Ensure matching passwords were submitted.
        if password != confirm_password:
            return apology("Your passwords do not match.", 403)

        # Run a query to check if the username already exists.
        query = SQL(
            """
            SELECT *
            FROM users
            WHERE username = %s
            """
        )
        c.execute(query, (username,))
        users = c.fetchall()
        if len(users) != 0:
            return apology("Sorry, this username is already taken.", 403)

        insert_query = psycopg2.sql.SQL(
            """
            INSERT INTO users (username, hash, cash) VALUES (%s, %s, %s)
            """
        )
        start_cash = 10000
        c.execute(
            insert_query,
            (username, generate_password_hash(password), start_cash),
        )
        db.commit()

        # Query database for username
        query = SQL(
            """
            SELECT *
            FROM users
            WHERE username = %s
            """
        )
        c.execute(query, (username,))
        user = c.fetchone()

        # Remember which user has logged in
        session["user_id"] = user["id"]
        db.close()
        c.close()

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Provides user with stock info"""

    if request.method == "POST":
        symbol = request.form.get("symbol")

        # Ensure symbol was submitted.
        if not symbol:
            return apology("Please enter a Symbol", 403)

        stock_info = lookup(symbol)

        if stock_info is None:
            return apology("Sorry, you entered an invalid symbol.", 403)
        else:
            name = stock_info["name"]
            price = usd(stock_info["price"])
            symbol = stock_info["symbol"]

            return render_template(
                "quoted.html", name=name, price=price, symbol=symbol
            )

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    db = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
    )
    c = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == "POST":
        user_id = session["user_id"]
        time = datetime.now()
        symbol = request.form.get("symbol")
        stock_info = lookup(symbol)
        if not stock_info:
            return apology("Please enter a valid symbol", 403)

        shares = request.form.get("shares")

        # Ensure valid number of shares was submitted
        if not shares or int(shares) <= 0:
            flash("Number of shares must be a positive integer", "error")
            return apology("Number of shares must be a positive integer.", 403)
        else:
            shares = int(shares)

        total = shares * stock_info["price"]

        # Ensure the user has enough cash to complete the purchase
        user_cash_query = psycopg2.sql.SQL(
            """
                                           SELECT cash
                                           FROM users
                                           WHERE id = %s
                                           """
        )
        c.execute(user_cash_query, (user_id,))
        cash = c.fetchone()[0]

        if cash < total:
            return apology(
                "Sorry, you do not have enough cash to make this purchase."
            )

        # Record the purchase
        record_purchase_query = SQL(
            """
            INSERT INTO transactions (user_id, time, stock,
                                        shares, share_value, total_value)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
        )
        c.execute(
            record_purchase_query,
            (
                user_id,
                time,
                symbol.upper(),
                shares,
                stock_info["price"],
                total,
            ),
        )
        db.commit()

        # Update users owned-stocks
        current_shares_query = SQL(
            """
            SELECT shares
            FROM ownedStocks
            WHERE user_id = %s AND stock = %s
            """
        )
        c.execute(current_shares_query, (user_id, symbol.upper()))
        result = c.fetchone()

        # The user already has some shares of the bought stock
        if result is not None:
            current_shares = result[0]
            update_owned_stocks_query = SQL(
                """
                UPDATE ownedStocks
                SET shares = %s
                WHERE user_id = %s AND stock = %s
                """
            )
            c.execute(
                update_owned_stocks_query,
                (current_shares + shares, user_id, symbol.upper()),
            )
            db.commit()
        # The user doesn't own any of the bought stock
        else:
            update_owned_stocks_query = SQL(
                """
                INSERT INTO ownedStocks (user_id, stock, shares)
                VALUES (%s, %s, %s)
                """
            )
            c.execute(
                update_owned_stocks_query, (user_id, symbol.upper(), shares)
            )
            db.commit()

        # Update users account balance
        update_account_balance_query = SQL(
            """
            UPDATE users
            SET cash = %s
            WHERE id = %s
            """
        )
        c.execute(update_account_balance_query, (cash - total, user_id))
        db.commit()

        db.close()
        c.close()
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    db = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
    )
    c = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    user_id = session["user_id"]

    # Query the database for the users owned stocks
    stock_options_query = SQL(
        """
        SELECT stock, shares
        FROM ownedStocks
        WHERE user_id = %s
        """
    )
    c.execute(stock_options_query, (user_id,))
    result = c.fetchall()
    # Save users owned stocks and share counts in a dictionary
    stocks_owned = {}
    for row in result:
        stocks_owned[row["stock"]] = row["shares"]

    # User has submitted form
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        stock_info = lookup(symbol)
        shares = int(request.form.get("shares"))
        total = shares * stock_info["price"]
        time = datetime.now()

        # Ensure valid symbol was submitted
        if not stock_info:
            return apology("Please enter a valid symbol.", 403)

        # Ensure valid number of shares was submitted
        if (
            not type(shares) is int
            or shares <= 0
            or shares > stocks_owned[symbol]
        ):
            return apology("You do not own this number of shares.", 403)

        # Update users owned stocks info
        update_owned_stocks_query = SQL(
            """
            UPDATE ownedStocks
            SET shares = %s
            WHERE user_id = %s AND stock = %s
            """
        )
        c.execute(
            update_owned_stocks_query,
            (stocks_owned[symbol] - shares, user_id, symbol),
        )
        db.commit()

        # Remove stocks from ownedStocks table if their qty is at 0
        if stocks_owned[symbol] - shares == 0:
            clean_owned_stocks_query = SQL(
                """
                DELETE FROM ownedStocks
                WHERE shares = 0
                """
            )
            c.execute(clean_owned_stocks_query)
            db.commit()

        # Update users transactions info
        update_transactions_query = SQL(
            """
            INSERT INTO transactions (user_id, time, stock,
                                        shares, share_value, total_value)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
        )
        c.execute(
            update_transactions_query,
            (user_id, time, symbol, -1 * shares, stock_info["price"], total),
        )
        db.commit()

        # Get users current account balance
        user_cash_query = SQL(
            """
            SELECT cash
            FROM users
            WHERE id = %s
            """
        )
        c.execute(user_cash_query, (user_id,))
        cash = c.fetchone()[0]
        # Update users account balance
        update_user_cash_query = SQL(
            """
            UPDATE users
            SET cash = %s
            WHERE id = %s
            """
        )
        c.execute(update_user_cash_query, (cash + total, user_id))
        db.commit()

        db.close()
        c.close()
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html", stocks_owned=stocks_owned)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    db = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
    )
    c = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    user_id = session["user_id"]

    # Query database for users transaciton info
    transaction_info_query = SQL(
        """
        SELECT stock, shares, total_value, time
        FROM transactions
        WHERE user_id = %s
        ORDER BY time DESC
        """
    )
    c.execute(transaction_info_query, (user_id,))
    result = c.fetchall()

    # Convert price to USD and create  a list of transaction info dicts
    transactions = []
    for transaction in result:
        transaction_info = {}
        transaction_info["symbol"] = transaction["stock"]
        transaction_info["shares"] = transaction["shares"]
        transaction_info["price"] = usd(transaction["total_value"])
        transaction_info["time"] = transaction["time"]

        transactions.append(transaction_info)
    db.close()
    c.close()
    return render_template("history.html", transactions=transactions)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


if __name__ == "__main__":
    app.run()
