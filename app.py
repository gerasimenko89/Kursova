import os
from datetime import datetime
from random import randint

from flask import Flask, request, render_template, redirect, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///user.db"
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


admin.add_view(ModelView(Schedule, db.session))
admin.add_view(ModelView(users, db.session))


@app.route('/process-user', methods=['POST'])
def process_form():
    email = request.form.get('email')
    password = request.form.get('password')
    type = request.form.get('type')
    if not email or not password or not type:
        return f"Email, Password and Type are required!"
    if type == 'register':
        user = users.query.filter_by(email=email).first()
        if user is not None:
            return render_template('register.html', message="User already exists!")
        user = users(email=email, password=password, token=generate_token())
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('main'))
    elif type == 'login':
        user = users.query.filter_by(email=email).first()
        if user is None:
            return render_template('login.html', message="User does not exist!")
        if user.password == password:
            user.token = generate_token()
            db.session.commit()
            # redirect to dashboard
            return redirect(url_for('main'))
        else:
            render_template('login.html', message="Password is incorrect!")


@app.route('/login')
def form():
    return render_template('login.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route("/styles/<name>")
def styles(name):
    f = open(f"static/{name}.css", "r")
    text = f.read()
    f.close()
    return text, 200, {'Content-Type': 'text/css'}




@app.route("/")
def main():
    schedule = Schedule.query.all()
    movies = []
    for i in schedule:
        movies.append({
            "title": i.title,
            "date": i.date,
            "start_time": i.start_time,
            "end_time": i.end_time,
            "seats": eval(i.seats)
        })
    for i in movies:
        print(type(i["seats"]))
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
