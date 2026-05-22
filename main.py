import os

from flask import render_template, Flask

app = Flask(__name__)

@app.route("/")
def index():
   nome = "PoupeMais.com.br"
   return render_template('index.html', site = nome)

@app.route("/login")
def login():
    nome = 'PoupeMais'
    return render_template('login/login.html')

def main():
    app.run(port=int(os.environ.get('PORT', 80)))

if __name__ == "__main__":
    main()
