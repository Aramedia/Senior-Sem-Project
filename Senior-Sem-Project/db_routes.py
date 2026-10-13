# sqlite in flask routes 
import sqlite3
from flask import g

DATABASE = '/database.sqbpro' # route to database file
#sqlite3 link instead 

def get_db(): # function to get database connection
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext # function to close database connection
def close_connection(exception):
    db = getattr(g, 'profile_database', None) 
    if db is not None:
        db.close()

@app.route('/users') # route to get all users from database
def index():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    return str(users)

