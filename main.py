from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_mysqldb import MySQL
import pypyodbc as odbc  # pip install pypyodbc
import re

app = Flask(__name__)

app.secret_key = 'your secret key'

server = 'empirefishing.database.windows.net'
database = 'EmpireFishingCSCI-4485'
dbusername = 'empirefishing'
dbpassword = '@Stockton'
connection_string = (
        'Driver={ODBC Driver 18 for SQL Server};Server=' + server + ',1433;Database=' + database + ';Uid=' + dbusername + ';Pwd=' + dbpassword + ';Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
conn = odbc.connect(connection_string)

mysql = MySQL(app)


def require_login_status(must_be_logged_out=False, admin=False):
    # if user needs to be logged in but isn't, return to login page
    if 'loggedin' not in session.keys() and not must_be_logged_out:
        return redirect(url_for('login'))

    # if user is logged in but shouldn't be, return to profile page
    if 'loggedin' in session.keys() and must_be_logged_out:
        return redirect(url_for('profile'))

    # if user is logged in but isn't an admin, return 403 for admin-only pages
    if admin:
        username = session['username']
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM userdata WHERE username = ?', (username,))
        account = cursor.fetchone()

        if not account['admin']:
            abort(403)


@app.route('/')
def home():
    return render_template("index.html")


@app.errorhandler(404)
def error404(error):
    return render_template("404.html")


@app.route('/admin')
def admin():
    login_status = require_login_status(admin=True)
    if login_status is not None:
        return login_status

    return render_template("admin.html")


@app.route('/bait-editor', methods=['GET', 'POST'])
def bait_editor():
    login_status = require_login_status(admin=True)
    if login_status is not None:
        return login_status

    msg = ''

    cursor = conn.cursor()

    if request.method == 'POST':
        # insert/modify items:
        insert_name = request.form['insert-name']
        insert_availability = 'insert-availability' in request.form
        insert_description = request.form['insert-description']

        if insert_name:
            cursor.execute('SELECT * FROM bait WHERE name = ?', (insert_name,))
            found_bait = cursor.fetchone()

            if found_bait:
                cursor.execute('UPDATE bait SET availability = ? WHERE name = ?', (int(insert_availability), insert_name))

                if insert_description:
                    cursor.execute('UPDATE bait SET description = ? WHERE name = ?', (insert_description, insert_name))

                msg = 'Updated bait %s.' % insert_name
            else:
                cursor.execute('INSERT INTO bait (name, availability, description) VALUES (?, ?, ?)', (insert_name, int(insert_availability), insert_description))
                msg = 'Added new bait %s.' % insert_name

        # remove items
        remove_name = request.form['remove-name']

        if remove_name:
            cursor.execute('DELETE FROM bait WHERE name = ?', (remove_name,))
            msg = 'Removed bait %s.' % remove_name

    # fetch current bait table
    cursor.execute('SELECT * FROM bait')
    baits = cursor.fetchall()

    conn.commit()

    return render_template("bait-editor.html", msg=msg, baits=baits)


@app.route('/bait')
def live_bait():
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bait')
    baits = cursor.fetchall()

    return render_template("bait.html", baits=baits)


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_status = require_login_status(must_be_logged_out=True)
    if login_status is not None:
        return login_status

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


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    login_status = require_login_status()
    if login_status is not None:
        return login_status

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM userdata WHERE username = ?', (session['username'], ))
    account = cursor.fetchone()

    username = session['username']
    email = account['email']
    phone = account['phone']
    consent = account['consent']

    if request.method == 'POST' and 'consent' in request.form:
        consent = request.form['consent'] == 'on'

        cursor.execute('UPDATE userdata SET email_consent = ? WHERE username = ?;', (int(consent), username))
        conn.commit()

    return render_template("profile.html", username=username, email=email, phone=phone, consent=consent)


@app.route('/register', methods=['GET', 'POST'])
def register():
    login_status = require_login_status(must_be_logged_out=True)
    if login_status is not None:
        return login_status

    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if (request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in
            request.form):

        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        if request.form.get('consent'):  # 1 yes 0 no
            consent = 1
        else:
            consent = 0

        # Check if account exists using MySQL
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM userdata WHERE username = ?', (username, ))
        account = cursor.fetchone()

        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif len(password) < 3:
            msg = 'Password too short!'
        elif len(phone) < 12:
            msg = 'Invalid Phone Number!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:

            # Account doesn't exist and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO userdata VALUES ( ?, ?, ?, ?, ?, ?, ?)',
                           (username, password, email, consent, phone, 0, date.today()))

            # today sets the account creation date, zero is for not admin

            conn.commit()
            msg = 'You have successfully registered!'

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)


if __name__ == '__main__':
    app.run()
