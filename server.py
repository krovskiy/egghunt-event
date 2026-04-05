from flask import Flask, render_template

app = Flask(__name__, static_folder='./src', static_url_path='/', template_folder='./src')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/rules")
def rules():
    return render_template("/rules/index.html")

@app.route("/create-egg")
def create_egg():
    return render_template("/create-egg/index.html")

@app.route("/my-eggs")
def my_eggs():
    return render_template("/my-eggs/index.html")

if __name__ == "__main__":
    app.run(debug=True)