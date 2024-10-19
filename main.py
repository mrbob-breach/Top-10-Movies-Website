from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, desc
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField
from wtforms.validators import DataRequired
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
Bootstrap5(app)


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movie-collection.db"
db.init_app(app)

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
TMDB_URL = "https://api.themoviedb.org/3/search/movie?include_adult=false&language=en-US&page=1"
headers = {
    "accept": "application/json",
    "Authorization": ACCESS_TOKEN
}


class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    with app.app_context():
        all_movies = Movie.query.order_by(Movie.rating).all()
        position = len(all_movies)
        for movie in all_movies:
            movie.ranking = position
            position -= 1
    return render_template("index.html", all_movies=all_movies)


class EditForm(FlaskForm):
    rating = DecimalField(label='Your Rating Out of 10 (e.g. 7.5)', places=2, validators=[DataRequired()])
    review = StringField(label='Your Review', validators=[DataRequired()])
    submit = SubmitField(label="Done")


@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = EditForm()
    movie_in_database = db.get_or_404(Movie, request.args.get("id"))
    if form.validate_on_submit():
        movie_in_database.rating = request.form["rating"]
        movie_in_database.review = request.form["review"]
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("edit.html", form=form, movie=movie_in_database)


@app.route("/delete", methods=["GET"])
def delete():
    movie_in_database = db.get_or_404(Movie, request.args.get("id"))
    db.session.delete(movie_in_database)
    db.session.commit()
    return redirect(url_for('home'))


class AddForm(FlaskForm):
    title = StringField(label='Movie Title', validators=[DataRequired()])
    submit = SubmitField(label="Add Movie")


params = {
    "query": "Lord of the rings"
}


@app.route("/add", methods=["GET", "POST"])
def add():
    add_form = AddForm()
    if add_form.validate_on_submit():
        movie_addition = request.form["title"]
        params = {
            "query": {movie_addition}
        }
        response = requests.get(TMDB_URL, headers=headers, params=params)
        movie_results = response.json()["results"]
        return render_template("select.html", movie_results=movie_results)
    return render_template("add.html", add_form=add_form)


@app.route("/select")
def select():
    movie_id = request.args.get("id")
    Movie_Details_URL = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"
    movie_addition = requests.get(Movie_Details_URL, headers=headers).json()
    new_movie = Movie(
        title=movie_addition['title'],
        year=movie_addition['release_date'][:4],
        description=movie_addition['overview'],
        img_url=f'https://image.tmdb.org/t/p/original{movie_addition['poster_path']}'
    )
    db.session.add(new_movie)
    db.session.commit()
    return redirect(url_for("edit", id=new_movie.id))


if __name__ == '__main__':
    app.run(debug=True)
