from flask import Flask, render_template, request, redirect, flash, url_for, session, g, jsonify
from dbhelper import *
from werkzeug.utils import secure_filename
from flask import send_from_directory
from datetime import date, datetime, timedelta
import os
import dbhelper
import random
import sqlite3
import string
import logging

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads/images/'
uploadfolder = "static/images/pictures"
app.config['UPLOAD_FOLDER'] = uploadfolder
app.secret_key = os.urandom(24) 

def generate_verification_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=5))

def send_verification_code(email, user_code):
    print(f"Sending email to: {email}")
    print(f"Verification code: {user_code}")
    
    try:
        print(f"Email content sent to {email}:")
        print(f"Your verification code is: {user_code}")
        print(f"Verification code {user_code} sent to {email}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        flash("There was an error sending the email. Please try again later.", "error")


#LOGIN 
@app.route("/login", methods=['GET', 'POST'])
def login():
    error_message = None

    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            error_message = "Please fill in all fields."
            session['error_message'] = error_message
            return redirect(url_for("login"))

        sql = "SELECT * FROM users WHERE user_email = ?"
        user = getprocess(sql, (email,))

        if user:
            if user[0]["user_password"] == password:
                # Store user_id in the session
                session['user_id'] = user[0]["user_id"]
                print("Session user_id set:", session['user_id'])

                session.pop('error_message', None) 

                # Redirect based on user type
                if user[0]["user_id"] == 1:  # Check if the user is a librarian (assuming user_id == 1 is the librarian)
                    return redirect(url_for("books"))
                else:
                    return redirect(url_for("library"))
            else:
                error_message = "Invalid email or password."
        else:
            error_message = "No user found with that email."
        
        session['error_message'] = error_message
        return redirect(url_for("login"))

    # Retrieve error message from session if it exists
    error_message = session.pop('error_message', None)
    return render_template("login.html", pageheader="Login", error_message=error_message)


#REGISTER
@app.route("/create_account", methods=['GET', 'POST'])
def create_account():
    error_message = None

    if 'error_message' in session:
        error_message = session.pop('error_message', None)

    if request.method == 'POST':
        full_name = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")

        if not full_name or not email or not password:
            session['error_message'] = "Please fill in all fields."
            return redirect(url_for("create_account"))

        # Validate email format
        if "@" not in email or "." not in email.split('@')[-1]:
            session['error_message'] = "Please provide a valid email address."
            return redirect(url_for("create_account"))

        # Check if email already exists
        sql = "SELECT * FROM users WHERE user_email = ?"
        user = getprocess(sql, (email,))

        if user:
            session['error_message'] = "Email is already in use."
            return redirect(url_for("create_account"))

        # Generate a random user verification code
        user_code = ''.join(random.choices(string.digits, k=5))

        # Insert new user into the database
        sql = 'INSERT INTO users (user_name, user_email, user_password, user_code) VALUES (?, ?, ?, ?)'
        params = (full_name, email, password, user_code)

        if postprocess(sql, params): 
            # Fetch the newly inserted user to retrieve the user_id
            # Use a query to fetch the user using their email
            sql = "SELECT * FROM users WHERE user_email = ?"
            new_user = getprocess(sql, (email,))

            if new_user:
                # Set the user_id into the session
                session['user_id'] = new_user[0]["user_id"]

                flash("Account created successfully! Please log in.", "success")
                return redirect(url_for("login"))
            else:
                session['error_message'] = "Failed to retrieve new user details."
                return redirect(url_for("create_account"))
        else:
            session['error_message'] = "Please provide a unique password."
            return redirect(url_for("create_account"))

    return render_template("create_acc.html", error_message=error_message)

#ACCOUNT RECOVERY
@app.route('/account-recovery', methods=['GET', 'POST'])
def account_recov():
    error_message = None 

    if request.method == 'POST':
        email = request.form['email']
        
        if not email:
            error_message = 'Please fill in this field.'
        else:
            sql = "SELECT * FROM users WHERE user_email = ?"
            user = getprocess(sql, (email,))

            if user:
                session['user_email'] = email
                
                user_code = generate_verification_code()
                
                sql_update = "UPDATE users SET user_code = ? WHERE user_email = ?"
                update = postprocess(sql_update, (user_code, email))

                send_verification_code(email, user_code)
                
                flash('Verification code sent to your email!', 'success')
                return redirect(url_for('send_code')) 
            else:
                error_message = 'No user found with that email'  
    
    return render_template('account_recov.html', error_message=error_message)

#SEND CODE
@app.route('/send-code', methods=['GET', 'POST'])
def send_code():
    email = session.get('user_email') 
    
    if not email:
        flash('Session expired. Please start over.', 'error')
        return redirect(url_for('account_recov'))
    
    sql = "SELECT user_code FROM users WHERE user_email = ?"
    result = getprocess(sql, (email,))
    
    if request.method == 'POST':
        entered_code = request.form['user_code']
        
        if result and result[0]['user_code'] == entered_code:
            flash('Code verified successfully. Please reset your password.', 'success')
            return redirect(url_for('reset_pass'))  
        else:
            flash('Invalid verification code. Please try again.', 'error')
    
    return render_template('send_code.html', user_code=result[0]['user_code'] if result else None) 

#CHANGE PASS
@app.route("/reset_pass", methods=['GET', 'POST'])
def reset_pass():
    email = session.get('user_email')
    if not email:
        flash('Session expired. Please start over.', 'error')
        return redirect(url_for('account_recov'))
    
    error_message = None 

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if not new_password or not confirm_password:
            error_message = "Please fill in all fields."
            session['error_message'] = error_message  
            return redirect(url_for('reset_pass'))  

        elif new_password != confirm_password:
            error_message = "Passwords don't match. Please try again."
            session['error_message'] = error_message 
            return redirect(url_for('reset_pass'))  
        else:
            sql_update = "UPDATE users SET user_password = ? WHERE user_email = ?"
            update = postprocess(sql_update, (new_password, email))
            
            if update:
                flash("Password has been successfully reset. Please log in.", 'success')
                session.pop('user_email', None)  
                return redirect(url_for('login')) 
            else:
                error_message = "An error occurred while resetting the password. Please try again."
                session['error_message'] = error_message  
                return redirect(url_for('reset_pass'))  

    if 'error_message' in session:
        error_message = session['error_message']
        session.pop('error_message', None)  

    return render_template('reset_pass.html', error_message=error_message)

#LIBRARIAN BOOKS PAGE
@app.route("/books")
def books() -> None:
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    user_id = session.get('user_id')
    sql = "SELECT * FROM users WHERE user_id = ?"
    user = getprocess(sql, (user_id,))

    if user and user[0]["user_id"] == 1:  # Check if the user is a librarian (assuming user_id == 1 is the librarian)
        search_query = request.args.get('query', '').strip()  # Get the search query from the URL, if any
        
        if search_query:
            # Filter books based on the search query (case-insensitive), checking title, author, or genre
            sql_books = """
            SELECT * FROM books
            WHERE LOWER(book_title) LIKE ? OR LOWER(author) LIKE ? OR LOWER(genre) LIKE ?
            """
            books = getprocess(sql_books, 
                               (f'%{search_query.lower()}%', 
                                f'%{search_query.lower()}%', 
                                f'%{search_query.lower()}%'))
        else:
            books = getall_records('books')  # Fetch all books if no search query

        return render_template("books.html", books=books)
    else:
        flash("You do not have permission to view this page.")
        return redirect(url_for("login"))
    
#ADD BOOK PAGE
@app.route("/addbook")
def addbook():
    # Retrieve the error message from the session
    error_message = session.pop('error_message', None)
    return render_template("addbook.html", error_message=error_message)

@app.route("/savebook", methods=["POST"])
def savebook():
    if 'user_id' not in session or session.get('user_id') != 1:
        session['error_message'] = "You must be logged in as a librarian to add books."
        return redirect(url_for("login"))

    # Get form data
    book_title = request.form.get("book_title")
    author = request.form.get("author")
    publication_year = request.form.get("publication_year")
    genre = request.form.get("genre")
    description = request.form.get("description")
    file = request.files.get("image_upload")

    # Validate all fields
    if not (book_title and author and publication_year and genre and description and file):
        session['error_message'] = "Please complete all book details."
        return redirect(url_for("addbook"))

    # Handle the image upload
    try:
        filename = os.path.join(uploadfolder, file.filename)
        file.save(filename)
    except Exception as e:
        session['error_message'] = "Error uploading image. Please try again."
        return redirect(url_for("addbook"))

    # Insert the book into the database
    sql_insert_book = """
    INSERT INTO books (book_title, author, publication_year, genre, description, image)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    result = postprocess(sql_insert_book, (book_title, author, publication_year, genre, description, filename))

    if result:
        # Retrieve the last book ID and insert into the status table
        sql_get_last_book_id = "SELECT MAX(book_id) AS last_id FROM books"
        last_book_id_result = getprocess(sql_get_last_book_id)
        if last_book_id_result:
            last_book_id = last_book_id_result[0]["last_id"]
            sql_insert_status = """
            INSERT INTO status (book_id, availability)
            VALUES (?, ?)
            """
            postprocess(sql_insert_status, (last_book_id, 'Available'))
            session.pop('error_message', None)  # Clear any existing error messages
            flash(f"The book '{book_title}' has been added successfully.")
            return redirect(url_for("lib_viewbook", book_id=last_book_id))
        else:
            session['error_message'] = "Error retrieving book ID after saving."
    else:
        session['error_message'] = "An error occurred while adding the book."

    return redirect(url_for("addbook"))


#Librarian View Book
@app.route("/lib_viewbook/<int:book_id>")
def lib_viewbook(book_id):
    # Fetch book details
    sql_book = "SELECT * FROM books WHERE book_id = ?"
    book = getprocess(sql_book, (book_id,))

    if not book:  # Handle case where no book is found
        os.abort(404, description="Book not found")

    # Fetch availability status from the status table
    sql_status = "SELECT availability FROM status WHERE book_id = ?"
    status_result = getprocess(sql_status, (book_id,))

    # Extract availability or set to 'Unavailable' if no result
    availability = status_result[0]['availability'] if status_result else 'Unavailable'

    # Pass data to the template
    return render_template("lib_viewbook.html", book=book[0], availability=availability)


# Add this function in your app.py or appropriate database utility file
def get_book_by_id(book_id):
    conn = sqlite3.connect('libroco.db')  # Your database file
    conn.row_factory = sqlite3.Row  # This allows access by column name
    cursor = conn.cursor()
    query = "SELECT * FROM books WHERE book_id = ?"
    cursor.execute(query, (book_id,))
    book = cursor.fetchone()  # Fetch the row as a dictionary-like object
    conn.close()
    return book


@app.route("/view_book_details/<int:book_id>")
def view_book_details(book_id):
    sql = "SELECT * FROM books WHERE book_id = ?"
    book = getprocess(sql, (book_id,))

    if book:
        return render_template("lib_viewbook.html", book=book[0])
    else:
        flash("Book not found.", "error")
        return redirect(url_for("books"))
    

# LIBRARIAN VIEW BOOKKKKKKKKKKKKKKKKKKKKKKK

@app.route('/book/<int:book_id>')
def show_book(book_id):
    """Render the book details page."""
    book = get_book_by_id(book_id)
    
    if book:
        return render_template('book_details.html', book=book)
    else:
        return "Book not found", 404
    
#Librarian Edit Book
# Route to edit book information
@app.route('/book/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if request.method == 'POST':
        # Get form data
        book_title = request.form.get('book_title')
        author = request.form.get('author')
        publication_year = request.form.get('publication_year')
        genre = request.form.get('genre')
        description = request.form.get('description')

        # Check if all fields are completed
        if not (book_title and author and publication_year and genre and description):
            session['error_message'] = "Please complete all book details."
            return redirect(url_for('edit_book', book_id=book_id))

        # Check if a new image file is uploaded
        image_upload = request.files.get('image_upload')
        image_path = None
        if image_upload and image_upload.filename != '':
            # Generate a unique filename using the book_id to avoid filename conflicts
            image_filename = f"{book_id}_{image_upload.filename}"
            image_path = os.path.join(uploadfolder, image_filename)
            try:
                image_upload.save(image_path)
            except Exception:
                session['error_message'] = "Error uploading image. Please try again."
                return redirect(url_for('edit_book', book_id=book_id))

        # If no new image is uploaded, keep the current image path (if exists)
        if not image_path:
            book_data = getprocess("SELECT image FROM books WHERE book_id = ?", (book_id,))
            image_path = book_data[0]['image'] if book_data else 'static/images/blank_image.png'

        # SQL update query
        sql = """
        UPDATE books
        SET book_title = ?, author = ?, publication_year = ?, genre = ?, description = ?, image = ?
        WHERE book_id = ?
        """
        params = (book_title, author, publication_year, genre, description, image_path, book_id)

        # Update the book in the database
        if postprocess(sql, params):
            session.pop('error_message', None)  # Clear any existing error messages
            flash("Book updated successfully")
            return redirect(url_for('view_book_details', book_id=book_id))
        session['error_message'] = "Error updating book"
        return redirect(url_for('edit_book', book_id=book_id))

    # Show edit form if GET request
    book = getprocess("SELECT * FROM books WHERE book_id = ?", (book_id,))
    if book:
        # Retrieve error message from session if it exists
        error_message = session.pop('error_message', None)
        return render_template('edit_book.html', book=dict(book[0]), error_message=error_message)
    flash("Book not found")
    return redirect(url_for('books'))


# Delete Book
@app.route('/delete_book/<int:book_id>', methods=['GET'])
def delete_book(book_id):
    try:
        # Delete related entries from requests, status, and wishlist
        dbhelper.postprocess("DELETE FROM requests WHERE book_id = ?", (book_id,))
        dbhelper.postprocess("DELETE FROM status WHERE book_id = ?", (book_id,))
        dbhelper.postprocess("DELETE FROM wishlist WHERE book_id = ?", (book_id,))
        
        # Delete the book from the books table
        deleted = dbhelper.postprocess("DELETE FROM books WHERE book_id = ?", (book_id,))
        
        if deleted:
            flash("Book deleted successfully!", "success")
        else:
            flash("Book not found or couldn't be deleted.", "error")
    except Exception as e:
        print(f"Error deleting book: {e}")
        flash("An error occurred while trying to delete the book.", "error")
    
    # Redirect to books page
    return redirect(url_for('books'))


# Route to list all books
@app.route('/books')
def list_books():
    books = getall_records("books")
    return render_template('list_books.html', books=books)

@app.route("/borrow", methods=["POST"])
def borrow():
    if 'user_id' not in session:
        flash("You must be logged in to borrow a book.")
        return redirect(url_for('login'))

    book_id = request.form.get("book_id")
    user_id = session.get('user_id')

    # Check the availability of the book
    sql_check_availability = "SELECT availability FROM status WHERE book_id = ?"
    availability = getprocess(sql_check_availability, (book_id,))

    if availability and availability[0]['availability'] == 'Available':
        # Insert borrow request into requests table
        sql_insert_request = """
        INSERT INTO requests (user_id, book_id)
        VALUES (?, ?)
        """
        result = postprocess(sql_insert_request, (user_id, book_id))

        if result:
            flash("Your borrow request has been submitted to the librarian.")
            print(f"Request inserted: user_id = {user_id}, book_id = {book_id}")  # Debug log
            return redirect(url_for("library"))
        else:
            flash("There was an issue submitting your request. Please try again.")
            return redirect(url_for("view_book", book_id=book_id))  # Stay on the same book page
    else:
        flash("This book is currently unavailable for borrowing.")
        return redirect(url_for("view_book", book_id=book_id))  # Stay on the same book page
   

@app.route('/approve_request/<int:request_id>', methods=['POST'])
def approve_request(request_id):
    # Set due date to 30 days from today
    due_date = (datetime.now() + timedelta(days=30)).date()

    # Get the book_id and user_id from the request
    book = getprocess("SELECT book_id, user_id FROM requests WHERE request_id = ?", (request_id,))
    if book:
        book_id = book[0]['book_id']
        user_id = book[0]['user_id']

        # Update the request to "Approved" and set the due date
        postprocess("""
            UPDATE requests
            SET status = 'Approved', due_date = ?
            WHERE request_id = ?;
        """, (due_date, request_id))

        # Insert a record into the book_transactions table to mark the book as borrowed
        postprocess("""
            INSERT INTO book_transactions (user_id, book_id, borrow_date, due_date, status)
            VALUES (?, ?, ?, ?, 'Borrowed');
        """, (user_id, book_id, datetime.now().date(), due_date))

        # Mark the book as unavailable
        postprocess("""
            UPDATE status
            SET availability = 'Unavailable'
            WHERE book_id = ?;
        """, (book_id,))

        # Remove all other requests for the same book
        postprocess("""
            DELETE FROM requests
            WHERE book_id = ? AND status = 'Pending';
        """, (book_id,))

    flash("Borrow request approved successfully.")
    return redirect(url_for('requests'))


def auto_return_overdue_books():
    today = datetime.now().date()

    # Find overdue books
    overdue_books = getprocess("""
        SELECT book_id
        FROM requests
        WHERE due_date < ? AND status = 'Approved';
    """, (today,))

    for book in overdue_books:
        book_id = book['book_id']
        
        # Mark the request as "Returned"
        postprocess("""
            UPDATE requests
            SET status = 'Returned'
            WHERE book_id = ? AND status = 'Approved';
        """, (book_id,))
        
        # Mark the book as "Available"
        postprocess("""
            UPDATE status
            SET availability = 'Available'
            WHERE book_id = ?;
        """, (book_id,))


@app.route("/return_book/<int:book_id>", methods=["POST"])
def return_book(book_id):
    if 'user_id' not in session:
        return redirect(url_for("login"))

    # Update the status table to make the book available
    sql_update_status = "UPDATE status SET availability = 'Available' WHERE book_id = ?"
    postprocess(sql_update_status, (book_id,))

    # Mark the transaction as returned
    sql_update_transaction = """
    UPDATE book_transactions
    SET status = 'Returned', return_date = ?
    WHERE book_id = ? AND user_id = ? AND status = 'Borrowed'
    """
    postprocess(sql_update_transaction, (datetime.now().date(), book_id, session['user_id']))

    flash("You have successfully returned the book.")
    return redirect(url_for("my_books"))

@app.route("/renew_book/<int:book_id>", methods=["POST"])
def renew_book(book_id):
    if 'user_id' not in session:
        return redirect(url_for("login"))

    # Extend the due date by 7 days
    sql_update_due_date = """
    UPDATE book_transactions
    SET due_date = DATE(due_date, '+7 days')
    WHERE book_id = ? AND user_id = ? AND status = 'Borrowed'
    """
    postprocess(sql_update_due_date, (book_id, session['user_id']))

    flash("You have successfully renewed the book for an additional 7 days.")
    return redirect(url_for("my_books"))


@app.route("/decline_request", methods=["POST"])
def decline_request():
    # Ensure the librarian is logged in
    if 'user_id' not in session or session.get('user_id') != 1:
        flash("You must be logged in as a librarian to decline requests.")
        return redirect(url_for("login"))

    # Get the request_id from the form
    request_id = request.form.get("request_id")

    # Delete the request from the requests table
    sql_delete_request = "DELETE FROM requests WHERE request_id = ?"
    postprocess(sql_delete_request, (request_id,))

    flash(f"The request has been declined.")

    return redirect(url_for("requests"))

@app.route("/requests")
def requests():
    # Ensure the librarian is logged in
    if 'user_id' not in session or session.get('user_id') != 1:
        flash("You must be logged in as a librarian to view requests.")
        return redirect(url_for("login"))

    # Get all pending borrow requests
    sql_get_requests = """
    SELECT b.book_title, b.author, b.genre, s.availability, u.user_name, r.request_id
    FROM requests r
    JOIN books b ON r.book_id = b.book_id
    JOIN users u ON r.user_id = u.user_id
    JOIN status s ON b.book_id = s.book_id
    WHERE r.status = 'Pending'  -- Only show pending requests
    """
    requests = getprocess(sql_get_requests)

    return render_template("requests.html", requests=requests)

#REQUESTS PAGE
def get_requests():
    # Connect to the database
    conn = sqlite3.connect('libroco.db')
    cursor = conn.cursor()
    
    # Query to get all requests along with book and user information
    cursor.execute("""
        SELECT books.book_title, books.author, books.genre, status.availability, users.user_name, requests.request_id
        FROM requests
        JOIN books ON requests.book_id = books.book_id
        JOIN users ON requests.user_id = users.user_id
        LEFT JOIN status ON books.book_id = status.book_id
    """)
    
    # Fetch all results
    requests = cursor.fetchall()
    conn.close()
    
    return requests

@app.route('/uploads/images/<filename>')
def upload_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

#READERS PAGE
@app.route("/readers")
def readers():
    all_users = getall_records("users")
    readers = [user for user in all_users if user["user_id"] != 1]

    readers_with_history = []
    for reader in readers:
        reader_id = reader['user_id']

        # Fetch book history
        sql_history = """
            SELECT books.book_title 
            FROM requests
            JOIN books ON requests.book_id = books.book_id
            WHERE requests.user_id = ?
        """
        history = getprocess(sql_history, (reader_id,))

        # Fetch user image
        sql_image = """
            SELECT user_image
            FROM profileimages
            WHERE user_id = ?
        """
        user_image = getprocess(sql_image, (reader_id,))
        image_path = f"static/{user_image[0]['user_image']}" if user_image else url_for('static', filename='images/default_profile.png')

        readers_with_history.append({
            "name": reader["user_name"],
            "contact": reader["user_contact"] or "",
            "email": reader["user_email"],
            "history": [h['book_title'] for h in history],
            "user_image": image_path  # Pass the relative image path to the template
        })

    # Sort readers by name
    readers_with_history = sorted(readers_with_history, key=lambda x: x['name'].lower())

    return render_template("readers.html", readers=readers_with_history)

#READER'S BOOK HISTORY
@app.route("/reader_history/<int:user_id>")
def reader_history(user_id):
    sql_history = """
        SELECT books.book_title
        FROM requests
        JOIN books ON requests.book_id = books.book_id
        WHERE requests.user_id = ?
    """
    history = getprocess(sql_history, (user_id,))
    book_titles = [h['book_title'] for h in history]
    return {"history": book_titles}
    

#EDIT READER'S PROFILE
@app.route("/edit_reader")
def edit_reader():
    return render_template("editreader.html")

@app.route("/update_reader")
def update_reader():
    return render_template("editreader.html")

#VIEW LIBRARIAN PROFILE
@app.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect(url_for("login"))

    user_id = session['user_id']

    sql = """
    SELECT u.user_name, u.user_email, u.user_contact, 
           COALESCE(p.user_image, 'static/images/default_profile.png') AS user_image
    FROM users u
    LEFT JOIN profileimages p ON u.user_id = p.user_id
    WHERE u.user_id = ?
    """
    user = getprocess(sql, (user_id,))

    if user:
        user_data = dict(user[0])
        user_data['user_image'] = user_data['user_image'].replace("\\", "/")
        return render_template("profile.html", user=user_data)
    else:
        flash("Error loading profile.")
        return redirect(url_for("login"))

@app.before_request
def before_request():
    print("Session data:", session)


@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if 'user_id' not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    user_id = session['user_id']

    if user_id != 1:
        flash("You do not have permission to edit this profile.")
        return redirect(url_for("reader_profile"))

    uploadfolder = os.path.join('static', 'images')
    if not os.path.exists(uploadfolder):
        os.makedirs(uploadfolder)

    error_message = ""

    if request.method == "POST":
        full_name = request.form['full_name']
        contact = request.form['contact']
        email = request.form['email']

        if "@" not in email or "." not in email.split("@")[-1]:
            error_message = "Please enter a valid email address."

        # Check if full_name is empty
        if not full_name or not email:  # If full_name or email are empty
            error_message = "Please fill in all fields correctly."
        elif not contact.isdigit():  # If contact contains non-numeric values
            error_message = "Contact number must contain only digits."

        # If any error message is set, return with the error
        if error_message:
            return render_template("editprofile.html", error_message=error_message, user={
                "full_name": full_name,
                "contact": contact,
                "email": email,
                "user_image": request.form.get('current_image', 'static/images/default_profile.png')
            })

        file = request.files.get('user_image')
        if file:
            filename = os.path.join(uploadfolder, file.filename)
            try:
                file.save(filename)  
            except Exception as e:
                flash(f"Error saving the image: {str(e)}")
                filename = 'static/images/default_profile.png'
        else:
            filename = request.form.get('current_image', 'static/images/default_profile.png')

        sql_update_user = """
            UPDATE users
            SET user_name = ?, user_contact = ?, user_email = ?
            WHERE user_id = ?
        """
        params = (full_name, contact, email, user_id)
        result = postprocess(sql_update_user, params)

        check_image_sql = "SELECT * FROM profileimages WHERE user_id = ?"
        existing_image = getprocess(check_image_sql, (user_id,))

        if existing_image:
            sql_update_image = """
                UPDATE profileimages
                SET user_image = ?
                WHERE user_id = ?
            """
            postprocess(sql_update_image, (filename, user_id))
        else:
            sql_insert_image = """
                INSERT INTO profileimages (user_id, user_image)
                VALUES (?, ?)
            """
            postprocess(sql_insert_image, (user_id, filename))

        if result:
            flash("Profile updated successfully.")
        else:
            flash("An error occurred while updating the profile.")

        return redirect(url_for("profile"))

    sql = """
        SELECT u.user_name, u.user_email, u.user_contact, p.user_image
        FROM users u
        LEFT JOIN profileimages p ON u.user_id = p.user_id
        WHERE u.user_id = ?
    """
    user_data = getprocess(sql, (user_id,))

    if user_data:
        user = user_data[0]
        user_data = {
            "full_name": user["user_name"],
            "email": user["user_email"],
            "contact": user["user_contact"],
            "user_image": user["user_image"] if user["user_image"] else 'static/images/default_profile.png'
        }
        return render_template("editprofile.html", user=user_data)
    else:
        flash("Error loading profile.")
        return redirect(url_for("profile"))


#LOGOUT
@app.route("/logout", methods=['GET'])
def logout():
    print("Logout initiated.")  
    session.clear() 
    print("Session cleared.") 
    return redirect(url_for("login"))

@app.route("/")
def index():
    return render_template("login.html", pageheader="Login")
    return render_template('your_template.html', book={
        'book_title': 'Example Book',
        'author': 'Author Name',
        'publication_year': '2024',
        'genre': 'Fiction',
        'description': 'This is a description of the book.',
        'image': 'mermeed.png'
    })

#READER'S LIBRARY
@app.route("/library")
def library():
    if 'user_id' not in session:
        return redirect(url_for("login"))

    user_id = session.get('user_id')
    sql = "SELECT * FROM users WHERE user_id = ?"
    user = getprocess(sql, (user_id,))

    if user:
        search_query = request.args.get('query', '').strip()
        
        if search_query:
            # Filter books based on the search query (case-insensitive), checking title, author, or genre
            sql_books = """
            SELECT * FROM books
            WHERE LOWER(book_title) LIKE ? OR LOWER(author) LIKE ? OR LOWER(genre) LIKE ?
            """
            # Search will match any part of book title, author, or genre, case-insensitive
            books = getprocess(sql_books, 
                               (f'%{search_query.lower()}%', 
                                f'%{search_query.lower()}%', 
                                f'%{search_query.lower()}%'))
        else:
            books = getall_records('books')  # Fetch all books if no search query

        return render_template("library.html", books=books)
    else:
        flash("You do not have permission to view this page.")
        return redirect(url_for("login"))
    
#READER'S VIEW BOOK    
@app.route("/view_book/<int:book_id>", methods=["GET"])
def view_book(book_id):
    # Fetch book details from the books table
    sql_book = "SELECT * FROM books WHERE book_id = ?"
    book = getprocess(sql_book, (book_id,))

    # Fetch availability status from the status table
    sql_status = "SELECT availability FROM status WHERE book_id = ?"
    status_result = getprocess(sql_status, (book_id,))
    
    # If status is found, set availability, else default to 'Unavailable'
    availability = status_result[0]['availability'] if status_result else 'Unavailable'

    # Pass both book and availability status to the template
    return render_template("view_book.html", book=book[0], availability=availability)

      
@app.route("/book2/<int:book_id>")
def book2(book_id):
    sql = "SELECT * FROM books WHERE book_id = ?"
    book = getprocess(sql, (book_id,))

    if book:
        return render_template("view_book.html", book=book[0])
    else:
        flash("Book not found.", "error")
        return redirect(url_for("books"))

#READER'S BORROWED BOOKS
# Function to fetch borrowed books from the database
def get_borrowed_books(user_id):
    """
    Retrieve the borrowed books for a specific user.
    """
    conn = sqlite3.connect('libroco.db')  # Connect to your database
    conn.row_factory = sqlite3.Row       # Return rows as dictionaries
    cursor = conn.cursor()

    # Query to fetch borrowed books with details
    query = """
    SELECT 
        bt.book_id,
        b.book_title,
        b.author,
        b.image,
        bt.due_date
    FROM 
        book_transactions bt
    JOIN 
        books b ON bt.book_id = b.book_id
    WHERE 
        bt.user_id = ? AND bt.status = 'Borrowed'
    ORDER BY 
        bt.due_date ASC
    """
    cursor.execute(query, (user_id,))
    books = cursor.fetchall()
    conn.close()
    return books

# Route to display borrowed books
@app.route('/my_books')
def my_books():
    if 'user_id' not in session:  # Check if the user is logged in
        return redirect(url_for('login'))

    user_id = session['user_id']  # Get the logged-in user's ID
    books = get_borrowed_books(user_id)  # Fetch borrowed books for the user
    today = date.today()  # Current date
    expiring_date = today + timedelta(days=3)  # Threshold for expiring books

    # Parse due_date into datetime.date object for each book
    for i, book in enumerate(books):
        book_dict = dict(book)  # Convert the sqlite3.Row object to a dictionary
        if isinstance(book_dict['due_date'], str):  # Check if due_date is a string
            try:
                # Attempt to convert string 'YYYY-MM-DD' to a datetime.date object
                book_dict['due_date'] = datetime.strptime(book_dict['due_date'], '%Y-%m-%d').date()
            except ValueError:
                # Handle any unexpected date format here, if needed
                book_dict['due_date'] = None  # Default to None if conversion fails

        # Replace the original book with the updated dictionary
        books[i] = book_dict

    # Render the template with the necessary data
    return render_template(
        'my_books.html', 
        books=books, 
        today=today, 
        expiring_date=expiring_date
    )

@app.route("/borrow_book/<int:book_id>")
def borrow_book(book_id):
    if 'user_id' not in session:
        return redirect(url_for("login"))

    user_id = session['user_id']  # Get user_id from the session

    # Get the current date and the due date (for example, 14 days from now)
    borrow_date = datetime.today().date()
    due_date = borrow_date + timedelta(days=14)

    # Check if the book is available (status = 'Available')
    sql_check_availability = "SELECT availability FROM status WHERE book_id = ?"
    status = getprocess(sql_check_availability, (book_id,))

    if status and status[0]['availability'] == 'Available':
        # Insert the borrow transaction
        sql_insert_transaction = """
        INSERT INTO book_transactions (user_id, book_id, borrow_date, due_date, status)
        VALUES (?, ?, ?, ?, 'Borrowed')
        """
        postprocess(sql_insert_transaction, (user_id, book_id, borrow_date, due_date))

        # Update the book's availability to 'Unavailable'
        sql_update_status = "UPDATE status SET availability = 'Unavailable' WHERE book_id = ?"
        postprocess(sql_update_status, (book_id,))

        flash("You have successfully borrowed the book.")
    else:
        flash("This book is not available for borrowing.")

    return redirect(url_for("books"))


#VIEW READER PROFILE
@app.route("/reader_profile")
def reader_profile():
    print("Session data in reader profile route:", session) 
    if 'user_id' not in session:
        return redirect(url_for("login"))

    user_id = session.get('user_id')

    sql_user = """
    SELECT u.user_name, u.user_email, u.user_contact, p.user_image
    FROM users u
    LEFT JOIN profileimages p ON u.user_id = p.user_id
    WHERE u.user_id = ?
    """
    user = getprocess(sql_user, (user_id,))

    if user:
        user_data = user[0]

        sql_history = """
        SELECT books.book_title, books.author, books.genre, requests.request_date
        FROM requests
        JOIN books ON requests.book_id = books.book_id
        WHERE requests.user_id = ?
        """
        history = getprocess(sql_history, (user_id,))

        book_history = [
            {
                "title": record['book_title'],
                "author": record['author'],
                "genre": record['genre'],
                "date": record['request_date']
            }
            for record in history
        ]

        return render_template(
            "reader_profile.html",
            user=user_data,
            book_history=book_history
        )
    else:
        flash("Profile not found.")
        return redirect(url_for("login"))

#EDIT READER PROFILE (READER DASHBOARD)
@app.route("/edit_reader_profile", methods=["GET", "POST"])
def edit_reader_profile():
    if 'user_id' not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    user_id = session['user_id']

    # Ensure only the reader can edit their profile
    if user_id == 1:
        flash("Librarians cannot edit reader profiles.")
        return redirect(url_for("reader_profile"))

    uploadfolder = os.path.join('static', 'images')
    if not os.path.exists(uploadfolder):
        os.makedirs(uploadfolder)

    error_message = None  # Initialize the error message variable

    if request.method == "POST":
        full_name = request.form['full_name']
        contact = request.form['contact']
        email = request.form['email']

        if "@" not in email or "." not in email.split("@")[-1]:
            error_message = "Please enter a valid email address."
        # Error handling for empty fields
        if not full_name or not email:  # If full_name or email are empty
            error_message = "Please fill in all fields correctly."
        elif not contact.isdigit():  # If contact contains non-numeric values
            error_message = "Contact number must contain only digits."

        if error_message is None:  # Only proceed if there are no errors
            file = request.files.get('user_image')
            if file:
                filename = os.path.join(uploadfolder, file.filename)
                try:
                    file.save(filename)
                    filename = 'images/' + file.filename  # Save only the relative path
                except Exception as e:
                    flash(f"Error saving the image: {str(e)}")
                    filename = 'images/default_profile.png'
            else:
                filename = request.form.get('current_image', 'images/default_profile.png')

            relative_path = filename

            # Update user profile information
            sql_update_user = """
                UPDATE users
                SET user_name = ?, user_contact = ?, user_email = ?
                WHERE user_id = ?
            """
            params = (full_name, contact, email, user_id)
            result = postprocess(sql_update_user, params)

            # Update profile image if changed, otherwise insert a new one
            check_image_sql = "SELECT * FROM profileimages WHERE user_id = ?"
            existing_image = getprocess(check_image_sql, (user_id,))
            if existing_image:
                sql_update_image = """
                    UPDATE profileimages
                    SET user_image = ?
                    WHERE user_id = ?
                """
                postprocess(sql_update_image, (relative_path, user_id))
            else:
                sql_insert_image = """
                    INSERT INTO profileimages (user_id, user_image)
                    VALUES (?, ?)
                """
                postprocess(sql_insert_image, (user_id, relative_path))

            if result:
                flash("Profile updated successfully.")
            else:
                flash("An error occurred while updating the profile.")

            return redirect(url_for("reader_profile"))

    sql = """
        SELECT u.user_name, u.user_email, u.user_contact, p.user_image
        FROM users u
        LEFT JOIN profileimages p ON u.user_id = p.user_id
        WHERE u.user_id = ?
    """
    user_data = getprocess(sql, (user_id,))

    if user_data:
        user = user_data[0]
        user_data = {
            "full_name": user["user_name"],
            "email": user["user_email"],
            "contact": user["user_contact"],
            "user_image": user["user_image"] if user["user_image"] else 'static/images/default_profile.png'
        }
        return render_template("reader-editprofile.html", user=user_data, error_message=error_message)
    else:
        flash("Error loading profile.")
        return redirect(url_for("reader_profile"))


# KEBIN READER WISHLIST FUNCTIONS
# Connect to the database
def get_db_connection():
    conn = sqlite3.connect('libroco.db')
    conn.row_factory = sqlite3.Row
    return conn

# Route to add a book to the wishlist
@app.route('/add_to_wishlist/<int:book_id>')
def add_to_wishlist(book_id):
    user_id = session.get('user_id')  # Assuming user_id is stored in session

    if not user_id:
        flash("You need to log in to add books to your wishlist.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        # Add book to wishlist if it doesn't already exist
        conn.execute(
            'INSERT INTO wishlist (book_id, user_id) VALUES (?, ?)',
            (book_id, user_id)
        )
        conn.commit()
        flash("Book added to wishlist!")
    except sqlite3.IntegrityError:
        flash("This book is already in your wishlist.")
    finally:
        conn.close()

    return redirect(url_for('wishlist'))


# Route to display the wishlist
@app.route('/wishlist')
def wishlist():
    user_id = session.get('user_id')  # Assuming user_id is stored in session

    if not user_id:
        flash("You need to log in to view your wishlist.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    wishlist_books = conn.execute(
        '''
        SELECT books.* 
        FROM wishlist
        JOIN books ON wishlist.book_id = books.book_id
        WHERE wishlist.user_id = ?
        ''',
        (user_id,)
    ).fetchall()
    conn.close()

    return render_template('wishlist.html', request=wishlist_books)


# Route to remove a book from the wishlist
@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    user_id = session.get('user_id')  # Assuming user_id is stored in session
    book_id = request.form.get('book_id')

    if not user_id:
        flash("You need to log in to modify your wishlist.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute(
        'DELETE FROM wishlist WHERE book_id = ? AND user_id = ?',
        (book_id, user_id)
    )
    conn.commit()
    conn.close()

    flash("Book removed from wishlist.")
    return redirect(url_for('wishlist'))

@app.route("/remove_selected_books", methods=["POST"])
def remove_selected_books():
    data = request.get_json()
    book_ids = data.get("books", [])  # List of book IDs to delete

    if not book_ids:
        return jsonify(success=False, message="No books selected.")

    user_id = session.get("user_id")  # Retrieve user ID from session

    if not user_id:
        return jsonify(success=False, message="User not authenticated.")

    # Construct the SQL for bulk deletion
    placeholders = ",".join(["?"] * len(book_ids))
    sql = f"DELETE FROM wishlist WHERE book_id IN ({placeholders}) AND user_id = ?"

    # Execute the SQL with book IDs and the user ID
    params = tuple(book_ids) + (user_id,)
    success = postprocess(sql, params)

    if success:
        return jsonify(success=True, message="Selected books successfully removed.")
    return jsonify(success=False, message="Failed to remove selected books.")

@app.route("/some_route/<int:book_id>")
def some_route(book_id):
    return redirect(url_for("view_book", book_id=book_id))

if __name__ == "__main__":
    app.config.update(
        SESSION_COOKIE_NAME='my_session',
        SESSION_COOKIE_SECURE=False,  # Set this to True in production
        SESSION_PERMANENT=False
    )
    app.debug = True
    app.run(debug=True)