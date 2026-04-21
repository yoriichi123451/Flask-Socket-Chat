from os import error

from flask import Flask, render_template, request,session,redirect, url_for, flash
from flask_socketio import SocketIO, send, emit
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.debug = True
app.config["SECRET_KEY"] = "Socket5196"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"
app.secret_key = "SecretKey22814885242"
socketio = SocketIO(app)
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50),nullable=False)
    password = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.String(500), nullable=True)
    avatar_url = db.Column(db.String, nullable=True, default="/images/default_avatar.png")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("username"):
        return redirect(url_for("login"))
    #if request.method == "POST":
        #Валидация и сохранение при необходимости
    user = db.get_or_404(User, session.get("user_id"))
    return render_template("index.html", user=user)

@app.route("/chat")
def chats():
    if not session.get("username"):
        return redirect(url_for("login"))
    return render_template("chat.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        username = request.form["username"]
        user_data = dict(request.form)
        if not username:
            flash("Введите ваше имя пользователя", "error")
            return render_template(
                "register.html",
                **user_data
            )
        password = request.form["password"]
        if not password:
            flash("Придумайте пароль", "error")
            return render_template(
                "register.html",
                **user_data
            )
        elif not 8 <= len(password) <= 24:
            flash("Длина пароля должна быть от 8 до 24 символов", "error")
            return render_template(
                "register.html",
                **user_data
            )
        elif password != request.form["check-password"]:
            flash("Пароли не совпадают", "error")
            return render_template(
                "register.html",
                )
        password_hash = generate_password_hash(password)
        user = User(username=username, password=password_hash)

        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("index"))
        else:
            flash("Неверный логин или пароль", "error")
            return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/settings")
def settings():
    if not session.get("username"):
        return redirect(url_for("login"))
    return render_template("chat.html")

@socketio.on('message')
def handle_message(data):
    print('received message: ' + data)
    send(data, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, allow_unsafe_werkzeug=True)