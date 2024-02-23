from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

app = Flask(__name__)

app.secret_key = 'your secret key'

app.config['MYSQL_HOST'] = 'empirefishing.database.windows.net'
app.config['MYSQL_USER'] = 'empirefishing'
app.config['MYSQL_PASSWORD'] = '@Stockton'
app.config['MYSQL_DB'] = 'EmpireFishingCSCI-4485'
# port for the empire fishing database is 1433

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template("index.html")

@app.errorhandler(404)
def error404(error):
    return render_template("404.html")

@app.route('/live-bait')
def live_bait():
    return render_template("live-bait.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    # placeholder login info
    session['loggedin'] = True
    session['username'] = "test"

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    # if user is not logged in, return to login screen
    if 'loggedin' not in session.keys():
        return redirect(url_for('login'))

    username = session['username']
    email = "(placeholder)"
    phone = "(placeholder)"

    return render_template("profile.html", username=username, email=email, phone=phone)

@app.route('/register')
def register():
    return render_template("register.html")

if __name__ == '__main__':
    app.run()
