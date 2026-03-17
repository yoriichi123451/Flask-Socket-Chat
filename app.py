from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit


app = Flask(__name__)
app.config["SECRET_KEY"] = "Socket5196"
socketio = SocketIO(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat")
def chats():
    return render_template("chat.html")

@socketio.on('message')
def handle_message(data):
    print('received message: ' + data)
    send(data, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, allow_unsafe_werkzeug=True)