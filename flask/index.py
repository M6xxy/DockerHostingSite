from flask import Flask, render_template, jsonify
import docker

app = Flask(__name__)
client = docker.from_env() 


#Webpage
@app.route('/')
def home():
    return render_template("home.html")

@app.route('/hosting')
def hosting():
    return render_template("hosting.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/login')
def login():
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
        container.start()
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

#DEBUG STUFF
if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, use_reloader=True)
