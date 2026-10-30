"""
JOB PORTAL MANAGEMENT SYSTEM
Python Mini Project | Uses SQLite (built into Python)

How to run:
1. Save this file as job_portal.py
2. Open a terminal in the file's folder.
3. Run: python job_portal.py

The database file (job_portal.db) is created automatically.
Demo employer account:
    username: employer
    password: employer123
"""

import sqlite3
import hashlib
import os
from datetime import datetime

DB_NAME = "job_portal.db"


def hash_password(password):
    """Hash a password before storing it in the database."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password, stored_value):
    try:
        salt_hex, digest_hex = stored_value.split(":")
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return digest.hex() == digest_hex
    except (ValueError, TypeError):
        return False


def connect_db():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('jobseeker', 'employer'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                salary TEXT NOT NULL,
                job_type TEXT NOT NULL,
                description TEXT NOT NULL,
                posted_on TEXT NOT NULL,
                FOREIGN KEY(employer_id) REFERENCES users(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                applicant_id INTEGER NOT NULL,
                resume_link TEXT NOT NULL,
                cover_letter TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Submitted',
                applied_on TEXT NOT NULL,
                UNIQUE(job_id, applicant_id),
                FOREIGN KEY(job_id) REFERENCES jobs(id),
                FOREIGN KEY(applicant_id) REFERENCES users(id)
            )
        """)
        # Add a demo employer only when the database is first initialized.
        cur.execute("SELECT id FROM users WHERE username = ?", ("employer",))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO users (full_name, username, password_hash, role) VALUES (?, ?, ?, ?)",
                ("Demo Employer", "employer", hash_password("employer123"), "employer")
            )


def register():
    print("\n--- Create Account ---")
    name = input("Full name: ").strip()
    username = input("Choose username: ").strip()
    password = input("Choose password: ")
    role = input("Register as (1) Job Seeker or (2) Employer: ").strip()

    if not name or not username or not password:
        print("All fields are required.")
        return
    if role not in ("1", "2"):
        print("Please select 1 or 2.")
        return

    role_name = "jobseeker" if role == "1" else "employer"
    try:
        with connect_db() as conn:
            conn.execute(
                "INSERT INTO users (full_name, username, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, username, hash_password(password), role_name)
            )
        print("Account created successfully. You can now log in.")
    except sqlite3.IntegrityError:
        print("That username is already taken. Please choose another.")


def login():
    print("\n--- Login ---")
    username = input("Username: ").strip()
    password = input("Password: ")
    with connect_db() as conn:
        row = conn.execute(
            "SELECT id, full_name, username, password_hash, role FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if row and verify_password(password, row[3]):
        print(f"\nWelcome, {row[1]}!")
        return {"id": row[0], "name": row[1], "username": row[2], "role": row[4]}
    print("Invalid username or password.")
    return None


def list_jobs(search_term=None):
    with connect_db() as conn:
        if search_term:
            pattern = f"%{search_term}%"
            rows = conn.execute("""
                SELECT j.id, j.title, j.company, j.location, j.salary, j.job_type,
                       j.description, j.posted_on, u.full_name
                FROM jobs j JOIN users u ON j.employer_id = u.id
                WHERE j.title LIKE ? OR j.company LIKE ? OR j.location LIKE ?
                      OR j.description LIKE ?
                ORDER BY j.id DESC
            """, (pattern, pattern, pattern, pattern)).fetchall()
        else:
            rows = conn.execute("""
                SELECT j.id, j.title, j.company, j.location, j.salary, j.job_type,
                       j.description, j.posted_on, u.full_name
                FROM jobs j JOIN users u ON j.employer_id = u.id
                ORDER BY j.id DESC
            """).fetchall()

    if not rows:
        print("No jobs found.")
        return []

    print("\n" + "=" * 72)
    print("AVAILABLE JOBS")
    print("=" * 72)
    for job in rows:
        print(f"\nJob ID: {job[0]} | {job[1]} at {job[2]}")
        print(f"Location: {job[3]} | Salary: {job[4]} | Type: {job[5]}")
        print(f"Posted: {job[7]} | Employer: {job[8]}")
        print(f"Description: {job[6]}")
        print("-" * 72)
    return rows


def search_jobs():
    term = input("Enter job title, company, location, or keyword: ").strip()
    if term:
        list_jobs(term)
    else:
        print("Please enter a search term.")


def post_job(user):
    print("\n--- Post a Job ---")
    title = input("Job title: ").strip()
    company = input("Company name: ").strip()
    location = input("Location (or Remote): ").strip()
    salary = input("Salary range: ").strip()
    job_type = input("Job type (Full-time/Part-time/Internship/Remote): ").strip()
    description = input("Job description and requirements: ").strip()

    if not all([title, company, location, salary, job_type, description]):
        print("All fields are required.")
        return

    with connect_db() as conn:
        conn.execute("""
            INSERT INTO jobs
            (employer_id, title, company, location, salary, job_type, description, posted_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user["id"], title, company, location, salary, job_type, description,
              datetime.now().strftime("%Y-%m-%d")))
    print("Job posted successfully.")


def apply_for_job(user):
    list_jobs()
    try:
        job_id = int(input("\nEnter the Job ID you want to apply for: ").strip())
    except ValueError:
        print("Job ID must be a number.")
        return

    with connect_db() as conn:
        job = conn.execute("SELECT id, title FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        print("That job does not exist.")
        return

    resume_link = input("Resume file/link (e.g. resume.pdf or portfolio URL): ").strip()
    cover_letter = input("Short cover letter: ").strip()
    if not resume_link or not cover_letter:
        print("Resume reference and cover letter are required.")
        return

    try:
        with connect_db() as conn:
            conn.execute("""
                INSERT INTO applications
                (job_id, applicant_id, resume_link, cover_letter, status, applied_on)
                VALUES (?, ?, ?, ?, 'Submitted', ?)
            """, (job_id, user["id"], resume_link, cover_letter,
                  datetime.now().strftime("%Y-%m-%d")))
        print(f"Application submitted for: {job[1]}")
    except sqlite3.IntegrityError:
        print("You have already applied for this job.")


def view_my_applications(user):
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT a.id, j.title, j.company, a.status, a.applied_on
            FROM applications a JOIN jobs j ON a.job_id = j.id
            WHERE a.applicant_id = ? ORDER BY a.id DESC
        """, (user["id"],)).fetchall()
    print("\n--- My Applications ---")
    if not rows:
        print("You have not applied for any jobs yet.")
        return
    for row in rows:
        print(f"Application #{row[0]} | {row[1]} at {row[2]} | Status: {row[3]} | Date: {row[4]}")


def view_employer_jobs(user):
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT id, title, company, location, posted_on
            FROM jobs WHERE employer_id = ? ORDER BY id DESC
        """, (user["id"],)).fetchall()
    print("\n--- Jobs Posted by You ---")
    if not rows:
        print("You have not posted any jobs.")
        return
    for row in rows:
        print(f"Job ID: {row[0]} | {row[1]} at {row[2]} | {row[3]} | Posted: {row[4]}")


def view_applicants(user):
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT a.id, j.title, j.company, u.full_name, u.username,
                   a.resume_link, a.cover_letter, a.status, a.applied_on
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            JOIN users u ON a.applicant_id = u.id
            WHERE j.employer_id = ?
            ORDER BY a.id DESC
        """, (user["id"],)).fetchall()
    print("\n--- Applications for Your Jobs ---")
    if not rows:
        print("No applications received yet.")
        return
    for row in rows:
        print(f"\nApplication ID: {row[0]} | Job: {row[1]} at {row[2]}")
        print(f"Applicant: {row[3]} (@{row[4]})")
        print(f"Resume: {row[5]}")
        print(f"Cover letter: {row[6]}")
        print(f"Status: {row[7]} | Applied on: {row[8]}")
        print("-" * 60)


def update_application_status(user):
    view_applicants(user)
    try:
        app_id = int(input("\nEnter Application ID to update: ").strip())
    except ValueError:
        print("Application ID must be a number.")
        return

    print("1. Submitted  2. Under Review  3. Shortlisted  4. Rejected  5. Hired")
    choices = {
        "1": "Submitted", "2": "Under Review", "3": "Shortlisted",
        "4": "Rejected", "5": "Hired"
    }
    choice = input("Choose new status: ").strip()
    if choice not in choices:
        print("Invalid status choice.")
        return

    with connect_db() as conn:
        cur = conn.execute("""
            UPDATE applications SET status = ?
            WHERE id = ? AND job_id IN (SELECT id FROM jobs WHERE employer_id = ?)
        """, (choices[choice], app_id, user["id"]))
    if cur.rowcount:
        print("Application status updated.")
    else:
        print("Application not found under your posted jobs.")


def jobseeker_menu(user):
    while True:
        print("\n=== JOB SEEKER MENU ===")
        print("1. View all jobs")
        print("2. Search jobs")
        print("3. Apply for a job")
        print("4. View my applications")
        print("5. Logout")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            list_jobs()
        elif choice == "2":
            search_jobs()
        elif choice == "3":
            apply_for_job(user)
        elif choice == "4":
            view_my_applications(user)
        elif choice == "5":
            break
        else:
            print("Invalid option. Try again.")


def employer_menu(user):
    while True:
        print("\n=== EMPLOYER MENU ===")
        print("1. Post a job")
        print("2. View all jobs")
        print("3. View my posted jobs")
        print("4. View applicants")
        print("5. Update application status")
        print("6. Logout")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            post_job(user)
        elif choice == "2":
            list_jobs()
        elif choice == "3":
            view_employer_jobs(user)
        elif choice == "4":
            view_applicants(user)
        elif choice == "5":
            update_application_status(user)
        elif choice == "6":
            break
        else:
            print("Invalid option. Try again.")


def main():
    initialize_database()
    while True:
        print("\n" + "=" * 44)
        print("      JOB PORTAL MANAGEMENT SYSTEM")
        print("=" * 44)
        print("1. Register")
        print("2. Login")
        print("3. Browse jobs as guest")
        print("4. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            register()
        elif choice == "2":
            user = login()
            if user:
                if user["role"] == "jobseeker":
                    jobseeker_menu(user)
                else:
                    employer_menu(user)
        elif choice == "3":
            list_jobs()
        elif choice == "4":
            print("Thank you for using the Job Portal Management System.")
            break
        else:
            print("Invalid option. Please choose 1-4.")


if __name__ == "__main__":
    main()
