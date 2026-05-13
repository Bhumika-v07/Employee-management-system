from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import hashlib
import html
import os
import secrets
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "employees.db")
HOST = "127.0.0.1"
PORT = 8000


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return f"{salt}${hashed.hex()}"


def check_password(password, stored_hash):
    salt, _ = stored_hash.split("$", 1)
    return hash_password(password, salt) == stored_hash


def init_db():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                admin_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(admin_id) REFERENCES admins(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                department TEXT NOT NULL,
                role TEXT NOT NULL,
                salary REAL NOT NULL,
                joining_date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        admin = db.execute("SELECT id FROM admins WHERE username = ?", ("admin",)).fetchone()
        if admin is None:
            db.execute(
                "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                ("admin", hash_password("admin123")),
            )


def page(title, body, username=None):
    nav = ""
    if username:
        nav = f"""
        <nav class="topbar">
            <a class="brand" href="/">EmployeeMS</a>
            <div>
                <span class="muted">Logged in as {escape(username)}</span>
                <a class="button ghost" href="/logout">Logout</a>
            </div>
        </nav>
        """

    return f"""<!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{escape(title)} | Employee Management System</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        {nav}
        <main class="container">
            {body}
        </main>
    </body>
    </html>"""


def escape(value):
    return html.escape(str(value), quote=True)


def employee_form(employee=None, errors=None, heading="Add Employee"):
    employee = employee or {}
    errors = errors or []
    action = "/employees/create" if not employee.get("id") else f"/employees/{employee['id']}/edit"
    error_html = render_errors(errors)

    def value(key):
        return escape(employee.get(key, ""))

    return f"""
    <section class="panel narrow">
        <div class="section-head">
            <div>
                <p class="eyebrow">Employee Record</p>
                <h1>{escape(heading)}</h1>
            </div>
            <a class="button ghost" href="/">Back</a>
        </div>
        {error_html}
        <form method="post" action="{action}" class="form-grid">
            <label>
                Full Name
                <input name="name" value="{value('name')}" placeholder="e.g. Ananya Sharma" required>
            </label>
            <label>
                Email
                <input type="email" name="email" value="{value('email')}" placeholder="name@company.com" required>
            </label>
            <label>
                Phone
                <input name="phone" value="{value('phone')}" placeholder="10 digit number" required>
            </label>
            <label>
                Department
                <select name="department" required>
                    {department_options(employee.get('department'))}
                </select>
            </label>
            <label>
                Role
                <input name="role" value="{value('role')}" placeholder="e.g. HR Executive" required>
            </label>
            <label>
                Monthly Salary
                <input type="number" min="1" step="0.01" name="salary" value="{value('salary')}" required>
            </label>
            <label>
                Joining Date
                <input type="date" name="joining_date" value="{value('joining_date')}" required>
            </label>
            <button class="button primary" type="submit">Save Employee</button>
        </form>
    </section>
    """


def department_options(selected):
    departments = ["HR", "Engineering", "Finance", "Marketing", "Sales", "Operations"]
    options = []
    for department in departments:
        checked = "selected" if department == selected else ""
        options.append(f'<option value="{department}" {checked}>{department}</option>')
    return "\n".join(options)


def render_errors(errors):
    if not errors:
        return ""
    items = "".join(f"<li>{escape(error)}</li>" for error in errors)
    return f'<ul class="alert">{items}</ul>'


def validate_employee(data, current_id=None):
    errors = []
    required_fields = ["name", "email", "phone", "department", "role", "salary", "joining_date"]
    for field in required_fields:
        if not data.get(field, "").strip():
            errors.append(f"{field.replace('_', ' ').title()} is required.")

    if data.get("email") and "@" not in data["email"]:
        errors.append("Enter a valid email address.")

    if data.get("phone") and (not data["phone"].isdigit() or len(data["phone"]) != 10):
        errors.append("Phone number must contain exactly 10 digits.")

    try:
        salary = float(data.get("salary", 0))
        if salary <= 0:
            errors.append("Salary must be greater than zero.")
    except ValueError:
        errors.append("Salary must be a number.")

    with get_db() as db:
        row = db.execute("SELECT id FROM employees WHERE email = ?", (data.get("email"),)).fetchone()
        if row and row["id"] != current_id:
            errors.append("An employee with this email already exists.")

    return errors


class EmployeeApp(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/static/style.css":
            self.serve_static("style.css", "text/css")
            return
        if path == "/login":
            self.show_login()
            return
        if path == "/logout":
            self.logout()
            return

        admin = self.current_admin()
        if not admin:
            self.redirect("/login")
            return

        if path == "/":
            self.dashboard(admin)
        elif path == "/employees/new":
            self.html(page("Add Employee", employee_form(), admin["username"]))
        elif path.startswith("/employees/") and path.endswith("/edit"):
            self.edit_employee_form(path, admin)
        elif path.startswith("/employees/") and path.endswith("/delete"):
            self.delete_employee(path)
        else:
            self.not_found()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/login":
            self.login()
            return

        admin = self.current_admin()
        if not admin:
            self.redirect("/login")
            return

        if path == "/employees/create":
            self.create_employee(admin)
        elif path.startswith("/employees/") and path.endswith("/edit"):
            self.update_employee(path, admin)
        else:
            self.not_found()

    def dashboard(self, admin):
        query = parse_qs(urlparse(self.path).query).get("q", [""])[0].strip()
        with get_db() as db:
            if query:
                employees = db.execute(
                    """
                    SELECT * FROM employees
                    WHERE name LIKE ? OR email LIKE ? OR department LIKE ? OR role LIKE ?
                    ORDER BY id DESC
                    """,
                    tuple([f"%{query}%"] * 4),
                ).fetchall()
            else:
                employees = db.execute("SELECT * FROM employees ORDER BY id DESC").fetchall()

        rows = "".join(render_employee_row(employee) for employee in employees)
        if not rows:
            rows = '<tr><td colspan="8" class="empty">No employee records found.</td></tr>'

        body = f"""
        <section class="hero">
            <div>
                <p class="eyebrow">Admin Dashboard</p>
                <h1>Employee Management System</h1>
                <p class="subtitle">A simple CRUD web app with login, validation, search, and SQLite storage.</p>
            </div>
            <a class="button primary" href="/employees/new">Add Employee</a>
        </section>

        <section class="panel">
            <div class="section-head">
                <h2>Employee Records</h2>
                <form class="search" method="get" action="/">
                    <input name="q" value="{escape(query)}" placeholder="Search employee">
                    <button class="button" type="submit">Search</button>
                </form>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Phone</th>
                            <th>Department</th>
                            <th>Role</th>
                            <th>Salary</th>
                            <th>Joining Date</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </section>
        """
        self.html(page("Dashboard", body, admin["username"]))

    def show_login(self, errors=None):
        body = f"""
        <section class="login-card">
            <p class="eyebrow">Secure Admin Access</p>
            <h1>Employee Management System</h1>
            <p class="subtitle">Use admin / admin123 to login for the demo.</p>
            {render_errors(errors or [])}
            <form method="post" action="/login" class="form-grid">
                <label>
                    Username
                    <input name="username" required autofocus>
                </label>
                <label>
                    Password
                    <input type="password" name="password" required>
                </label>
                <button class="button primary" type="submit">Login</button>
            </form>
        </section>
        """
        self.html(page("Login", body))

    def login(self):
        data = self.form_data()
        with get_db() as db:
            admin = db.execute("SELECT * FROM admins WHERE username = ?", (data.get("username"),)).fetchone()
            if not admin or not check_password(data.get("password", ""), admin["password_hash"]):
                self.show_login(["Invalid username or password."])
                return

            token = secrets.token_urlsafe(32)
            db.execute("INSERT INTO sessions (token, admin_id) VALUES (?, ?)", (token, admin["id"]))

        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie", f"session={token}; HttpOnly; SameSite=Lax; Path=/")
        self.end_headers()

    def logout(self):
        token = self.cookie_value("session")
        if token:
            with get_db() as db:
                db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self.send_response(303)
        self.send_header("Location", "/login")
        self.send_header("Set-Cookie", "session=; Max-Age=0; Path=/")
        self.end_headers()

    def create_employee(self, admin):
        data = self.form_data()
        errors = validate_employee(data)
        if errors:
            self.html(page("Add Employee", employee_form(data, errors), admin["username"]))
            return

        with get_db() as db:
            db.execute(
                """
                INSERT INTO employees (name, email, phone, department, role, salary, joining_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                clean_employee_values(data),
            )
        self.redirect("/")

    def edit_employee_form(self, path, admin):
        employee_id = employee_id_from_path(path)
        employee = find_employee(employee_id)
        if not employee:
            self.not_found()
            return
        self.html(page("Edit Employee", employee_form(dict(employee), heading="Edit Employee"), admin["username"]))

    def update_employee(self, path, admin):
        employee_id = employee_id_from_path(path)
        employee = find_employee(employee_id)
        if not employee:
            self.not_found()
            return

        data = self.form_data()
        data["id"] = employee_id
        errors = validate_employee(data, employee_id)
        if errors:
            self.html(page("Edit Employee", employee_form(data, errors, "Edit Employee"), admin["username"]))
            return

        with get_db() as db:
            db.execute(
                """
                UPDATE employees
                SET name = ?, email = ?, phone = ?, department = ?, role = ?, salary = ?, joining_date = ?
                WHERE id = ?
                """,
                clean_employee_values(data) + (employee_id,),
            )
        self.redirect("/")

    def delete_employee(self, path):
        employee_id = employee_id_from_path(path)
        with get_db() as db:
            db.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        self.redirect("/")

    def current_admin(self):
        token = self.cookie_value("session")
        if not token:
            return None
        with get_db() as db:
            return db.execute(
                """
                SELECT admins.* FROM admins
                JOIN sessions ON sessions.admin_id = admins.id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()

    def form_data(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        parsed = parse_qs(body)
        return {key: values[0].strip() for key, values in parsed.items()}

    def cookie_value(self, name):
        cookie_header = self.headers.get("Cookie", "")
        for item in cookie_header.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                if key == name:
                    return value
        return None

    def serve_static(self, filename, content_type):
        path = os.path.join(BASE_DIR, "static", filename)
        if not os.path.exists(path):
            self.not_found()
            return
        with open(path, "rb") as file:
            content = file.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(content)

    def html(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode())

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def not_found(self):
        self.html(page("Not Found", '<section class="panel"><h1>Page not found</h1></section>'), 404)

    def log_message(self, format, *args):
        return


def clean_employee_values(data):
    return (
        data["name"].strip(),
        data["email"].lower().strip(),
        data["phone"].strip(),
        data["department"].strip(),
        data["role"].strip(),
        float(data["salary"]),
        data["joining_date"].strip(),
    )


def find_employee(employee_id):
    with get_db() as db:
        return db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()


def employee_id_from_path(path):
    try:
        return int(path.split("/")[2])
    except (IndexError, ValueError):
        return 0


def render_employee_row(employee):
    return f"""
    <tr>
        <td>{escape(employee['name'])}</td>
        <td>{escape(employee['email'])}</td>
        <td>{escape(employee['phone'])}</td>
        <td>{escape(employee['department'])}</td>
        <td>{escape(employee['role'])}</td>
        <td>Rs. {employee['salary']:,.2f}</td>
        <td>{escape(employee['joining_date'])}</td>
        <td class="actions">
            <a class="button small" href="/employees/{employee['id']}/edit">Edit</a>
            <a class="button small danger" href="/employees/{employee['id']}/delete"
               onclick="return confirm('Delete this employee record?')">Delete</a>
        </td>
    </tr>
    """


if __name__ == "__main__":
    init_db()
    server = HTTPServer((HOST, PORT), EmployeeApp)
    print(f"Employee Management System running at http://{HOST}:{PORT}")
    print("Demo login: admin / admin123")
    server.serve_forever()
