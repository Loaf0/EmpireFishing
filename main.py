from dateutil.utils import today
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import pypyodbc as odbc  # pip install pypyodbc
import re

app = Flask(__name__)

app.secret_key = 'your secret key'

server = 'empirefishing.database.windows.net'
database = 'EmpireFishingCSCI-4485'
dbusername = 'empirefishing'
dbpassword = '@Stockton'
connection_string = ('Driver={ODBC Driver 18 for SQL Server};Server=' + server + ',1433;Database=' + database + ';Uid=' + dbusername + ';Pwd=' + dbpassword + ';Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
conn = odbc.connect(connection_string)

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template("index.html")


@app.errorhandler(404)
def error404():
    return render_template("404.html")


@app.route('/live-bait')
def live_bait():
    return render_template("live-bait.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    
    # check if username and password were received
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:

        username = request.form['username']
        password = request.form['password']

        # Check if account exists using MySQL - Grabs from userdata table on Azure SQL Server
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM userdata WHERE username = ? AND password = ?', (username, password))

        # Fetch one record and return result
        account = cursor.fetchone()
        
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']

            # Redirect to profile
            return redirect(url_for('profile'))
        else:
            # Account doesn't exist or username/password incorrect
            msg = 'Incorrect username/password!'
            # Show the login form with message (if any)
    return render_template('login.html', msg=msg)


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
