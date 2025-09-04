import os
import math
import re
import logging
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session as flask_session, send_from_directory, redirect
from bunker_mod import return_attendance, data_json, return_cgpa, get_course_plan

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'psg-bunker-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # Session expires after 2 hours

# Rate limiting setup (simple in-memory version)
from collections import defaultdict
from time import time
login_attempts = defaultdict(list)

def rate_limit(max_attempts=20, time_window=300):
    """Decorator to limit login attempts"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            now = time()
            
            # Clean old attempts
            login_attempts[ip] = [attempt for attempt in login_attempts[ip] if attempt > now - time_window]
            
            # Check if exceeded max attempts
            if len(login_attempts[ip]) >= max_attempts:
                logger.warning(f"Rate limit exceeded for IP: {ip}")
                if request.is_json:
                    return jsonify({"ok": False, "message": "Too many login attempts. Please try again later."}), 429
                else:
                    return render_template("index.html", error="Too many login attempts. Please try again later."), 429
            
            # Record this attempt
            login_attempts[ip].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def login_required(f):
    """Decorator to ensure user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'rollno' not in flask_session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
@rate_limit(max_attempts=5, time_window=300)  # 5 attempts per 5 minutes
def login():
    # Handle both form and JSON data
    if request.is_json:
        rollno = request.json.get('rollno', '').strip()
        password = request.json.get('password', '')
        remember_me = request.json.get('remember_me', False)
    else:
        rollno = request.form.get('rollno', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'

    if not rollno or not password:
        if request.is_json:
            return jsonify({"ok": False, "message": "Roll number and password are required"}), 400
        else:
            return render_template("index.html", error="Roll number and password are required"), 400

    # More flexible roll number validation (PSG format: YYDepartmentNumber)
    # Examples: 21IT066, 20MEC123, 19ADM01, etc.
    if not re.match(r'^\d{2}[A-Za-z]{1,4}\d{1,4}$', rollno):
        if request.is_json:
            return jsonify({"ok": False, "message": "Invalid roll number format."}), 400
        else:
            return render_template("index.html", error="Invalid roll number format."), 400

    try:
        result = return_attendance(rollno, password)
        
        if isinstance(result, str):
            if request.is_json:
                return jsonify({"ok": False, "message": result}), 401
            else:
                return render_template("index.html", error=result), 401

        attendance_raw, session_obj = result

        # Get real course plan data with course titles
        course_plan = get_course_plan(session_obj)

        # Process attendance data with real course names from courseplan
        attendance_data = data_json(attendance_raw, course_plan)
        cgpa_data = return_cgpa(session_obj)

        # Store data in Flask session for API endpoints
        flask_session['attendance_data'] = attendance_data
        flask_session['cgpa_data'] = cgpa_data
        flask_session['course_plan'] = course_plan
        flask_session['rollno'] = rollno
        
        # Set session permanence based on remember_me
        flask_session.permanent = remember_me

        if request.is_json:
            return jsonify({"ok": True, "message": "Login successful"})
        else:
            return render_template("dashboard.html",
                                 rollno=rollno,
                                 attendance=attendance_data,
                                 cgpa=cgpa_data)

    except Exception as e:
        logger.error(f"Login error for {rollno}: {str(e)}")
        if request.is_json:
            return jsonify({"ok": False, "message": "An internal error occurred. Please try again later."}), 500
        else:
            return render_template("index.html", error="An internal error occurred. Please try again later."), 500

@app.route('/attendance')
@login_required
def get_attendance():
    """API endpoint for attendance data with course titles"""
    try:
        attendance_data = flask_session.get('attendance_data', [])
        
        if not attendance_data:
            return jsonify({"error": "No attendance data available"}), 404

        # Calculate overall statistics
        total_hours = sum(subject['total_hours'] for subject in attendance_data)
        total_present = sum(subject['total_present'] for subject in attendance_data)
        overall_percentage = (total_present / total_hours * 100) if total_hours > 0 else 0

        # Calculate bunkable/need days for 75% threshold
        if overall_percentage < 75:
            need_days = math.ceil((0.75 * total_hours - total_present) / 0.25)
            bunkable_days = 0
        else:
            need_days = 0
            bunkable_days = int((total_present - 0.75 * total_hours) / 0.75)

        # Include course titles in response
        subjects_with_titles = []
        for subject in attendance_data:
            subject_with_title = subject.copy()
            subject_with_title['display_name'] = subject.get('course_title', 
                                                           subject.get('name', 
                                                                      subject.get('original_name', 'Unknown Course')))
            subjects_with_titles.append(subject_with_title)

        return jsonify({
            "subjects": subjects_with_titles,
            "total_days": total_hours,
            "attended_days": total_present,
            "percentage": overall_percentage,
            "need_days": need_days,
            "bunkable_days": bunkable_days
        })
    
    except Exception as e:
        logger.error(f"Error fetching attendance: {str(e)}")
        return jsonify({"error": "Failed to fetch attendance data"}), 500

@app.route('/cgpa')
@login_required
def get_cgpa():
    """API endpoint for CGPA data"""
    try:
        cgpa_data = flask_session.get('cgpa_data', {})
        return jsonify(cgpa_data)
    except Exception as e:
        logger.error(f"Error fetching CGPA: {str(e)}")
        return jsonify({"error": "Failed to fetch CGPA data"}), 500

@app.route('/courses')
@login_required
def get_courses():
    """API endpoint to get course mapping"""
    try:
        course_plan = flask_session.get('course_plan', {})
        return jsonify(course_plan)
    except Exception as e:
        logger.error(f"Error fetching courses: {str(e)}")
        return jsonify({"error": "Failed to fetch course data"}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page route with course titles"""
    try:
        return render_template("dashboard.html",
                             rollno=flask_session['rollno'],
                             attendance=flask_session.get('attendance_data', []),
                             cgpa=flask_session.get('cgpa_data', {}))
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return redirect('/')

@app.route('/logout')
def logout():
    """Clear session and logout user"""
    flask_session.clear()
    return redirect('/')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(429)
def too_many_requests(e):
    return render_template('429.html'), 429

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "PSG Bunker is running"})

if __name__ == '__main__':
    # Use environment variable for debug mode
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)


