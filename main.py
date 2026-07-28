import os

from flask import render_template, Flask

app = Flask(__name__)

@app.route("/")
def index():
    nome = 'poupemais.com'
    return render_template('index.html', site = nome)

@app.route("/login")
def login():
    return render_template('login/login.html')

@app.route("/localizacao")
def localizacao():
    return render_template('pages/localizacao.html')    

def main():
    app.run(port=int(os.environ.get('PORT', 80)))

if __name__ == "__main__":
    main()

