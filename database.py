from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    
    # Relationship to track borrowed books
    borrowed_books = db.relationship('Transaction', backref='student', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rfid_uid = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    shelf_number = db.Column(db.String(50), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    
    # Track borrowing history
    transactions = db.relationship('Transaction', backref='book', lazy='True')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    is_returned = db.Column(db.Boolean, default=False)

class Settings(db.Model):
    """Store system settings"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)