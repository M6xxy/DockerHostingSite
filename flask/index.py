from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO
from flask_login import *
import docker
import threading


app = Flask(__name__)
app.secret_key = "scrt_key"
socketio = SocketIO(app)
client = docker.from_env() 

#Login Manager stuff
loginManager = LoginManager()
loginManager.init_app(app)
loginManager.login_view = "login"

#Test DB
users =  {
    "test": {"password": "1234"}
}

#Logged user
class User(UserMixin):
    def __init__(self,id):
        self.id = id

    def __repr__(self):
        return f"<User {self.id}"

#User Loader
@loginManager.user_loader
def loadUser(userId):
    if userId in users:
        return User(userId)
    return None


#Webpage
@app.route('/')
def home():
    return render_template("home.html")

@app.route('/hosting')
def hosting():
    return render_template("hostingInfo.html")

@app.route('/panel')
@login_required
def panel():
    return render_template("hosting.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/login', methods=["GET","POST"])
def login():
    #Collect Data POST
    if request.method == "POST":
        username = request.form.get("logUsername")
        password = request.form.get("logPassword")
        
        #Check if user exists
        if username in users and users[username]["password"] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for("panel"))
        #Wrong Details
        return "Invalid Login Info"
    #Display Data GET
    return render_template("login.html")

#Minecraft Server 
MINECRAFT_CONTAINER = "mc_server"
MINECRAFT_IMAGE = "itzg/minecraft-server"


def get_or_create_container():
    try:
        container = client.containers.get(MINECRAFT_CONTAINER)
    except docker.errors.NotFound:
        container = client.containers.run(
            MINECRAFT_IMAGE,
            name=MINECRAFT_CONTAINER,
            environment={"EULA": "TRUE", "MEMORY": "2G"},
            ports={"25565/tcp": 25565},
            stdin_open=True,
            tty=True,
            detach=True
        )
    return container


@app.route("/serverStart", methods=["POST"])
def mc_server_start():
    container = get_or_create_container()
    container.reload()
    if container.stats != "running":
        
        #Start Servver
        container.start()
        
        #Create thread for server logs
        t = threading.Thread(target=getServerLogs)
        t.start()
        
        return jsonify({"status": "starting"})
    return jsonify({"status": "already running"})

@app.route("/serverStop", methods=["POST"])
def mc_server_stop():
    container = get_or_create_container()
    container.reload()
    if container.status == "running":
        container.stop()
        return jsonify({"status": "stopped"})
    return jsonify({"status": "not running"})

def getServerLogs():
    container = client.containers.get("mc_server")
    #Get container logss
    logStream = container.logs(stream=True,follow=True)
    buffer = ""
    #Fix console returning single letterss
    for chunk in logStream:
        chunk = chunk.decode('utf-8')
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n",1)
            socketio.emit('console', {'data': line.strip()})
    
#DEBUG STUFF
if __name__ == '__main__':
    
    
    #Run App with socketIO
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=True, allow_unsafe_werkzeug=True)

