# Employee Management System
This project was built as a simple final year/prefinal year CRUD application for learning backend basics.

A simple web application for managing employee records. It supports admin login, CRUD operations, search, validation, password hashing, and SQLite database storage.

This project is intentionally kept beginner-friendly so it can be explained easily in interviews.

## Features

- Admin authentication with session cookie
- Add employee records
- View all employee records
- Update employee details
- Delete employee records
- Search by name, email, department, or role
- Server-side validation for required fields, email, phone number, salary, and duplicate email
- SQLite database, created automatically when the app starts

## Tech Stack

- Python
- SQLite
- HTML
- CSS
- No external packages required

## How to Run

Open this folder in a terminal and run:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

Demo admin login:

```text
Username: admin
Password: admin123
```

## Project Structure

```text
employee-management-system/
  app.py
  employees.db
  static/
    style.css
  README.md
```

The `employees.db` file is created automatically after running the project.

## Project Overview

This is a CRUD-based Employee Management System made for admins. The admin must login before accessing employee data. After login, the admin can create, read, update, and delete employee records. The project uses SQLite for storing data and Python's built-in HTTP server for handling routes.

The important parts to explain are:

- `init_db()` creates the database tables and default admin.
- `current_admin()` checks whether a user is logged in using a session token.
- `validate_employee()` protects data quality before insert or update.
- `dashboard()` reads employee records and supports search.
- `create_employee()`, `update_employee()`, and `delete_employee()` perform CRUD operations.

## Possible Future Improvements

- Add separate roles like HR and Manager
- Add pagination for large employee lists
- Add export to CSV
- Add profile photo upload
- Add stronger CSRF protection for production use
