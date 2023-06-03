import os
from datetime import datetime
from random import randint

from flask import Flask, request, render_template, redirect, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DEBUG"] = True
app.config["FLASK_DEBUG"] = True
app.config["SECRET_KEY"] = os.urandom(24)
db = SQLAlchemy(app)
admin = Admin(app)


# function to generate token
def generate_token():
    import uuid
    return uuid.uuid4().hex


class users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))
    token = db.Column(db.String(80))

    def __repr__(self) -> str:
        return f"{self.id} - {self.email} - {self.token}"


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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('users', backref=db.backref('tickets', lazy=True))

    def __repr__(self):
        return f"Tickets({self.id}, {self.title}, {self.date}, {self.start_time}, {self.end_time}, {eval(self.seats)}, {self.user_id})"


class TicketsView(ModelView):
    with app.app_context():
        column_searchable_list = ['title', 'date', 'start_time', 'end_time', 'seats', 'user_id']
        column_filters = ['title', 'date', 'start_time', 'end_time', 'seats', 'user_id']
        column_editable_list = ['title', 'date', 'start_time', 'end_time', 'seats', 'user_id']
        column_sortable_list = ['title', 'date', 'start_time', 'end_time', 'seats', 'user_id']
        column_default_sort = ('title', True)
        column_exclude_list = ['user_id']
        column_display_pk = True
        users = users.query.all()
        column_choices = {
            'user_id': [(user.id, user.email) for user in users]
        }


admin.add_view(ModelView(Schedule, db.session))
admin.add_view(ModelView(users, db.session))
admin.add_view(TicketsView(Tickets, db.session))


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.query.filter_by(email=email).first()
        if user:
            if user.password == password:
                token = generate_token()
                user.token = token
                db.session.commit()
                # add cookie
                response = redirect(url_for('main'))
                response.set_cookie('token', token)
                response.set_cookie('email', user.email)
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

        user = users.query.filter_by(email=email).first()
        if user:
            return "User already exists"
        else:
            new_user = users(email=email, password=password, token=generate_token())
            db.session.add(new_user)
            db.session.commit()
            # add cookie
            response = redirect(url_for('main'))
            response.set_cookie('token', new_user.token)
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
def profile():
    token = request.cookies.get('token')
    if not token:
        return redirect(url_for('login'))
    user = users.query.filter_by(token=token).first()
    if user is None:
        return redirect(url_for('login'))
    tickets = Tickets.query.filter_by(user_id=user.id).all()
    return render_template('profile.html', tickets=tickets)


@app.route("/buy_ticket/<id>", methods=['POST'])
def buy_ticket(id):
    token = request.cookies.get('token')
    username = request.cookies.get('email')
    if not token or not username:
        return redirect(url_for('login'))
    user = users.query.filter_by(token=token).first()
    if user is None:
        return redirect(url_for('login'))
    if user.token != token:
        return redirect(url_for('login'))
    schedule = Schedule.query.filter_by(id=id).first()
    if schedule is None:
        return redirect(url_for('main'))
    seats = eval(schedule.seats)
    seeats = request.form.getlist('seat')
    for i in range(len(seeats)):
        seeats[i] = int(seeats[i])
    #return seeats
    for i in seeats:
        if i not in seats:
            return redirect(url_for('main'))
    for i in seeats:
        seats.remove(i)
        ticket = Tickets(title=schedule.title, date=schedule.date, start_time=schedule.start_time, end_time=schedule.end_time,
                seats=str(i), user=user)
        db.session.add(ticket)
    schedule.seats = str(seats)
    db.session.commit()
    return redirect(url_for('profile'))


@app.route("/")
def main():
    schedule = Schedule.query.all()
    username = request.cookies.get('email')
    token = request.cookies.get('token')
    if not token or not username:
        return redirect(url_for('login'))
    user = users.query.filter_by(token=token).first()
    if user is None:
        return redirect(url_for('login'))
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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
