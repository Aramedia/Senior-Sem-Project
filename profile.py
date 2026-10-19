from flask import Flask

app = Flask(__name__)

@app.route('/profile')
def profile():
    return 'This is the current profile page</p>'

