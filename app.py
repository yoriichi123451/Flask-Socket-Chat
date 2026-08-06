from os import error

from flask import Flask, render_template, request,session,redirect, url_for, flash
from flask_socketio import SocketIO, send, emit, join_room, leave_room
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
    avatar_url = db.Column(db.String, nullable=True, default="/images/default_avatar.svg")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False) #private and group
    name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    members = db.relationship("ChatMember", backref="chat", lazy=True)
    messages = db.relationship("Message", backref="chat", lazy=True)

class ChatMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User", foreign_keys=[user_id])
    joined_at = db.Column(db.DateTime, server_default=db.func.now())

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    sender = db.relationship("User", foreign_keys=[sender_id])
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, server_default=db.func.now())


with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user = db.get_or_404(User, session.get("user_id"))
    if request.method == "POST":
        user.username = request.form.get("username")
        user.bio = request.form.get("bio")
        if request.form.get("delete_avatar"):
            user.avatar_url = "images/default_avatar.svg"
            session["avatar_url"] = "images/default_avatar.svg"
        file = request.files.get("avatar")
        if file and file.filename != "":
            filename = file.filename
            file.save(f"static/avatars/{filename}")
            user.avatar_url = f"avatars/{filename}"
            session["avatar_url"] = f"avatars/{filename}"
        db.session.commit()
        session["username"] = user.username
        return redirect(url_for("index"))
    return render_template("index.html", user=user)

@app.route("/chats")
def chats():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user_chats = db.session.query(Chat).join(ChatMember).filter(
        ChatMember.user_id == uid
    ).order_by(Chat.created_at.desc()).all()
    users = User.query.filter(User.id != uid).all()
    chats_data = []
    for chat in user_chats:
        if chat.type == "private":
            other = ChatMember.query.filter(
                ChatMember.chat_id == chat.id,
                ChatMember.user_id != uid
            ).first()
            name = other.user.username  if other and other.user else "Неизвестный"
        else:
            name = chat.name
        chats_data.append({
            "chat": chat,
            "name": name,
            "members_count": len(chat.members)
        })
    return render_template("chats.html", chats_data=chats_data, users=users)

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
            session["avatar_url"] = user.avatar_url
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
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("chats.html")

@app.route("/chat/<int:chat_id>")
def chat_view(chat_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=session["user_id"]).first_or_404()
    chat = Chat.query.get_or_404(chat_id)
    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.sent_at).all()
    return render_template("chatview.html", chat=chat, messages=messages)

@socketio.on('join')
def on_join(data):
    chat_id = data["chat_id"]
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=session["user_id"]).first()
    if not member:
        return
    join_room(f"chat_{chat_id}")
    emit("system", {'text':"Пользователь присоединился к чату"}, room=f"chat_{chat_id}")

@socketio.on('message')
def handle_message(data):
    chat_id = data["chat_id"]
    content = data["content"]
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=session["user_id"]).first()
    if not member:
        return
    msg = Message(chat_id=chat_id, sender_id=session["user_id"], content=content)
    db.session.add(msg)
    db.session.commit()
    emit(
        "message", {
        'content':content,
        'sender':session["username"],
        'sent_at':msg.sent_at.isoformat()
        }, room=f"chat_{chat_id}")

@app.route("/chat/private/<int:target_user_id>", methods=["POST"])
def open_private_chat(target_user_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    existing = db.session.query(Chat).join(ChatMember).filter(
        Chat.type == "private",
        ChatMember.user_id == uid
    ).filter(Chat.id.in_(
        db.session.query(ChatMember.chat_id).filter_by(user_id=target_user_id)
    )).first()
    if existing:
        return redirect(url_for("chat_view", chat_id=existing.id))
    chat = Chat(type="private")
    db.session.add(chat)
    db.session.flush()
    db.session.add(ChatMember(chat_id=chat.id, user_id=uid))
    db.session.add(ChatMember(chat_id=chat.id, user_id=target_user_id))
    db.session.commit()
    return redirect(url_for("chat_view", chat_id=chat.id))

@app.route("/chat/group", methods=["POST"])
def create_group():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    name = request.form.get("name", "Группа")
    member_ids = request.form.getlist("members")
    chat = Chat(type="group", name=name)
    db.session.add(chat)
    db.session.flush()
    all_members = set(member_ids) | {session["user_id"]}
    for uid in all_members:
        db.session.add(ChatMember(chat_id=chat.id, user_id=int(uid)))
    db.session.commit()
    return redirect(url_for("chat_view", chat_id=chat.id))

if __name__ == "__main__":
    socketio.run(app, allow_unsafe_werkzeug=True)