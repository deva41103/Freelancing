from flask import Flask, request, render_template, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for session management

# MySQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:deva%4012@localhost/db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define database models
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(20))
    email = db.Column(db.String(120))
    company_name = db.Column(db.String(120))
    projects = db.relationship('Project', backref='client', lazy=True)

class Freelancer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(20))
    email = db.Column(db.String(120))
    skills = db.Column(db.Text)
    experience = db.Column(db.String(20))
    bids = db.relationship('Bid', backref='freelancer', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proj_name = db.Column(db.String(120), nullable=False)
    proj_type = db.Column(db.String(120), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    approved_freelancer_id = db.Column(db.Integer, db.ForeignKey('freelancer.id'))
    at_cost = db.Column(db.Float)
    bids = db.relationship('Bid', backref='project', lazy=True)

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bid_amount = db.Column(db.Float, nullable=False)
    proposal = db.Column(db.Text, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('freelancer.id'), nullable=False)

# Create database tables
with app.app_context():
    db.create_all()

# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Client Signup
@app.route("/client/signup", methods=["GET","POST"])
def client_signup():
    if request.method=="POST":
        username=request.form["username"]
        if Client.query.filter_by(username=username).first():
            flash("Username already registered!", "danger")
            return redirect(url_for("client_signup"))
        new_client = Client(
            username=username, 
            password=request.form["password"], 
            mobile=request.form["mobile"], 
            email=request.form["email"], 
            company_name=request.form["company_name"]
        )
        db.session.add(new_client)
        db.session.commit()
        flash("Signup successful! Please log in.", "success")
        return redirect(url_for("client_login"))
    return render_template("signup.html", user_type="client")


# Client Login
@app.route("/client/login", methods=["GET", "POST"])
def client_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        client = Client.query.filter_by(username=username).first()
        if client and client.password == password:
            session["username"] = client.username
            session["user_type"] = "client"
            flash("Login successful!", "success")
            return redirect(url_for("client_dashboard"))
        else:
            flash("Invalid Credentials!", "danger")
            return redirect(url_for("client_login"))
    return render_template("login.html", user_type="client") 


# Client Dashboard
@app.route("/client/dashboard")
def client_dashboard():
    if "username" not in session or session.get("user_type") != "client":
        return redirect(url_for("client_login"))
    return render_template("client_dashboard.html", username=session["username"])


# Freelancer Signup
@app.route("/freelancer/signup", methods=["GET","POST"])
def freelancer_signup():
    if request.method=="POST":
        username=request.form["username"]
        if Freelancer.query.filter_by(username=username).first():
            flash("Username already registered!", "danger")
            return redirect(url_for("freelancer_signup"))
        new_freelancer = Freelancer(
            username=username, 
            password=request.form["password"], 
            mobile=request.form["mobile"], 
            email=request.form["email"], 
            skills=request.form["skills"], 
            experience=request.form["experience"]
        )
        db.session.add(new_freelancer)
        db.session.commit()
        flash("Signup successful! Please log in.", "success")
        return redirect(url_for("freelancer_login"))
    return render_template("signup.html", user_type="freelancer")


# Freelancer Login
@app.route("/freelancer/login", methods=["GET", "POST"])
def freelancer_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        freelancer = Freelancer.query.filter_by(username=username).first()
        if freelancer and freelancer.password == password:
            session["username"] = freelancer.username
            session["user_type"] = "freelancer"
            flash("Login successful!", "success")
            return redirect(url_for("freelancer_dashboard"))
        else:
            flash("Invalid Credentials!", "danger")
            return redirect(url_for("freelancer_login"))
    return render_template("login.html", user_type="freelancer") 


# Freelancer Dashboard
@app.route("/freelancer/dashboard")
def freelancer_dashboard():
    if "username" not in session or session.get("user_type") != "freelancer":
        return redirect(url_for("freelancer_login"))
    # Fetch freelancer's ID from the database
    freelancer = Freelancer.query.filter_by(username=session["username"]).first()
    if not freelancer:
        flash("Freelancer not found!", "danger")
        return redirect(url_for("freelancer_login"))
    # Fetch projects where the freelancer is approved, along with client details
    approved_projects = db.session.query(
        Project.proj_name, 
        Project.at_cost, 
        Client.username.label("client_username"), 
        Client.company_name.label("company_name")
    ).join(Client, Project.client_id == Client.id).filter(
        Project.approved_freelancer_id == freelancer.id
    ).all()
    return render_template("freelancer_dashboard.html", 
                           username=freelancer.username, 
                           user_type="freelancer", 
                           approved_projects=approved_projects)


# Post Project (client)
@app.route("/client/postproject", methods=["GET", "POST"])
def post_project():
    if "username" not in session or session.get("user_type") != "client":
        return redirect(url_for("client_login"))
    if request.method == "POST":
        client = Client.query.filter_by(username=session["username"]).first()
        if not client:
            flash("Client not found!", "danger")
            return redirect(url_for("post_project"))
        # Debugging prints
        print("Received form data:", request.form)
        proj_name = request.form.get("proj_name")
        proj_type = request.form.get("proj_type")
        if not proj_name or not proj_type:
            flash("Project name and type are required!", "danger")
            return redirect(url_for("post_project"))
        project = Project(proj_name=proj_name, proj_type=proj_type, client_id=client.id)
        db.session.add(project)
        db.session.commit()
        flash("Project posted successfully!", "success")
        return redirect(url_for("view_project"))
    return render_template("post_project.html")


# View Project (client)
@app.route("/client/viewpostproject", methods=["GET","POST"])
def view_project():
    if "username" not in session or session.get("user_type") != "client":
        return redirect(url_for("client_login"))
    client = Client.query.filter_by(username=session["username"]).first()
    if not client:
        flash("Client not found!", "danger")
        return redirect(url_for("client_login"))
    projects = Project.query.filter_by(client_id=client.id).all()
    return render_template("view_project.html", projects=projects)


# Terminate Project (client)
@app.route("/client/projects/<proj_name>/terminate", methods=["POST"])
def terminate_project(proj_name):
    if "user_type" in session and session["user_type"] == "client":
        username = session["username"]
        client = Client.query.filter_by(username=username).first()
        if client:
            project = Project.query.filter_by(client_id=client.id, proj_name=proj_name).first()
            if project:
                # Delete all related bids before deleting the project
                Bid.query.filter_by(project_id=project.id).delete()
                db.session.delete(project)
                db.session.commit()
                flash(f"Project '{proj_name}' has been terminated!", "success")
            else:
                flash("Project not found!", "danger")
    return redirect(url_for("view_project"))


# Bid On Project (freelancer)
@app.route("/freelancer/bidonproject", methods=["GET", "POST"])
def bid_on_project():
    if "username" not in session or session.get("user_type") != "freelancer":
        return redirect(url_for("freelancer_login"))    
    freelancer = Freelancer.query.filter_by(username=session["username"]).first()
    if request.method == "POST":
        print("Form Data Received:", request.form)  # Debugging line
        if "proj_id" not in request.form:
            flash("Project ID is missing!", "danger")
            return redirect(url_for("bid_on_project"))
        proj_id = request.form["proj_id"]
        bid_amount = request.form["bid_amount"]
        proposal = request.form["proposal"]
        project = Project.query.get(proj_id)
        if project:
            bid = Bid(freelancer_id=freelancer.id, project_id=project.id, bid_amount=bid_amount, proposal=proposal)
            db.session.add(bid)
            db.session.commit()
            flash("Bid placed successfully!", "success")
            return redirect(url_for("bid_on_project"))
    projects = Project.query.filter_by(approved_freelancer_id=None).all()
    return render_template("bid_on_project.html", projects=projects,client_username=Project.client_id)


# View Project Bids (Client)
@app.route("/client/projects/<proj_name>/bids", methods=["GET"])
def view_project_bids(proj_name):
    if "username" not in session or session.get("user_type") != "client":
        return redirect(url_for("client_login"))
    client = Client.query.filter_by(username=session["username"]).first()
    if not client:
        flash("Client not found!", "danger")
        return redirect(url_for("client_login"))
    project = Project.query.filter_by(proj_name=proj_name, client_id=client.id).first()
    if not project:
        flash("Project not found or does not belong to this client!", "danger")
        return redirect(url_for("view_project"))
    if project.approved_freelancer_id:
        bid = Bid.query.filter_by(project_id=project.id, freelancer_id=project.approved_freelancer_id).first()
        freelancer = db.session.get(Freelancer, project.approved_freelancer_id)
        bids_with_details = [{
            "freelancer": freelancer.username,
            "bid_amount": bid.bid_amount,
            "proposal": bid.proposal,
            "skills": freelancer.skills,
            "experience": freelancer.experience,
            "email": freelancer.email,
            "mobile": freelancer.mobile
        }]
    else:
        bids = Bid.query.filter_by(project_id=project.id).all()
        bids_with_details = []
        for bid in bids:
            freelancer = db.session.get(Freelancer, bid.freelancer_id) 
            if freelancer:  # Ensure the freelancer exists
                bids_with_details.append({
                    "freelancer": freelancer.username,
                    "bid_amount": bid.bid_amount,
                    "proposal": bid.proposal,
                    "skills": freelancer.skills,
                    "experience": freelancer.experience,
                    "email": freelancer.email,
                    "mobile": freelancer.mobile
                })
    return render_template("view_project_bids.html", project=project, bids=bids_with_details)


# Approve Freelancer (Client)
@app.route("/client/projects/<proj_name>/approve/<freelancer>", methods=["POST"])
def approve_freelancer(proj_name, freelancer):
    if session.get("user_type") != "client":
        return jsonify({"error": "Unauthorized"}), 403  # Return error if not a client
    client = Client.query.filter_by(username=session["username"]).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
    project = Project.query.filter_by(client_id=client.id, proj_name=proj_name).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    freelancer_obj = Freelancer.query.filter_by(username=freelancer).first()
    if not freelancer_obj:
        return jsonify({"error": "Freelancer not found"}), 404
    bid = Bid.query.filter_by(project_id=project.id, freelancer_id=freelancer_obj.id).first()
    if not bid:
        return jsonify({"error": "Bid not found for this freelancer"}), 404
    # Approve the freelancer
    project.approved_freelancer_id = freelancer_obj.id  
    project.at_cost = bid.bid_amount  
    db.session.commit()
    return jsonify({"message": f"Freelancer {freelancer} approved!", "approved_freelancer_id": freelancer_obj.id})


# Logout
@app.route("/logout")
def logout():
    session.clear()  # Remove all session data
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)