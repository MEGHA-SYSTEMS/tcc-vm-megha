import os

from flask import render_template, Flask

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

def main():
    app.run(port=int(os.environ.get('PORT', 80)))

if __name__ == "__main__":
    main()
