import os
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from random import randint
#init migration
from flask_migrate import Migrate

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
migration = Migrate(app, db)
admin = Admin(app)



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))
    admin = db.Column(db.Boolean, default=False)

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
    if current_user.is_anonymous and current_user.admin:
        return redirect(url_for('admin.index'))
    else:
        return redirect(url_for('login'))

class viewModel(ModelView):
    def is_accessible(self):
        return not current_user.is_anonymous and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))


admin.add_view(viewModel(Schedule, db.session))
admin.add_view(viewModel(User, db.session))
admin.add_view(viewModel(Tickets, db.session))


@login_manager.user_loader
def load_user(user_id):
    # Implement the logic to load the User from your database or other source
    return User.query.get(user_id)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main'))

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
                flash("Не вірний логін або пароль")
                return redirect(url_for('login'))
        else:
            flash("Не вірний логін або пароль")
            return redirect(url_for('login'))
    else:
        return render_template('login.html')



@app.route('/register', methods=['POST', 'GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur_user = User.query.filter_by(email=email).first()
        if cur_user:
            flash("Користувач вже існує", "error")
            return redirect(url_for('register'))
        else:
            new_user = User(email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            response = redirect(url_for('main'))
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
    admin = User(email="admin@admin.com", password="111", admin=True)
    db.session.add(admin)
    db.session.commit()
    film_titles = [
        "Iron Man",
        "Captain America: The First Avenger",
        "Thor",
        "The Avengers",
        "Guardians of the Galaxy"
    ]
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

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/fill")
def fill():
    populate_schedule()
    return redirect(url_for('main'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
