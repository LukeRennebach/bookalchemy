"""ORM models for BookAlchemy: Author and Book."""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates

db = SQLAlchemy()


class Author(db.Model):
    """Represents an author, including their name and optional birth and death dates.
    This model stores information about an author and is linked to the Book model
    in a one-to-many relationship."""
    __tablename__ = "author"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    birth_date = db.Column(db.String(20))
    date_of_death = db.Column(db.String(20))

    def __repr__(self):
        return f"<Author name={self.name}>"

    def __str__(self):
        birth = self.birth_date or "unknown"
        death = self.date_of_death or "—"
        return f"{self.name} (Born: {birth}, Died: {death})"


class Book(db.Model):
    """Represents a book with title, ISBN, and optional publication year.
    Each book is associated with one author through a foreign key relationship,
    enabling bidirectional access between authors and their books."""
    __tablename__ = "book"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(150), nullable=False)
    publication_year = db.Column(db.Integer)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    author = db.relationship('Author', backref='books', lazy=True)

    __table_args__ = (
        db.CheckConstraint("publication_year IS NULL OR publication_year >= 0", name="ck_book_pubyear_nonneg"),
    )

    def __repr__(self):
        return f"<Book title={self.title} author={self.author.name if self.author else 'Unknown'}>"

    def __str__(self):
        author_name = self.author.name if self.author else "Unknown Author"
        year = self.publication_year if self.publication_year is not None else "n/a"
        return f"'{self.title}' by {author_name} (Published: {year})"

    @validates("publication_year")
    def validate_publication_year(self, key, value):
        """Ensure year is a non-negative integer if provided."""
        if value is None:
            return None
        try:
            ivalue = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("publication_year must be an integer or None") from exc
        if ivalue < 0:
            raise ValueError("publication_year cannot be negative")
        if ivalue > 3000:
            raise ValueError("publication_year seems unrealistic (>3000)")
        return ivalue

    @validates("isbn")
    def validate_isbn(self, key, value):
        """Ensure ISBN is a non-empty string."""
        if not value or not str(value).strip():
            raise ValueError("isbn is required")
        return str(value).strip()
