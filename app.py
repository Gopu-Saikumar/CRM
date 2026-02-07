from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('CRM_SECRET_KEY', 'crm-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(150))
    status = db.Column(db.String(50))


class FollowUp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    note = db.Column(db.Text)
    followup_date = db.Column(db.String(50))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        raw_password = request.form['password']
        if not username or not raw_password:
            flash('Please fill in all fields', 'warning')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        password = generate_password_hash(raw_password)
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('dashboard.html', customers=customers)


@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            email=request.form['email'],
            phone=request.form['phone'],
            company=request.form['company'],
            status=request.form['status']
        )
        db.session.add(customer)
        db.session.commit()
        flash('Customer added', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_customer.html')


@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.email = request.form['email']
        customer.phone = request.form['phone']
        customer.company = request.form['company']
        customer.status = request.form['status']
        db.session.commit()
        flash('Customer updated', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_customer.html', customer=customer)


@app.route('/delete_customer/<int:id>', methods=['POST'])
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    # delete any followups for this customer
    FollowUp.query.filter_by(customer_id=customer.id).delete()
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted', 'info')
    return redirect(url_for('dashboard'))


@app.route('/followups/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def followups(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == 'POST':
        note = request.form['note']
        date = request.form['date']
        follow = FollowUp(customer_id=customer_id, note=note, followup_date=date)
        db.session.add(follow)
        db.session.commit()
        flash('Follow-up saved', 'success')
        return redirect(url_for('followups', customer_id=customer_id))

    followups = FollowUp.query.filter_by(customer_id=customer_id).order_by(FollowUp.id.desc()).all()
    return render_template('followups.html', followups=followups, customer=customer)


@app.route('/delete_followup/<int:id>', methods=['POST'])
@login_required
def delete_followup(id):
    f = FollowUp.query.get_or_404(id)
    cid = f.customer_id
    db.session.delete(f)
    db.session.commit()
    flash('Follow-up deleted', 'info')
    return redirect(url_for('followups', customer_id=cid))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('home'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
