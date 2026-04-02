from flask import Flask, render_template, request, redirect, session
import os, json

app = Flask(__name__)
app.secret_key = "secret123"

BASE_UPLOAD = "static/videos"
DATA_FILE = "data.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def ensure_user(data, user):
    if "users" not in data:
        data["users"] = {}

    if user not in data["users"]:
        data["users"][user] = {
            "followers": [],
            "following": [],
            "bio": ""
        }

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].lower()
        session["user"] = username

        data = load_data()
        ensure_user(data, username)
        save_data(data)

        os.makedirs(os.path.join(BASE_UPLOAD, username), exist_ok=True)
        return redirect("/home")

    return render_template("login.html")

@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")

    data = load_data()
    videos = []

    for user in os.listdir(BASE_UPLOAD):
        path = os.path.join(BASE_UPLOAD, user)

        if os.path.isdir(path):
            for v in os.listdir(path):
                key = f"{user}/{v}"

                if key not in data:
                    data[key] = {"likes":0,"comments":[],"saved":[],"liked_by":[]}

                videos.append((user, v, data[key]))

    save_data(data)
    return render_template("home.html", videos=videos)

@app.route("/following")
def following():
    user = session["user"]
    data = load_data()

    following = data["users"][user]["following"]
    videos = []

    for u in following:
        folder = os.path.join(BASE_UPLOAD, u)
        if os.path.exists(folder):
            for v in os.listdir(folder):
                key = f"{u}/{v}"
                if key not in data:
                    data[key] = {"likes":0,"comments":[],"saved":[],"liked_by":[]}
                videos.append((u,v,data[key]))

    save_data(data)
    return render_template("home.html", videos=videos)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["video"]
    user = session["user"]
    file.save(os.path.join(BASE_UPLOAD, user, file.filename))
    return redirect("/home")

@app.route("/like/<path:v>")
def like(v):
    data = load_data()
    user = session["user"]
    pos = request.args.get("pos")

    if v not in data:
        data[v] = {"likes":0,"comments":[],"saved":[],"liked_by":[]}

    if user in data[v]["liked_by"]:
        data[v]["liked_by"].remove(user)
        data[v]["likes"] -= 1
    else:
        data[v]["liked_by"].append(user)
        data[v]["likes"] += 1

    save_data(data)
    return redirect(f"/home#{pos}" if pos else "/home")

@app.route("/comment/<path:v>", methods=["POST"])
def comment(v):
    data = load_data()
    user = session["user"]
    text = request.form["text"]
    pos = request.form.get("pos")

    if v not in data:
        data[v] = {"likes":0,"comments":[],"saved":[],"liked_by":[]}

    data[v]["comments"].append(f"{user}: {text}")
    save_data(data)

    return redirect(f"/home#{pos}" if pos else "/home")

@app.route("/save/<path:v>")
def save(v):
    data = load_data()
    user = session["user"]
    pos = request.args.get("pos")

    if v not in data:
        data[v] = {"likes":0,"comments":[],"saved":[],"liked_by":[]}

    if user not in data[v]["saved"]:
        data[v]["saved"].append(user)

    save_data(data)
    return redirect(f"/home#{pos}" if pos else "/home")

@app.route("/follow/<username>")
def follow(username):
    data = load_data()
    user = session["user"]

    ensure_user(data, user)
    ensure_user(data, username)

    if user not in data["users"][username]["followers"]:
        data["users"][username]["followers"].append(user)
        data["users"][user]["following"].append(username)

    save_data(data)
    return redirect(f"/profile/{username}")

@app.route("/unfollow/<username>")
def unfollow(username):
    data = load_data()
    user = session["user"]

    if user in data["users"][username]["followers"]:
        data["users"][username]["followers"].remove(user)
        data["users"][user]["following"].remove(username)

    save_data(data)
    return redirect(f"/profile/{username}")

@app.route("/profile/<username>")
def profile(username):
    data = load_data()
    current = session["user"]

    ensure_user(data, username)

    folder = os.path.join(BASE_UPLOAD, username)
    videos = os.listdir(folder) if os.path.exists(folder) else []

    followers = len(data["users"][username]["followers"])
    following = len(data["users"][username]["following"])
    is_following = current in data["users"][username]["followers"]
    bio = data["users"][username].get("bio","")

    return render_template("profile.html",
        user=username,
        videos=videos,
        followers=followers,
        following=following,
        is_following=is_following,
        bio=bio
    )

@app.route("/edit_profile", methods=["GET","POST"])
def edit_profile():
    user = session["user"]
    data = load_data()

    ensure_user(data, user)

    if request.method == "POST":
        bio = request.form["bio"]
        data["users"][user]["bio"] = bio
        save_data(data)
        return redirect(f"/profile/{user}")

    return render_template("edit_profile.html", bio=data["users"][user].get("bio",""))

@app.route("/saved")
def saved():
    user = session["user"]
    data = load_data()

    vids=[]
    for key in data:
        if "/" in key and user in data[key]["saved"]:
            u,v = key.split("/")
            vids.append((u,v))

    return render_template("saved.html", videos=vids)

@app.route("/search", methods=["GET","POST"])
def search():
    users = os.listdir(BASE_UPLOAD)
    result=[]

    if request.method=="POST":
        name=request.form["name"].lower()
        result=[u for u in users if name in u.lower()]

    return render_template("search.html", users=result)

@app.route("/myprofile")
def myprofile():
    return redirect(f"/profile/{session['user']}")

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

app run(host="0.0.0.0",port=10000)
