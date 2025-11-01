"""Flask entrypoint for the BookAlchemy app: routes, config and CRUD handlers."""

import os

from flask import Flask, render_template, request, redirect, url_for, flash
from data_models import db, Author, Book

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'  # needed for flash() messages
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "data", "library.sqlite")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
db.init_app(app)


@app.route("/add_author", methods=["GET", "POST"])
def add_author():
    """Render and process the Add Author form."""
    message = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        birth_date = request.form.get("birth_date", "").strip()
        date_of_death = request.form.get("date_of_death", "").strip()

        if not name:
            message = "Name is required."
        else:
            author = Author(
                name=name,
                birth_date=birth_date or None,
                date_of_death=date_of_death or None
            )
            db.session.add(author)
            db.session.commit()
            message = f'Author "{author.name}" added.'

    return render_template("add_author.html", message=message)

@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    """Render and process the Add Book form."""
    message = None
    authors = Author.query.order_by(Author.name.asc()).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        isbn = request.form.get("isbn", "").strip()
        publication_year = request.form.get("publication_year", "").strip()
        author_id = request.form.get("author_id", "").strip()

        if not (title and isbn and author_id):
            message = "Title, ISBN, and author are required."
        else:
            year_value = int(publication_year) if publication_year.isdigit() else None
            book = Book(
                title=title,
                isbn=isbn,
                publication_year=year_value,
                author_id=int(author_id)
            )
            db.session.add(book)
            db.session.commit()
            message = f'Book "{book.title}" added.'

    return render_template("add_book.html", authors=authors, message=message)


@app.route("/", methods=["GET"])
def home():
    """List books with optional title search."""
    q = request.args.get("q", "").strip()
    query = Book.query
    if q:
        query = query.filter(Book.title.ilike(f"%{q}%"))  # LIKE '%q%'
    books = query.all()
    no_results = bool(q) and not books
    return render_template("home.html", books=books, q=q, no_results=no_results)


# Route to delete a book and remove author if no books remain
@app.route("/book/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id):
    """Delete a book; remove its author if no books remain."""
    book = Book.query.get_or_404(book_id)
    author = book.author
    db.session.delete(book)
    db.session.commit()

    # If the author now has no books, remove the author as well
    if author and not author.books:
        db.session.delete(author)
        db.session.commit()
        flash(
            f'Deleted "{book.title}" and removed author "{author.name}" '
            f'(no remaining books).'
        )
    else:
        flash(f'Deleted "{book.title}".')


    return redirect(url_for("home"))


# --- Error handlers ---
@app.errorhandler(404)
def not_found(error):
    """Render custom 404 page."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    """Render custom 500 page."""
    return render_template("500.html"), 500


# Standard entry point to run the app and ensure tables exist
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # make sure tables exist
    app.run(debug=True)