from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_mysqldb import MySQL
import pypyodbc as odbc
import requests
import random
import time
import math
import re
import os

app = Flask(__name__)

app.secret_key = 'your secret key'

#SQL Azure Server
server = 'empirefishingv2.database.windows.net'
database = 'EmpireFishingCSCI-4485'
dbusername = 'empirefishing'
dbpassword = '@Stockton'
connection_string = (
        'Driver={ODBC Driver 18 for SQL Server};Server=' + server + ',1433;Database=' + database + ';Uid=' + dbusername + ';Pwd=' + dbpassword + ';Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
conn = odbc.connect(connection_string)

mysql = MySQL(app)


# Mailgun API
api_key = "b87eb1e2828aef10ccb994a97375d0b6-4b670513-129e8904"
domain = "sandboxfff78680340b4054ae4daddac1b07ff2.mailgun.org"
sender = "Empire Fishing and Tackle <EmpireFishingAndTackle@sandboxfff78680340b4054ae4daddac1b07ff2.mailgun.org>"

def send_email(recipient, subject, message):
    # (because we are using for free I have to manually approve emails)
    """
    :param recipient: All array of emails who are going to be receiving message
    :type recipient: string array
    :param subject: Subject of email
    :type subject: string
    :param message: Message to be sent to users
    :type message: string
    :return:
    """
    return requests.post(
        f"https://api.mailgun.net/v3/{domain}/messages",
        auth=("api", api_key),
        data={"from": sender,
              "to": recipient,
              "subject": subject,
              "text": message})

def require_login_status(must_be_logged_out=False, must_be_admin=False, destination='profile'):
    # if user needs to be logged in but isn't, return to login page
    if 'loggedin' not in session.keys() and not must_be_logged_out:
        return redirect(url_for('login') + '?destination=' + destination)

    # if user is logged in but shouldn't be, return to profile page
    if 'loggedin' in session.keys() and must_be_logged_out:
        return redirect('/' + destination)

    # if user is logged in but isn't an admin, return 403 for admin-only pages
    if must_be_admin and not session['admin']:
        abort(403)


@app.route('/')
def home():
    return render_template("index.html", session=session)


@app.route('/lineSpooling')
def lineSpooling():
    return render_template("lineSpooling.html", session=session)


@app.errorhandler(404)
def error404(error):
    return render_template("404.html", session=session)


@app.route('/admin')
def admin():
    login_status = require_login_status(must_be_admin=True, destination='admin')
    if login_status is not None:
        return login_status

    return render_template("admin.html", session=session)


@app.route('/bait-editor', methods=['GET', 'POST'])
def bait_editor():
    login_status = require_login_status(must_be_admin=True, destination='bait-editor')
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
                cursor.execute('UPDATE bait SET availability = ? WHERE name = ?',
                               (int(insert_availability), insert_name))

                if insert_description:
                    cursor.execute('UPDATE bait SET description = ? WHERE name = ?', (insert_description, insert_name))

                msg = 'Updated bait %s.' % insert_name
            else:
                cursor.execute('INSERT INTO bait (name, availability, description) VALUES (?, ?, ?)',
                               (insert_name, int(insert_availability), insert_description))
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

    return render_template("bait-editor.html", session=session, msg=msg, baits=baits)


@app.route('/bait')
def live_bait():
    must_be_available = request.args.get('available', default='false') == "true"

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bait' + (' WHERE availability = 1' if must_be_available else ''))
    baits = cursor.fetchall()
    baits.sort(key=lambda x: x['name'])

    return render_template("bait.html", session=session, baits=baits)


@app.route('/brand-editor', methods=['GET', 'POST'])
def brand_editor():
    login_status = require_login_status(must_be_admin=True, destination='brand-editor')
    if login_status is not None:
        return login_status

    msg = ''

    cursor = conn.cursor()

    if request.method == 'POST':
        # insert/modify items:
        insert_logo = request.files.getlist('insert-logo')[0]
        insert_logo_name = insert_logo.filename
        insert_name = request.form.get('insert-name')
        insert_description = request.form.get('insert-description')

        if insert_name:
            cursor.execute('SELECT * FROM brands WHERE name = ?', (insert_name,))
            found_brand = cursor.fetchone()

            if found_brand:
                if insert_logo_name:
                    cursor.execute('UPDATE brands SET logo = ? WHERE name = ?', (insert_logo_name, insert_name))

                if insert_description:
                    cursor.execute('UPDATE brands SET description = ? WHERE name = ?',
                                   (insert_description, insert_name))

                msg = 'Updated brand %s.' % insert_name
            else:
                cursor.execute('INSERT INTO brands (logo, name, description) VALUES (?, ?, ?)',
                               (insert_logo_name, insert_name, insert_description))
                msg = 'Added new brand %s.' % insert_name

            # upload logo to brands folder
            if insert_logo:
                # create brands folder if it doesn't already exist
                if not os.path.exists("static/images/brands"):
                    os.mkdir("static/images/brands")

                insert_logo.save("static/images/brands/" + insert_logo_name)

        # remove items
        remove_name = request.form.get('remove-name')

        if remove_name:
            cursor.execute('DELETE FROM brands WHERE name = ?', (remove_name,))
            msg = 'Removed brand %s.' % remove_name

    # fetch current brand table
    cursor.execute('SELECT * FROM brands')
    brands = cursor.fetchall()

    conn.commit()

    return render_template("brand-editor.html", session=session, msg=msg, brands=brands)


@app.route('/brands')
def brands_list():
    sort = request.args.get('sort', default='random')

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM brands')
    brands = cursor.fetchall()

    if sort == 'alphabetical':
        brands.sort(key=lambda x: x['name'])
    else:
        random.shuffle(brands)

    return render_template("brands.html", session=session, brands=brands)


@app.route('/community')
def community():
    return render_template("community.html", session=session)


@app.route('/shop')
def shop():
    return render_template("shop.html", session=session)


# WILL BE REMOVED ONLY FOR TESTING WILL BE INTEGRATED INTO THE SHOP
@app.route('/product')
def product():
    return render_template("product.html", session=session)


# WILL BE REMOVED ONLY FOR TESTING WILL BE INTEGRATED INTO THE SHOP
@app.route('/cart')
def cart():
    return render_template("cart.html", session=session)


@app.route('/fishingSpots', methods=['GET', 'POST'])
def fishingSpots():
    lat = []
    long = []
    label = []

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM markedFishingSpots')
    spot = cursor.fetchone()
    while spot is not None:
        lat.append(spot['lat'])
        long.append(spot['long'])
        label.append(spot['label'])
        spot = cursor.fetchone()

    locations = '['
    count = 0
    while count < len(label):
        locations += '{"lat":' + str(lat[count]) + ',"long":' + str(long[count]) + ',"label":"' + str(
            label[count]) + '"},'
        count += 1
    locations = locations[:-1]
    locations += ']'

    return render_template("fishingSpots.html", locations=locations)


@app.route('/map-editor', methods=['GET', 'POST'])
def map_editor():
    login_status = require_login_status(must_be_admin=True, destination='map-editor')
    if login_status is not None:
        return login_status

    msg = ''

    cursor = conn.cursor()

    if request.method == 'POST':
        # insert/modify items:
        insert_label = request.form['insert-label']
        insert_longitude = request.form['insert-long']
        insert_latitude = request.form['insert-lat']

        if insert_label:
            cursor.execute('SELECT * FROM markedFishingSpots WHERE label = ?', (insert_label,))
            found_label = cursor.fetchone()

            if found_label:
                cursor.execute('UPDATE markedFishingSpots SET long = ? WHERE label = ?',
                               (insert_longitude, insert_label))

                if insert_latitude:
                    cursor.execute('UPDATE markedFishingSpots SET lat = ? WHERE label = ?',
                                   (insert_latitude, insert_label))
                msg = 'Updated marker %s.' % insert_label
            else:
                cursor.execute('INSERT INTO markedFishingSpots (lat, long, label) VALUES (?, ?, ?)',
                               (insert_latitude, insert_longitude, insert_label))
                msg = 'Added new marker %s.' % insert_label

        # remove marker
        remove_marker = request.form['remove-label']

        if remove_marker:
            cursor.execute('DELETE FROM markedFishingSpots WHERE label = ?', (remove_marker,))
            msg = 'Removed marker %s.' % remove_marker

    # fetch current marker table
    cursor.execute('SELECT * FROM markedFishingSpots')
    markers = cursor.fetchall()

    conn.commit()

    return render_template("map-editor.html", session=session, msg=msg, markers=markers)


@app.route('/home')
def home_redirect():
    return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
    destination = request.args.get('destination', default='profile')

    login_status = require_login_status(must_be_logged_out=True, destination=destination)
    if login_status is not None:
        return login_status

    msg = ''

    # check if username and password were received
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'destination' in request.form:
        username = request.form['username']
        password = request.form['password']
        destination = request.form['destination']

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

            # add admin attribute to session if user is an admin
            session['admin'] = bool(account['admin'])

            # Redirect to desired page (profile by default)
            return redirect('/' + destination)
        else:
            # Account doesn't exist or username/password incorrect
            msg = 'Incorrect username/password!'
            # Show the login form with message (if any)
    return render_template('login.html', destination=destination, session=session, msg=msg)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('admin', None)
    return redirect(url_for('home'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    login_status = require_login_status()
    if login_status is not None:
        return login_status

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM userdata WHERE username = ?', (session['username'],))
    account = cursor.fetchone()

    username = session['username']
    email = account['email']
    phone = account['phone']
    consent = account['consent']

    if request.method == 'POST' and 'consent' in request.form:
        consent = request.form['consent'] == 'on'

        cursor.execute('UPDATE userdata SET email_consent = ? WHERE username = ?;', (int(consent), username))
        conn.commit()

    return render_template("profile.html", session=session, username=username, email=email, phone=phone,
                           consent=consent)


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
        cursor.execute('SELECT * FROM userdata WHERE username = ?', (username,))
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
                           (username, password, email, consent, phone, 0, math.floor(time.time())))

            # today sets the account creation date, zero is for not admin

            conn.commit()
            msg = 'You have successfully registered!'

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', session=session, msg=msg)


if __name__ == '__main__':
    app.run()


