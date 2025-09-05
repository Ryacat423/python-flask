from flask import Flask, render_template, request, redirect, url_for
from routes.auth import auth_register, auth_login, auth_logout

from db import collection

app = Flask(__name__)
app.secret_key = "your-secret-key"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return auth_register()

@app.route('/login', methods=['GET', 'POST'])
def login():
    return auth_login()

@app.route('/logout')
def logout():
    return auth_logout() 

@app.route("/add", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        product_id = request.form["id"]
        product_name = request.form["name"]
        product_price = float(request.form["price"])
        new_product = {
            "_id": product_id,
            "name": product_name,
            "price": product_price
        }
        collection.insert_one(new_product)
        return redirect(url_for("add_product"))
    return render_template("add_product.html")

if __name__ == "__main__":
    app.run(debug=True)