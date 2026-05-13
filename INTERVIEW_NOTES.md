# Interview Notes

## One-Line Project Explanation

Employee Management System is a simple admin-based CRUD web application used to manage employee records securely.

## Resume Bullet Points

- Built a Python and SQLite based Employee Management System with admin login and complete CRUD operations.
- Added server-side validation for employee details such as email, phone number, salary, and duplicate records.
- Implemented session-based authentication and password hashing to protect employee data.
- Designed a simple responsive dashboard with employee search, add, edit, and delete features.

## How to Explain the Flow

1. The admin logs in using a username and password.
2. The password is checked against a hashed password stored in SQLite.
3. After login, a session token is saved in the database and browser cookie.
4. The dashboard reads employee records from the database.
5. The admin can add, edit, delete, and search employee records.
6. Before saving data, the backend validates important fields.

## Main Files to Discuss

- `app.py`: Contains routes, database setup, authentication, validation, and CRUD logic.
- `static/style.css`: Contains the UI styling.
- `employees.db`: SQLite database created automatically when the app runs.

## Honest Limitations

This is a student-level project, so it is good for learning and resume demonstration. For production, I would add CSRF tokens, role-based access, deployment settings, audit logs, and stronger testing.
