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

if __name__ == '__main__':
    app.run()
