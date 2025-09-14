from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error
import os

# --- Database Configuration ---
# Make sure this password is correct
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "mysystem",  # Replace with your actual password
    "database": "darpan_db"
}

app = FastAPI()


def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None


# --- Pydantic Models for Request Bodies ---
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    fullName: str
    email: str
    password: str


class SummaryRequest(BaseModel):
    data: dict


# --- NEW REGISTRATION ENDPOINT ---
@app.post("/api/register")
def register_user(request: RegisterRequest):
    """
    Creates a new citizen user account.
    """
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)

    # 1. Check if user already exists
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (request.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
    except Error as e:
        print(f"Database query error: {e}")
        raise HTTPException(status_code=500, detail="Error checking user existence")

    # 2. Insert new user
    # In a real app, hash the password before storing! e.g., using passlib
    dummy_hash = "hashed_" + request.password
    insert_query = """
        INSERT INTO users (full_name, email, password_hash, role) 
        VALUES (%s, %s, %s, 'citizen')
    """
    try:
        cursor.execute(insert_query, (request.fullName, request.email, dummy_hash))
        conn.commit()
    except Error as e:
        conn.rollback()
        print(f"Database insert error: {e}")
        raise HTTPException(status_code=500, detail="Could not create user account.")
    finally:
        cursor.close()
        conn.close()

    return {"success": True, "message": "Account created successfully. Please log in."}


# --- Existing Login Endpoint (No changes) ---
@app.post("/api/login")
def login_user(request: LoginRequest):
    conn = get_db_connection()
    if conn is None: raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, email, role, full_name FROM users WHERE email = %s"
    try:
        cursor.execute(query, (request.email,))
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    if user:
        return {"success": True, "user": user}
    else:
        raise HTTPException(status_code=401, detail="Invalid email or password")


# --- Other Existing Endpoints (No changes) ---
@app.get("/api/applications/{user_id}")
def get_user_applications(user_id: int):
    conn = get_db_connection()
    if conn is None: raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT a.id, s.name as serviceName, a.status, a.submitted_on, a.last_update, u_official.full_name as currentOfficial
        FROM applications a
        LEFT JOIN services s ON a.service_id = s.id
        LEFT JOIN users u_official ON a.current_official_id = u_official.id
        WHERE a.user_id = %s
    """
    try:
        cursor.execute(query, (user_id,))
        applications = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return {"applications": applications}


@app.post("/api/generate-summary")
def generate_summary(request: SummaryRequest):
    prompt = f"Generate an executive summary based on this data: {request.data}"
    summary = f"AI Summary for your data: {prompt}"
    return {"summary": summary}


@app.get("/")
def read_root():
    return {"message": "Welcome to the Project Darpan Backend API"}

