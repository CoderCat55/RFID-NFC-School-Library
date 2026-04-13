from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from database import db, Student, Book, Transaction
from werkzeug.utils import secure_filename
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize database
db.init_app(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """Home page - choose admin or student mode"""
    return render_template('index.html')

# ============= ADMIN ROUTES =============

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard"""
    # Get current borrowings
    current_borrowings = Transaction.query.filter_by(is_returned=False).all()
    
    # Get statistics
    total_books = Book.query.count()
    available_books = Book.query.filter_by(is_available=True).count()
    total_students = Student.query.count()
    borrowed_books = Transaction.query.filter_by(is_returned=False).count()
    
    return render_template('admin.html',
                         borrowings=current_borrowings,
                         total_books=total_books,
                         available_books=available_books,
                         total_students=total_students,
                         borrowed_books=borrowed_books)

@app.route('/admin/upload-students', methods=['POST'])
def upload_students():
    """Upload student list from Excel file"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if file and file.filename.endswith(('.xlsx', '.xls')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Read Excel file
            df = pd.read_excel(filepath)
            
            # Expected columns: 'student_number', 'name'
            for _, row in df.iterrows():
                student = Student.query.filter_by(student_number=str(row['student_number'])).first()
                if not student:
                    student = Student(
                        student_number=str(row['student_number']),
                        name=row['name']
                    )
                    db.session.add(student)
            
            db.session.commit()
            flash(f'Successfully uploaded {len(df)} students', 'success')
        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'error')
        finally:
            os.remove(filepath)  # Clean up uploaded file
            
    else:
        flash('Please upload an Excel file (.xlsx or .xls)', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export-database')
def export_database():
    """Export database as SQLite file"""
    db_path = os.path.join(os.getcwd(), 'library.db')
    return send_file(db_path, as_attachment=True, download_name='library_backup.db')

@app.route('/admin/import-database', methods=['POST'])
def import_database():
    """Import database file"""
    if 'database' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['database']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if file and file.filename.endswith('.db'):
        try:
            # Close all connections
            db.session.remove()
            
            # Save uploaded database
            filepath = os.path.join(os.getcwd(), 'library.db')
            file.save(filepath)
            
            # Reinitialize connection
            with app.app_context():
                db.create_all()
            
            flash('Database imported successfully', 'success')
        except Exception as e:
            flash(f'Error importing database: {str(e)}', 'error')
    else:
        flash('Please upload a valid .db file', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/return-book/<int:transaction_id>')
def admin_return_book(transaction_id):
    """Mark a book as returned"""
    transaction = Transaction.query.get_or_404(transaction_id)
    transaction.is_returned = True
    transaction.return_date = datetime.utcnow()
    transaction.book.is_available = True
    db.session.commit()
    
    flash(f'Book "{transaction.book.title}" has been returned', 'success')
    return redirect(url_for('admin_dashboard'))

# ============= BOOK MANAGEMENT ROUTES =============

@app.route('/add-book')
def add_book_page():
    """Page for adding books (mobile-friendly)"""
    return render_template('add_book.html')

@app.route('/api/add-book', methods=['POST'])
def add_book():
    """API endpoint to add a new book"""
    data = request.json
    
    # Check if RFID already exists
    existing_book = Book.query.filter_by(rfid_uid=data['rfid_uid']).first()
    if existing_book:
        return jsonify({'success': False, 'message': 'This RFID tag is already registered'}), 400
    
    book = Book(
        rfid_uid=data['rfid_uid'],
        title=data['title'],
        author=data['author'],
        language=data['language'],
        shelf_number=data['shelf_number']
    )
    
    db.session.add(book)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Book added successfully'})

@app.route('/api/search-books')
def search_books():
    """Search books by title, author, or language"""
    query = request.args.get('q', '')
    
    books = Book.query.filter(
        db.or_(
            Book.title.ilike(f'%{query}%'),
            Book.author.ilike(f'%{query}%'),
            Book.language.ilike(f'%{query}%')
        )
    ).all()
    
    results = []
    for book in books:
        results.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'language': book.language,
            'shelf_number': book.shelf_number,
            'is_available': book.is_available
        })
    
    return jsonify(results)

# ============= STUDENT ROUTES =============

@app.route('/student')
def student_login():
    """Student login page"""
    return render_template('student_login.html')

@app.route('/api/verify-student', methods=['POST'])
def verify_student():
    """Verify student number"""
    student_number = request.json.get('student_number')
    student = Student.query.filter_by(student_number=student_number).first()
    
    if student:
        return jsonify({
            'success': True,
            'student_id': student.id,
            'name': student.name,
            'student_number': student.student_number
        })
    else:
        return jsonify({'success': False, 'message': 'Student not found'}), 404

@app.route('/student/<int:student_id>')
def student_dashboard(student_id):
    """Student dashboard"""
    student = Student.query.get_or_404(student_id)
    
    # Get student's current borrowings
    current_borrowings = Transaction.query.filter_by(
        student_id=student_id,
        is_returned=False
    ).all()
    
    # Get borrowing history
    history = Transaction.query.filter_by(
        student_id=student_id
    ).order_by(Transaction.borrow_date.desc()).limit(20).all()
    
    return render_template('student_dashboard.html',
                         student=student,
                         current_borrowings=current_borrowings,
                         history=history)

@app.route('/api/borrow-book', methods=['POST'])
def borrow_book():
    """Process book borrowing"""
    data = request.json
    student_id = data.get('student_id')
    rfid_uid = data.get('rfid_uid')
    
    # Find the book
    book = Book.query.filter_by(rfid_uid=rfid_uid).first()
    if not book:
        return jsonify({'success': False, 'message': 'Book not found'}), 404
    
    if not book.is_available:
        # Check if this student has it
        transaction = Transaction.query.filter_by(
            book_id=book.id,
            student_id=student_id,
            is_returned=False
        ).first()
        
        if transaction:
            # Return the book
            transaction.is_returned = True
            transaction.return_date = datetime.utcnow()
            book.is_available = True
            db.session.commit()
            return jsonify({
                'success': True,
                'action': 'returned',
                'message': f'Book "{book.title}" has been returned'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'This book is currently borrowed by another student'
            }), 400
    
    # Borrow the book
    transaction = Transaction(
        book_id=book.id,
        student_id=student_id
    )
    book.is_available = False
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'action': 'borrowed',
        'message': f'Book "{book.title}" has been borrowed'
    })

# Initialize database
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)