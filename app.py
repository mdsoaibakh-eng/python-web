import os
from flask import Flask, render_template, redirect, url_for, flash, request, session
from dotenv import load_dotenv
from models import db, Product, Admin, User, Registration
from markupsafe import Markup, escape
from werkzeug.utils import secure_filename
from datetime import datetime

load_dotenv()

# ===========================
# Admin Login Required
# ===========================
def admin_login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in as admin.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# ===========================
# USER Login Required
# ===========================
def user_login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in as a user.", "error")
            return redirect(url_for("user_login"))
        return f(*args, **kwargs)
    return wrapper


# ===========================
# Create App
# ===========================
def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '123456')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Create tables
    with app.app_context():
        db.create_all()

    # ================
    # Template filter
    # ================
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s is None:
            return ""
        return Markup("<br>".join(escape(s).splitlines()))

    # ===========================
    # ADMIN AUTHINCATION
    # ===========================

    @app.route("/admin/register", methods=["GET", "POST"])
    def admin_register():
        if request.method == "POST":
            username = request.form.get("username").strip()
            password = request.form.get("password").strip()

            if not username or not password:
                flash("Username and password required.", "error")
                return render_template("admin_register.html")

            if Admin.query.filter_by(username=username).first():
                flash("Username already taken.", "error")
                return render_template("admin_register.html")

            admin = Admin(username=username)
            admin.set_password(password)

            db.session.add(admin)
            db.session.commit()

            flash("Admin registered successfully.", "success")
            return redirect(url_for("admin_login"))

        return render_template("admin_register.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username").strip()
            password = request.form.get("password").strip()

            admin = Admin.query.filter_by(username=username).first()

            if not admin or not admin.check_password(password):
                flash("Invalid username or password.", "error")
                return render_template("admin_login.html")

            session.clear()
            session["admin_id"] = admin.id

            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))

        return render_template("admin_login.html")

    @app.route("/admin/logout")
    def logout():
        session.pop("admin_id", None)
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    # ###############################################################
    # USER AUTHENTICATION
    # ######################################################################

    @app.route("/user/register", methods=["GET", "POST"])
    def user_register():
        if request.method == "POST":
            username = request.form.get("username").strip()
            email = request.form.get("email").strip()
            password = request.form.get("password").strip()

            if not username or not email or not password:
                flash("All fields are required.", "error")
                return render_template("user_register.html")

            if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
                flash("Username or email already taken.", "error")
                return render_template("user_register.html")

            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            flash("Registered successfully. Please login.", "success")
            return redirect(url_for("user_login"))

        return render_template("user_register.html")

    @app.route("/user/login", methods=["GET", "POST"])
    def user_login():
        if request.method == "POST":
            username = request.form.get("username").strip()
            password = request.form.get("password").strip()

            user = User.query.filter_by(username=username).first()

            if not user or not user.check_password(password):
                flash("Invalid username or password.", "error")
                return render_template("user_login.html")

            session.clear()
            session["user_id"] = user.id

            flash("Logged in successfully.", "success")
            return redirect(url_for("user_dashboard"))

        return render_template("user_login.html")

    @app.route("/user/logout")
    def user_logout():
        session.pop("user_id", None)
        flash("Logged out.", "info")
        return redirect(url_for("index"))


    # #####################################################
    # PRODUCT REGISTRATION
    # ########################################################

    @app.route("/user/register_products/<int:products_id>", methods=["POST"])
    @user_login_required
    def register_products(products_id):
        user = User.query.get(session["user_id"])
        products = Product.query.get_or_404(products_id)

        # Check if already registered
        existing_reg = Registration.query.filter_by(user_id=user.id, products_id=products.id).first()
        if existing_reg:
            flash("You are already registered for this products.", "info")
            return redirect(url_for("detail", products_id=products.id))

        registration = Registration(user_id=user.id, products_id=products.id)
        db.session.add(registration)
        db.session.commit()

        flash("Registered for products successfully.", "success")
        return redirect(url_for("user_dashboard"))


    # ################################################
    # USER DASHBOARD
    # ####################################################

    @app.route("/user/dashboard")
    @user_login_required
    def user_dashboard():
        user = User.query.get(session["user_id"])
        registrations = user.registrations
        return render_template("user_dashboard.html", user=user, registrations=registrations)


    # ##########################################
    # Admin: View & Approve Registrations
    # ################################################

    @app.route("/admin/registrations")
    @admin_login_required
    def admin_view_registrations():
        registrations = Registration.query.order_by(Registration.created_at.desc()).all()
        return render_template("admin_registrations.html", registrations=registrations)

    @app.route("/admin/registrations/approve/<int:reg_id>", methods=["POST"])
    @admin_login_required
    def approve_registration(reg_id):
        reg_record = Registration.query.get_or_404(reg_id)
        reg_record.status = "Approved"
        reg_record.approved_at = datetime.utcnow()
        db.session.commit()

        flash("Registration approved.", "success")
        return redirect(url_for("admin_view_registrations"))


    # ##########################################
    # PUBLIC PRODUCT VIEWS
    # ################################################

    @app.route("/")
    def index():
        # page = request.args.get("page", 1, type=int)
        # per_page = 6
        # products = Product.query.order_by(Product.date.asc()).paginate(page=page, per_page=per_page, error_out=False)
        return render_template("index.html")

    @app.route("/products/<int:products_id>")
    def detail(products_id):
        products = Product.query.get_or_404(products_id)
        is_registered = False
        if session.get("user_id"):
            user_id = session.get("user_id")
            if Registration.query.filter_by(user_id=user_id, products_id=products.id).first():
                is_registered = True
        
        return render_template("detail.html", products=products, is_registered=is_registered)


    # #######################################
    # ADMIN CRUD (PRODUCTS)
    # ############################################

    @app.route("/create", methods=["GET", "POST"])
    @admin_login_required
    def create():
        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            description = (request.form.get("description") or "").strip() or None
            location = (request.form.get("location") or "").strip()
            date_str = request.form.get("date")

            if not title or not location or not date_str:
                flash("Title, Location and Date are required.", "error")
                return render_template("create.html", title=title, description=description, location=location, date=date_str)

            try:
                products_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid date format.", "error")
                return render_template("create.html", title=title, description=description, location=location, date=date_str)

            products = Product(title=title, description=description, location=location, date=products_date)
            db.session.add(products)
            db.session.commit()

            flash("Product created successfully.", "success")
            return redirect(url_for("index"))

        return render_template("create.html", title="", description="", location="", date="")

    @app.route("/edit/<int:products_id>", methods=["GET", "POST"])
    @admin_login_required
    def edit(products_id):
        products = Product.query.get_or_404(products_id)

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            description = (request.form.get("description") or "").strip() or None
            location = (request.form.get("location") or "").strip()
            date_str = request.form.get("date")

            if not title or not location or not date_str:
                flash("Title, Location and Date are required.", "error")
                return render_template("edit.html", products=products)

            try:
                products_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid date format.", "error")
                return render_template("edit.html", products=products)

            products.title = title
            products.description = description
            products.location = location
            products.date = products_date

            db.session.commit()

            flash("Product updated.", "success")
            return redirect(url_for("detail", products_id=products.id))

        return render_template("edit.html", products=products)

    @app.route("/delete/<int:products_id>", methods=["POST"])
    @admin_login_required
    def delete(products_id):
        products = Product.query.get_or_404(products_id)
        db.session.delete(products)
        db.session.commit()
        flash("Product deleted.", "info")
        return redirect(url_for("index"))
    
       # ===========================
    # ESTIMATE PAGE
    # ===========================
    @app.route("/estimate")
    def estimate():
        return render_template("estimate.html")
    
    # ===========================
    # About Us
    # ===========================
    @app.route("/about")
    def about():
        return render_template("about.html")
 

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app

if __name__ == "__main__":
    create_app().run(debug=True)
