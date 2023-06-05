import os
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for
from flask import current_app
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from random import randint

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DEBUG"] = True
app.config["FLASK_DEBUG"] = True
app.config["SECRET_KEY"] = os.urandom(24)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
admin = Admin(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))

    def get_id(self):
        return self.id

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def __repr__(self):
        return f"User(id='{self.id}', username='{self.username}', password='{self.password}',, secret_code='{self.secret_code}', sesionValidTo='{self.sesionValidTo}', codeToConfirmEmail='{self.codeToConfirmEmail}', isEmailConfirmed='{self.isEmailConfirmed}', is_admin='{self.is_admin}')"

    def __repr__(self) -> str:
        return f"{self.id} - {self.email}"


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    date = db.Column(db.String(80))
    start_time = db.Column(db.String(80))
    end_time = db.Column(db.String(80))
    seats = db.Column(db.String(150))

    def __repr__(self):
        return f"Schedule({self.id}, {self.title}, {self.date}, {self.start_time}, {self.end_time}, {eval(self.seats)})"


class Tickets(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    date = db.Column(db.String(80))
    start_time = db.Column(db.String(80))
    end_time = db.Column(db.String(80))
    seats = db.Column(db.String(150))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('tickets', lazy=True))

    def __repr__(self):
        return f"Tickets({self.id}, {self.title}, {self.date}, {self.start_time}, {self.end_time}, {eval(self.seats)}, {self.user_id})"


from sqlalchemy import inspect


class TicketsView(ModelView):
    with app.app_context():
        column_searchable_list = ['title', 'date', 'start_time', 'end_time', 'seats', 'user_id']
        column_filters = ['title', 'date', 'start_time', 'end_time', 'seats', 'user_id']
        column_editable_list = ['title', 'date', 'start_time', 'end_time', 'seats', 'user_id']
        column_sortable_list = ['title', 'date', 'start_time', 'end_time', 'seats', 'user_id']
        column_default_sort = ('title', True)
        column_exclude_list = ['user_id']
        column_display_pk = True
        # Check if the 'User' table exists
        if inspect(db.engine).has_table("User"):
            column_choices = {
                'user_id': [(user.id, user.email) for user in User.query.all()]
            }


@app.route('/admin')
@login_required
def adm():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))
    else:
        return redirect(url_for('login'))


admin.add_view(ModelView(Schedule, db.session))
admin.add_view(ModelView(User, db.session))
admin.add_view(TicketsView(Tickets, db.session))


@login_manager.user_loader
def load_user(user_id):
    # Implement the logic to load the User from your database or other source
    return User.query.get(user_id)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cr_user = User.query.filter_by(email=email).first()
        if cr_user:
            if cr_user.password == password:
                login_user(cr_user)
                response = redirect(url_for('main'))
                return response
            else:
                return "Wrong password"
        else:
            return "User not found"
    else:
        return render_template('login.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur_us = User.query.filter_by(email=email).first()
        if cur_us:
            return "User already exists"
        else:
            new_user = User(email=email, password=password)
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)  # Log in the newly registered User

            # Add cookies
            response = redirect(url_for('main'))
            response.set_cookie('email', new_user.email)
            return response

    else:
        return render_template('register.html')


@app.route("/static/<name>")
def styles(name):
    f = open(f"static/{name}", "r")
    text = f.read()
    f.close()
    return text, 200, {'Content-Type': 'text/css'}


@app.route("/profile")
@login_required
def profile():
    tickets = Tickets.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', tickets=tickets)


@app.route("/buy_ticket/<id>", methods=['POST'])
@login_required
def buy_ticket(id):
    schedule = Schedule.query.filter_by(id=id).first()
    if schedule is None:
        return redirect(url_for('main'))

    seats = eval(schedule.seats)
    selected_seats = request.form.getlist('seat')
    selected_seats = [int(seat) for seat in selected_seats]

    # Check if selected seats are valid
    for seat in selected_seats:
        if seat not in seats:
            return redirect(url_for('main'))

    # Remove selected seats from available seats
    for seat in selected_seats:
        seats.remove(seat)
        ticket = Tickets(title=schedule.title, date=schedule.date, start_time=schedule.start_time,
                         end_time=schedule.end_time, seats=str(seat), user=current_user)
        db.session.add(ticket)

    schedule.seats = str(seats)
    db.session.commit()
    return redirect(url_for('profile'))


@app.route("/")
@login_required
def main():
    schedule = Schedule.query.all()
    movies = []
    for i in schedule:
        movies.append({
            "id": i.id,
            "title": i.title,
            "date": i.date,
            "start_time": i.start_time,
            "end_time": i.end_time,
            "seats": eval(i.seats)
        })
    return render_template("main.html", schedule=movies)


def populate_schedule():
    film_titles = [
        "Iron Man",
        "Captain America: The First Avenger",
        "Thor",
        "The Avengers",
        "Guardians of the Galaxy"
    ]

    # Generate 5 sessions for the Marvel films
    for i in range(5):
        title = film_titles[i]
        date = datetime.now().strftime("%Y-%m-%d")
        start_time = f"{randint(10, 18)}:30"  # Random start time between 10 AM and 6 PM
        end_time = f"{int(start_time[:2]) + 2}:30"  # End time is 2 hours after the start time
        seats = "[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]"

        session = Schedule(title=title, date=date, start_time=start_time, end_time=end_time, seats=seats)

        # Add the session to the database
        db.session.add(session)

    # Commit the changes to the database
    db.session.commit()


@app.route("/fill")
def fill():
    populate_schedule()
    return redirect(url_for('main'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
