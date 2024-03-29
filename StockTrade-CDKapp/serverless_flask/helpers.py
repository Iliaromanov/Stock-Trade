import requests
import urllib.parse

from flask import redirect, render_template, session, flash
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def percent(value: float) -> tuple:
    """Formats float value to percent and denotes colour of value in table"""
    rounded = round(100 * value, 3)
    if rounded < 0:
        return ("red", f"-%{-1*rounded}")
    elif rounded == 0.0:
        return ("grey", "%0.00")
    else:
        return ("green", f"%{rounded}")


def usd(value: float) -> str:
    """Format value as USD."""
    return f"${value:,.2f}"


def lookup(symbol: str) -> dict:
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = (
            "pk_416fe4a246914cb594e7deeda6251bf5"  # os.environ.get("API_KEY")
        )
        response = requests.get(
            f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"  # noqa
        )
        response.raise_for_status()
    except requests.RequestException:
        flash(
            "IEX is currently under maintenance. Sorry for the inconvenience",
            "error",
        )
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"],
            "percent": percent(float(quote["changePercent"])),
        }
    except (KeyError, TypeError, ValueError):
        return None


def apology(message: str, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return (
        render_template("apology.html", top=code, bottom=escape(message)),
        code,
    )
