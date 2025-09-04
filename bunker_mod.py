import math
import re
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def gradeMap(grade):
    grade_map = {
        "O": 10, "A+": 9, "A": 8, "B+": 7, 
        "B": 6, "C": 5, "RA": 0, "SA": 0, "W": 0
    }
    return grade_map.get(grade.strip().upper(), 0)

class TimeTableModel:
    """Model for storing course information with titles"""
    def __init__(self, course_code, course_title, programme="", sem_no=""):
        self.course_code = course_code
        self.course_title = course_title
        self.programme = programme
        self.sem_no = sem_no

def return_attendance(username, pwd):
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Login to PSG eCampus
        login_url = "https://ecampus.psgtech.ac.in/studzone2/"
        r = session.get(login_url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')

        viewstate = soup.select("#__VIEWSTATE")[0]["value"]
        eventvalidation = soup.select("#__EVENTVALIDATION")[0]["value"]
        viewstategen = soup.select("#__VIEWSTATEGENERATOR")[0]["value"]

        payload = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategen,
            "__EVENTVALIDATION": eventvalidation,
            "txtusercheck": username,
            "txtpwdcheck": pwd,
            "abcd3": "Login"
        }

        session.post(login_url, data=payload, headers=headers)

        # Get attendance data
        attendance_url = "https://ecampus.psgtech.ac.in/studzone2/AttWfPercView.aspx"
        page = session.get(attendance_url, headers=headers)
        soup = BeautifulSoup(page.text, 'html.parser')

        table = soup.find("table", {"class": "cssbody"})
        if not table:
            return "Attendance data not available or invalid credentials"

        data = []
        for row in table.find_all("tr"):
            cols = [ele.text.strip() for ele in row.find_all("td")]
            data.append([ele for ele in cols if ele])

        return data, session

    except Exception as e:
        logger.error(f"Error in return_attendance: {str(e)}")
        return f"Error: {str(e)}"

def fetch_time_table(session):
    """Fetch course titles from timetable page"""
    try:
        time_table_url = "https://ecampus.psgtech.ac.in/studzone2/AttWfStudTimtab.aspx"
        page = session.get(time_table_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        table = soup.find("table", attrs={"id": "TbCourDesc"})
        if table is None:
            return {}

        data = []
        rows = table.find_all("tr")
        for index, row in enumerate(rows):
            cols = row.find_all("td")
            cols = [ele.text.strip() for ele in cols]
            data.append([ele for ele in cols if ele])

        # Create course code to title mapping
        course_map = {}
        for i in range(1, len(data)):
            if len(data[i]) >= 2:
                course_code = data[i][0]
                course_title = data[i][1]
                course_map[course_code] = course_title

        return course_map

    except Exception as e:
        logger.error(f"Error fetching timetable: {e}")
        return {}

def get_course_plan(session):
    """Course plan fetching with multiple strategies"""
    try:
        # Strategy 1: Try the courseplan URL
        courseplan_url = "https://ecampus.psgtech.ac.in/studzone/Attendance/courseplan"
        page = session.get(courseplan_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        courses = {}
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue

            for i, row in enumerate(rows):
                if i == 0:  # Skip header
                    continue

                cols = row.find_all(["td", "th"])
                if len(cols) >= 2:
                    course_code = cols[0].text.strip()
                    course_name = cols[1].text.strip()

                    if course_code and course_name and len(course_code) > 0 and len(course_name) > 2:
                        course_code = re.sub(r'\s+', ' ', course_code).strip()
                        course_name = re.sub(r'\s+', ' ', course_name).strip()

                        key = course_code.upper()
                        courses[key] = {
                            'name': course_name,
                            'code': course_code
                        }

        # Strategy 2: Fallback to timetable if courseplan fails
        if not courses:
            timetable_map = fetch_time_table(session)
            for code, title in timetable_map.items():
                courses[code.upper()] = {
                    'name': title,
                    'code': code
                }

        logger.info(f"Fetched {len(courses)} courses")
        return courses

    except Exception as e:
        logger.error(f"Error fetching course plan: {e}")
        # Final fallback to timetable
        try:
            return fetch_time_table(session)
        except:
            return {}

def find_course_name(subject_text, course_map):
    """Course name matching with multiple strategies"""
    if not course_map:
        return subject_text

    original = subject_text.strip()

    # Strategy 1: Direct lookup
    if original.upper() in course_map:
        return course_map[original.upper()].get('name', original) if isinstance(course_map[original.upper()], dict) else course_map[original.upper()]

    # Strategy 2: Extract course code patterns
    code_patterns = re.findall(r'[A-Z]{2,3}\d{4}', original.upper())
    for pattern in code_patterns:
        if pattern in course_map:
            return course_map[pattern].get('name', original) if isinstance(course_map[pattern], dict) else course_map[pattern]

    # Strategy 3: Look for any alphanumeric code
    code_clean = re.sub(r'[^A-Z0-9]', '', original.upper())
    if code_clean in course_map:
        return course_map[code_clean].get('name', original) if isinstance(course_map[code_clean], dict) else course_map[code_clean]

    # Strategy 4: Partial matching
    for code, course_info in course_map.items():
        course_name = course_info.get('name', course_info) if isinstance(course_info, dict) else course_info
        if code in original.upper() or any(word in code for word in original.upper().split() if len(word) > 2):
            return course_name

    # Strategy 5: Reverse lookup
    original_words = set(original.upper().split())
    for code, course_info in course_map.items():
        course_name = course_info.get('name', course_info) if isinstance(course_info, dict) else course_info
        course_words = set(course_name.upper().split())
        if len(original_words.intersection(course_words)) >= min(2, len(original_words)):
            return course_name

    return original

def data_json(data, course_map=None):
    """Data processing with course titles"""
    response = []
    for item in data[1:]:
        if len(item) < 10:
            continue

        # Get course name from course map
        original_name = item[0]
        course_title = find_course_name(original_name, course_map) if course_map else original_name

        temp = {
            "name": course_title,  # Full course name/title
            "course_title": course_title,  # Explicit field for course title
            "course_code": original_name,  # Original course code
            "original_name": original_name,  # Keep original for reference
            "total_hours": int(item[1]),
            "exception_hour": int(item[2]),
            "total_present": int(item[4]),
            "percentage_of_attendance": float(item[5]),
            "attendance_from": item[8],
            "attendance_to": item[9],
            "type": "lab" if "lab" in original_name.lower() else "theory"
        }

        # Calculate attendance requirements
        total_eligible_hours = temp['total_hours'] + temp['exception_hour']
        required_for_75 = math.ceil(0.75 * total_eligible_hours)

        if temp['total_present'] < required_for_75:
            temp['classes_to_attend'] = required_for_75 - temp['total_present']
            temp['classes_to_bunk'] = 0
            temp['status'] = 'must_attend'
        else:
            max_absent = math.floor(0.25 * total_eligible_hours)
            current_absent = total_eligible_hours - temp['total_present']
            temp['classes_to_bunk'] = max(0, max_absent - current_absent)
            temp['classes_to_attend'] = 0
            temp['status'] = 'can_bunk'

        temp['required_percentage'] = 75
        temp['shortage'] = max(0, required_for_75 - temp['total_present'])

        response.append(temp)
    return response

def return_cgpa(session):
    try:
        results_url = "https://ecampus.psgtech.ac.in/studzone2/FrmEpsStudResult.aspx"
        page = session.get(results_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        table = soup.find("table", {"id": "DgResult"})
        if not table:
            return {"error": "No results found"}

        data = []
        semester_data = {}

        for row in table.find_all("tr")[1:]:
            cols = [ele.text.strip() for ele in row.find_all("td")]
            if len(cols) >= 6:
                try:
                    credits = int(cols[3]) if cols[3].isdigit() else 0
                    semester = cols[0].strip()
                    grade = cols[4].split()[-1] if cols[4] else ""

                    course_data = {
                        "semester": semester,
                        "code": cols[1],
                        "title": cols[2],
                        "credits": credits,
                        "grade": grade,
                        "result": cols[5]
                    }
                    data.append(course_data)

                    if semester not in semester_data:
                        semester_data[semester] = []
                    semester_data[semester].append(course_data)

                except (ValueError, IndexError):
                    continue

        if not data:
            return {"error": "No valid course data found"}

        # Calculate CGPA
        total_points = 0
        total_credits = 0
        latest_sem = ""

        semester_numbers = []
        for semester in semester_data.keys():
            try:
                sem_num = convert_semester_to_number(semester)
                semester_numbers.append((sem_num, semester))
            except:
                semester_numbers.append((0, semester))

        if semester_numbers:
            semester_numbers.sort(reverse=True, key=lambda x: x[0])
            latest_sem = semester_numbers[0][1]

        for course in data:
            if (course["credits"] > 0 and 
                course["grade"] in ["O", "A+", "A", "B+", "B", "C+", "C"]):
                total_points += course["credits"] * gradeMap(course["grade"])
                total_credits += course["credits"]

        overall_cgpa = total_points / total_credits if total_credits > 0 else 0

        return {
            "latest_sem": latest_sem,
            "total_cgpa": round(overall_cgpa, 3),
            "total_semesters": len(semester_data),
            "courses": data
        }

    except Exception as e:
        logger.error(f"Error in return_cgpa: {str(e)}")
        return {"error": str(e)}

def convert_semester_to_number(semester):
    semester = semester.strip().upper()
    roman_map = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8,
        "IX": 9, "X": 10, "XI": 11, "XII": 12
    }

    if semester in roman_map:
        return roman_map[semester]

    numbers = re.findall(r'\d+', semester)
    if numbers:
        return int(numbers[0])

    return 0
