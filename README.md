# RFID-NFC-School-Library
together lets plan a rfid based library system
Every book will have a dedicated rfid tag.
Every book wolud be saved into the system by its name,language,author and place number (which shelf etc.) 
Students will insert their school number and then scan the books rfid tag.
Administrators should be able to see who has which books into custody.
Book names,authors or language shoul be searchable

Requirentments:
Can be run on computer.
Database can be exported and reuploaded.
Can take student names&school number as a excel sheet.
administrator would load student info (names and school number) by excel table.

Hardware
Normal computer, usb-rfid reader


Software :
UI admin : can upload student info,add books 
UI book add : 
Since the RFID UID appears on your phone screen, you can simply **type or copy-paste** that number into a web form.
- Create a mobile-optimized web page on your Flask server (e.g., `http://your-computer-ip:5000/add-book`)
    
- The page contains a simple form with fields:
    - RFID UID (manual entry)
    - Book Title
    - Author
    - Language
    - Shelf/Location Number

**Workflow:**
1. Staff opens this page on phone's browser
2. Scans book with phone's NFC/RFID app
3. Copies the UID from screen, pastes into form
4. Fills other details
5. Submits → saves directly to database
UI student :can take and give books , search books

Design Goals:
Do not make things harder for to debug. Go with the usable safest opiton.
I need a plain UI I dont need and fancy things so do not add anything uncessary 


RFID-Library-System/
├── app.py                 # Main Flask application
├── database.py           # Database models and operations
├── requirements.txt      # Python dependencies
├── templates/            # HTML templates
│   ├── admin.html        # Admin dashboard
│   ├── add_book.html     # Book addition form
│   ├── student.html      # Student interface
│   └── search.html       # Search results
├── static/               # CSS/JS files
│   └── style.css
├── uploads/              # For Excel file uploads
└── library.db            # SQLite database

Further Future Things
MIT App Inventor: 
Can read the nfc tags but not their number rather their info. Nearİnfo component
We could just do everything on the phone? I mean if we can acess the database 
