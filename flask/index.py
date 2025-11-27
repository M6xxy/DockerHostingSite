from flask import Flask, render_template, jsonify
import docker

app = Flask(__name__)
client = docker.from_env() 

MINECRAFT_CONTAINER = "mc_server"

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
@app.route("/serverStart", methods=["POST"])
def mc_server_start():
    container = client.containers.get(MINECRAFT_CONTAINER)
    if container.stats != "running":
        container.start
        return jsonify({"status": "starting"})
    return jsonify({"status": "already running"})

@app.route("/serverStop")
def mc_server_stop():
    container = client.containers.get(MINECRAFT_CONTAINER)
    if container.stats == "running":
        container.start
        return jsonify({"status": "stopped"})
    return jsonify({"status": "not running"})

#DEBUG STUFF
if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, use_reloader=True)
