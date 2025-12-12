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
            return redirect(url_for("hosting"))
        #Wrong Details
        return render_template("login.html", alert_msg="ERROR:WRONG LOGIN INFO")
    #Display Data GET
    return render_template("login.html")

@app.route('/register', methods=["POST"])
def register():
    username = request.form.get("regUsername")
    password = request.form.get("regPassword")

    # Check if user already exists
    if username in users:
        return render_template("login.html", alert_msg="ERROR: Username already exists")

    # Add new user to the "database"
    users[username] = {"password": password}

    # Automatically log in the new user
    user = User(username)
    login_user(user)

    return redirect(url_for("hosting"))


#Minecraft Server 
MINECRAFT_CONTAINER = "mc_server"
MINECRAFT_IMAGE = "itzg/minecraft-server"
pyRamServer = "NULL"

def get_or_create_container(ramAmount):
    #Open Container
    try:
        container = client.containers.get(MINECRAFT_CONTAINER)
    except docker.errors.NotFound:
        container = client.containers.run(
            MINECRAFT_IMAGE,
            name=MINECRAFT_CONTAINER,
            environment={"EULA": "TRUE", "MEMORY": ramAmount,"USE_AIKAR_FLAGS": "true"},
            ports={"25565/tcp": 25565},
            stdin_open=True,
            tty=True,
            detach=True
        )
    return container


@app.route("/serverSelect", methods=["POST"])
def mc_server_select():
    global pyRamServer
    #If new ram selected kill container
    if(pyRamServer != request.form.get("ram")):
        try:
            container = client.containers.get(MINECRAFT_CONTAINER)
            container.reload()
            container.remove(force=True)
        except docker.errors.NotFound:
            pass    
        #Get ram
        pyRamServer = request.form.get("ram")
        print("PYRAM DETECTED: ", pyRamServer, flush=True)
    
    return render_template("hosting.html")

@app.route("/serverStart", methods=["POST"])

def mc_server_start():
    container = get_or_create_container(pyRamServer)
    container.reload()
    if container.stats != "Running":
        
        #Start Servver
        container.start()
        
        #Create thread for server logs
        t = threading.Thread(target=getServerLogs)
        t.start()
        
        return jsonify({"status": "Running"})
    return jsonify({"status": "Already running"})

@app.route("/serverStop", methods=["POST"])
def mc_server_stop():
    container = client.containers.get(MINECRAFT_CONTAINER)
    container.reload()
    if container.status == "running":
        container.stop()
        container.remove(force=True)
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

