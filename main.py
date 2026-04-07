import os

from flask import Flask, send_file, 

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('src/templates/index.html')

@app.route("/login")
def contato():
    return render_template('src/templates/login.html')

def main():
    app.run(debug="True", host'127.0.0.1', port=5000)

if __name__ == "__main__":
    main()
