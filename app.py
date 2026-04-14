from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
from database import db, Student, Book, Transaction
from werkzeug.utils import secure_filename
import pandas as pd
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Admin password (hardcoded as requested)
ADMIN_PASSWORD = '1234'

# Initialize database
db.init_app(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def admin_required(f):
    """Decorator to protect admin routes with password"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Home page - student access and browse books"""
    return render_template('index.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid password', 'error')
    return render_template('admin_login.html')

@app.route('/admin-logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    return redirect(url_for('index'))

# ============= ADMIN ROUTES =============

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    # Get current borrowings with eager loading of relationships
    current_borrowings = Transaction.query.filter_by(is_returned=False)\
        .join(Student)\
        .join(Book)\
        .options(db.joinedload(Transaction.student), db.joinedload(Transaction.book))\
        .all()
    
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
@admin_required
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
            
            # Debug: print column names to console
            print("Excel columns:", df.columns.tolist())
            
            # Handle different possible column names
            df_columns_lower = {col.lower(): col for col in df.columns}
            
            student_num_col = None
            name_col = None
            
            # Find student number column
            for possible_name in ['student_number', 'student number', 'number', 'id', 'student_id', 'school_number', 'school number']:
                if possible_name in df_columns_lower:
                    student_num_col = df_columns_lower[possible_name]
                    break
                    
            # Find name column
            for possible_name in ['name', 'student_name', 'student name', 'full_name', 'full name']:
                if possible_name in df_columns_lower:
                    name_col = df_columns_lower[possible_name]
                    break
            
            if student_num_col is None or name_col is None:
                flash(f'Excel must contain columns for student number and name. Found columns: {", ".join(df.columns)}', 'error')
                return redirect(url_for('admin_dashboard'))
            
            success_count = 0
            for _, row in df.iterrows():
                # Skip rows with missing data
                if pd.isna(row[student_num_col]) or pd.isna(row[name_col]):
                    continue
                    
                student = Student.query.filter_by(student_number=str(row[student_num_col])).first()
                if not student:
                    student = Student(
                        student_number=str(row[student_num_col]),
                        name=str(row[name_col])
                    )
                    db.session.add(student)
                    success_count += 1
            
            db.session.commit()
            flash(f'Successfully added {success_count} new students', 'success')
        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'error')
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            
    else:
        flash('Please upload an Excel file (.xlsx or .xls)', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export-database')
@admin_required
def export_database():
    """Export database as SQLite file"""
    db_path = os.path.join(os.getcwd(), 'library.db')
    return send_file(db_path, as_attachment=True, download_name='library_backup.db')

@app.route('/admin/import-database', methods=['POST'])
@admin_required
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
@admin_required
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
@admin_required
def add_book_page():
    """Page for adding books (mobile-friendly)"""
    return render_template('add_book.html')

@app.route('/api/add-book', methods=['POST'])
@admin_required
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

@app.route('/browse')
def browse_books():
    """Browse all books page - accessible to anyone"""
    return render_template('browse.html')

@app.route('/api/all-books')
def get_all_books():
    """Get all books with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    books_query = Book.query.order_by(Book.title)
    books_paginated = books_query.paginate(page=page, per_page=per_page, error_out=False)
    
    books = []
    for book in books_paginated.items:
        books.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'language': book.language,
            'shelf_number': book.shelf_number,
            'is_available': book.is_available
        })
    
    return jsonify({
        'books': books,
        'has_next': books_paginated.has_next,
        'has_prev': books_paginated.has_prev,
        'page': page,
        'total_pages': books_paginated.pages
    })

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