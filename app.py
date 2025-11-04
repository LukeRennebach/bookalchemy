"""Flask entrypoint for the BookAlchemy app: routes, config and CRUD handlers."""

import os
from datetime import date, datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import func
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
        birth_date_str = request.form.get("birth_date", "").strip()
        date_of_death_str = request.form.get("date_of_death", "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")

        # Parse dates if provided (expecting YYYY-MM-DD)
        birth_dt = None
        death_dt = None
        try:
            if birth_date_str:
                birth_dt = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Birth date must be YYYY-MM-DD.")
        try:
            if date_of_death_str:
                death_dt = datetime.strptime(date_of_death_str, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Date of death must be YYYY-MM-DD.")

        today = date.today()
        if birth_dt and birth_dt > today:
            errors.append("Birth date cannot be in the future.")
        if death_dt and death_dt > today:
            errors.append("Date of death cannot be in the future.")
        if birth_dt and death_dt and death_dt < birth_dt:
            errors.append("Date of death must be after birth date.")

        # Duplicate author check by normalized name (case-insensitive)
        if name and not errors:
            existing = Author.query.filter(func.lower(Author.name) == name.lower()).first()
            if existing:
                errors.append("Author already exists.")

        if errors:
            message = "; ".join(errors)
        else:
            try:
                author = Author(
                    name=name,
                    birth_date=birth_dt if birth_dt else None,
                    date_of_death=death_dt if death_dt else None,
                )
                db.session.add(author)
                db.session.commit()
                message = f'Author "{author.name}" added.'
            except Exception as exc:
                db.session.rollback()
                message = f"Could not add author: {exc}"

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

        errors = []
        if not (title and isbn and author_id):
            errors.append("Title, ISBN, and author are required.")

        # Validate author exists
        author_obj = None
        if author_id:
            try:
                author_obj = Author.query.get(int(author_id))
                if not author_obj:
                    errors.append("Selected author does not exist.")
            except Exception:
                errors.append("Invalid author selection.")

        # Basic ISBN validation (allow hyphens/spaces, require 10 or 13 digits)
        def is_valid_isbn(raw: str) -> bool:
            digits = "".join(ch for ch in raw if ch.isdigit())
            return len(digits) in (10, 13)

        if isbn and not is_valid_isbn(isbn):
            errors.append("ISBN must contain 10 or 13 digits (hyphens/spaces allowed).")

        # Publication year validation
        year_value = None
        if publication_year:
            if publication_year.isdigit():
                year_value = int(publication_year)
                current_year = date.today().year
                if year_value < 1450 or year_value > current_year:  # reasonable bounds
                    errors.append("Publication year must be between 1450 and the current year.")
            else:
                errors.append("Publication year must be a number.")

        # Prevent duplicate title for the same author (case-insensitive)
        if title and author_obj:
            duplicate = (
                Book.query
                .filter(Book.author_id == author_obj.id)
                .filter(func.lower(Book.title) == title.lower())
                .first()
            )
            if duplicate:
                errors.append("This author already has a book with that title.")

        if errors:
            message = "; ".join(errors)
        else:
            try:
                book = Book(
                    title=title,
                    isbn=isbn,
                    publication_year=year_value,
                    author_id=author_obj.id if author_obj else int(author_id),
                )
                db.session.add(book)
                db.session.commit()
                message = f'Book "{book.title}" added.'
            except Exception as exc:
                db.session.rollback()
                message = f"Could not add book: {exc}"

    return render_template("add_book.html", authors=authors, message=message)


@app.route("/", methods=["GET"])
def home():
    """List books with optional title search."""
    search_query = request.args.get("q", "").strip()
    query = Book.query
    if search_query:
        query = query.filter(Book.title.ilike(f"%{search_query}%"))
    books = query.all()
    no_results = bool(search_query) and not books
    return render_template("home.html", books=books, q=search_query, no_results=no_results)


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