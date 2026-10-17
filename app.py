
# from flask import Flask, render_template, jsonify, request
# import mysql.connector
# import getpass
# from datetime import datetime, date

# app = Flask(__name__)

# print("E-Learning Course Analytics System")
# DB_PASSWORD = getpass.getpass("Enter MySQL password: ")
import os
import time
from flask import Flask, render_template, jsonify, request
import mysql.connector
from datetime import datetime, date
from flask import g

app = Flask(__name__)

print("E-Learning Course Analytics System")


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

# def get_connection():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password=DB_PASSWORD,
#         database="elearning_analytics",
#         connection_timeout=5
#     )
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "elearning_analytics"),
        port=int(os.getenv("DB_PORT", "3306")),
        connection_timeout=5
    )
def get_db_connection():
    if "db_connection" not in g:
        g.db_connection = get_connection()
    return g.db_connection    


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def read_json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def required_text(data, field, max_length):
    value = data.get(field)

    if not isinstance(value, str) or not value.strip():
        return None, f"{field} is required"

    value = value.strip()

    if len(value) > max_length:
        return None, f"{field} must be {max_length} characters or fewer"

    return value, None


def optional_text(data, field, max_length):
    value = data.get(field)

    if value is None or value == "":
        return None, None

    if not isinstance(value, str):
        return None, f"{field} must be text"

    value = value.strip()

    if len(value) > max_length:
        return None, f"{field} must be {max_length} characters or fewer"

    return value or None, None


def positive_id(value):
    return type(value) is int and value > 0


def valid_boolean(value):
    return type(value) is bool




def run_query(sql, params=(), fetch=None, commit=False):
    conn = get_db_connection()
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        query_start = time.perf_counter()

        cursor.execute(sql, params)

        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        else:
            result = {
                "rowcount": cursor.rowcount,
                "lastrowid": cursor.lastrowid
            }
            if commit:
                conn.commit()

        query_time = time.perf_counter() - query_start

        print(
            f"DB timing | query_and_fetch={query_time:.3f}s",
            flush=True
        )

        return result

    except Exception:
        if commit:
            conn.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
            
@app.teardown_appcontext
def close_db_connection(exception=None):
    conn = g.pop("db_connection", None)

    if conn is not None:
        conn.close()


def database_error(message="Database operation failed"):
    app.logger.exception(message)
    return jsonify({"error": message}), 500


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/")
def dashboard():
    try:
        summary = run_query("""
            SELECT
                COUNT(*) AS total_enrollments,
                COALESCE(SUM(status = 'completed'), 0)
                    AS completed_enrollments,
                COALESCE(SUM(status = 'active'), 0)
                    AS active_enrollments
            FROM enrollments
            WHERE status != 'cancelled'
        """, fetch="one")

        total = summary["total_enrollments"] or 0
        completed = summary["completed_enrollments"] or 0

        summary["completion_rate"] = (
            round(completed * 100 / total, 2) if total else 0
        )

        courses = run_query("""
            SELECT
                c.course_id,
                c.course_name,
                COUNT(e.enrollment_id) AS enrollments,
                COALESCE(SUM(e.status = 'completed'), 0)
                    AS completions,
                ROUND(
                    100.0 * COALESCE(SUM(e.status = 'completed'), 0)
                    / NULLIF(COUNT(e.enrollment_id), 0),
                    2
                ) AS completion_rate
            FROM courses c
            LEFT JOIN enrollments e
                ON c.course_id = e.course_id
                AND e.status != 'cancelled'
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_name
        """, fetch="all")

        weekly = run_query("""
            SELECT
                DATE_FORMAT(
                    DATE(activity_date) -
                    INTERVAL WEEKDAY(activity_date) DAY,
                    '%Y-%m-%d'
                ) AS week_start,
                COUNT(*) AS activity_count
            FROM activities a
            JOIN enrollments e
                ON a.enrollment_id = e.enrollment_id
            WHERE e.status != 'cancelled'
            GROUP BY week_start
            ORDER BY week_start
        """, fetch="all")

        inactive = run_query("""
            SELECT
                e.enrollment_id,
                l.roll_no,
                c.course_name,
                e.enrolled_at,
                MAX(a.activity_date) AS last_activity
            FROM enrollments e
            JOIN learners l ON e.learner_id = l.learner_id
            JOIN courses c ON e.course_id = c.course_id
            LEFT JOIN activities a
                ON e.enrollment_id = a.enrollment_id
            WHERE e.status = 'active'
            GROUP BY
                e.enrollment_id,
                l.roll_no,
                c.course_name,
                e.enrolled_at
            HAVING
                e.enrolled_at <= NOW() - INTERVAL 14 DAY
                AND (
                    MAX(a.activity_date) IS NULL
                    OR MAX(a.activity_date) < NOW() - INTERVAL 14 DAY
                )
            ORDER BY e.enrolled_at
        """, fetch="all")

        return render_template(
            "index.html",
            summary=summary,
            courses=courses,
            weekly=weekly,
            inactive=inactive
        )

    except mysql.connector.Error:
        return database_error("Could not load dashboard. Check MySQL.")
    except Exception:
        return database_error("Could not load dashboard.")


@app.route("/health")
def health():
    try:
        run_query("SELECT 1", fetch="one")
        return jsonify({
            "status": "ok",
            "database": "connected"
        }), 200
    except mysql.connector.Error:
        return database_error("Database connection failed")


# ==================================================
# COURSES CRUD
# ==================================================

@app.route("/api/courses", methods=["GET"])
def get_courses():
    try:
        rows = run_query("""
            SELECT course_id, course_name, category
            FROM courses ORDER BY course_id
        """, fetch="all")
        return jsonify(rows), 200
    except mysql.connector.Error:
        return database_error("Could not retrieve courses")


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    try:
        course = run_query("""
            SELECT course_id, course_name, category
            FROM courses WHERE course_id = %s
        """, (course_id,), fetch="one")

        if course is None:
            return jsonify({"error": "Course not found"}), 404

        return jsonify(course), 200
    except mysql.connector.Error:
        return database_error("Could not retrieve course")


@app.route("/api/courses", methods=["POST"])
def add_course():
    data = read_json()

    if data is None:
        return jsonify({"error": "Send a JSON object"}), 400

    name, error = required_text(data, "course_name", 100)
    if error:
        return jsonify({"error": error}), 400

    category, error = optional_text(data, "category", 50)
    if error:
        return jsonify({"error": error}), 400

    try:
        result = run_query("""
            INSERT INTO courses (course_name, category)
            VALUES (%s, %s)
        """, (name, category), commit=True)

        return jsonify({
            "message": "Course added successfully",
            "course_id": result["lastrowid"]
        }), 201
    except mysql.connector.Error:
        return database_error("Could not add course")


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    data = read_json()

    if data is None:
        return jsonify({"error": "Send a JSON object"}), 400

    name, error = required_text(data, "course_name", 100)
    if error:
        return jsonify({"error": error}), 400

    category, error = optional_text(data, "category", 50)
    if error:
        return jsonify({"error": error}), 400

    try:
        existing = run_query(
            "SELECT course_id FROM courses WHERE course_id = %s",
            (course_id,), fetch="one"
        )

        if existing is None:
            return jsonify({"error": "Course not found"}), 404

        run_query("""
            UPDATE courses
            SET course_name = %s, category = %s
            WHERE course_id = %s
        """, (name, category, course_id), commit=True)

        return jsonify({"message": "Course updated successfully"}), 200
    except mysql.connector.Error:
        return database_error("Could not update course")


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    try:
        result = run_query(
            "DELETE FROM courses WHERE course_id = %s",
            (course_id,), commit=True
        )

        if result["rowcount"] == 0:
            return jsonify({"error": "Course not found"}), 404

        return jsonify({"message": "Course deleted successfully"}), 200

    except mysql.connector.IntegrityError:
        return jsonify({
            "error": "Cannot delete course because enrolments reference it"
        }), 409
    except mysql.connector.Error:
        return database_error("Could not delete course")


# ==================================================
# LEARNERS CRUD
# ==================================================

@app.route("/api/learners", methods=["GET"])
def get_learners():
    try:
        rows = run_query("""
            SELECT learner_id, roll_no
            FROM learners ORDER BY learner_id
        """, fetch="all")
        return jsonify(rows), 200
    except mysql.connector.Error:
        return database_error("Could not retrieve learners")


@app.route("/api/learners/<int:learner_id>", methods=["GET"])
def get_learner(learner_id):
    try:
        learner = run_query("""
            SELECT learner_id, roll_no
            FROM learners WHERE learner_id = %s
        """, (learner_id,), fetch="one")

        if learner is None:
            return jsonify({"error": "Learner not found"}), 404

        return jsonify(learner), 200
    except mysql.connector.Error:
        return database_error("Could not retrieve learner")


@app.route("/api/learners", methods=["POST"])
def add_learner():
    data = read_json()

    if data is None:
        return jsonify({"error": "Send a JSON object"}), 400

    roll_no, error = required_text(data, "roll_no", 30)
    if error:
        return jsonify({"error": error}), 400

    try:
        result = run_query("""
            INSERT INTO learners (roll_no) VALUES (%s)
        """, (roll_no,), commit=True)

        return jsonify({
            "message": "Learner added successfully",
            "learner_id": result["lastrowid"]
        }), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Roll number already exists"}), 409
    except mysql.connector.Error:
        return database_error("Could not add learner")


@app.route("/api/learners/<int:learner_id>", methods=["PUT"])
def update_learner(learner_id):
    data = read_json()

    if data is None:
        return jsonify({"error": "Send a JSON object"}), 400

    roll_no, error = required_text(data, "roll_no", 30)
    if error:
        return jsonify({"error": error}), 400

    try:
        existing = run_query(
            "SELECT learner_id FROM learners WHERE learner_id = %s",
            (learner_id,), fetch="one"
        )

        if existing is None:
            return jsonify({"error": "Learner not found"}), 404

        run_query("""
            UPDATE learners SET roll_no = %s
            WHERE learner_id = %s
        """, (roll_no, learner_id), commit=True)

        return jsonify({"message": "Learner updated successfully"}), 200
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Roll number already exists"}), 409
    except mysql.connector.Error:
        return database_error("Could not update learner")


@app.route("/api/learners/<int:learner_id>", methods=["DELETE"])
def delete_learner(learner_id):
    try:
        result = run_query(
            "DELETE FROM learners WHERE learner_id = %s",
            (learner_id,), commit=True
        )

        if result["rowcount"] == 0:
            return jsonify({"error": "Learner not found"}), 404

        return jsonify({"message": "Learner deleted successfully"}), 200

    except mysql.connector.IntegrityError:
        return jsonify({
            "error": "Cannot delete learner because enrolments reference them"
        }), 409
    except mysql.connector.Error:
        return database_error("Could not delete learner")


# ==================================================
# ENROLMENTS CRUD
# ==================================================

@app.route("/api/enrollments", methods=["GET"])
def get_enrollments():
    try:
        rows = run_query("""
            SELECT
                e.enrollment_id,
                e.learner_id,
                l.roll_no,
                e.course_id,
                c.course_name,
                e.enrolled_at,
                e.status
            FROM enrollments e
            JOIN learners l ON e.learner_id = l.learner_id
            JOIN courses c ON e.course_id = c.course_id
            ORDER BY e.enrollment_id
        """, fetch="all")
        return jsonify(rows), 200
    except mysql.connector.Error:
        return database_error("Could not retrieve enrolments")


@app.route("/api/enrollments/<int:enrollment_id>", methods=["GET"])
def get_enrollment(enrollment_id):
    try:
        row = run_query("""
            SELECT enrollment_id, learner_id, course_id,
                   enrolled_at, status
            FROM enrollments
            WHERE enrollment_id = %s
        """, (enrollment_id,), fetch="one")

        if row is None:
            return jsonify({"error": "Enrolment not found"}), 404

        return jsonify(row), 200
    except mysql.connector.Error:
        return database_error("Could not retrieve enrolment")


@app.route("/api/enrollments", methods=["POST"])
def add_enrollment():
    data = read_json()

    if data is None:
        return jsonify({"error": "Send a JSON object"}), 400

    learner_id = data.get("learner_id")
    course_id = data.get("course_id")
    status = data.get("status", "active")

    if not positive_id(learner_id) or not positive_id(course_id):
        return jsonify({
            "error": "learner_id and course_id must be positive integers"
        }), 400

    if status not in ("active", "completed", "cancelled"):
        return jsonify({"error": "Invalid enrolment status"}), 400

    try:
        result = run_query("""
            INSERT INTO enrollments (learner_id, course_id, status)
            VALUES (%s, %s, %s)
        """, (learner_id, course_id, status), commit=True)

        return jsonify({
            "message": "Enrolment added successfully",
            "enrollment_id": result["lastrowid"]
        }), 201
    except mysql.connector.IntegrityError:
        return jsonify({
            "error": "Learner or course does not exist"
        }), 400
    except mysql.connector.Error:
        return database_error("Could not add enrolment")


@app.route("/api/enrollments/<int:enrollment_id>", methods=["PUT"])
def update_enrollment(enrollment_id):
    data = read_json()

    if data is None:
        return jsonify({"error": "Send a JSON object"}), 400

    learner_id = data.get("learner_id")
    course_id = data.get("course_id")
    status = data.get("status")

    if not positive_id(learner_id) or not positive_id(course_id):
        return jsonify({
            "error": "learner_id and course_id must be positive integers"
        }), 400

    if status not in ("active", "completed", "cancelled"):
        return jsonify({"error": "Invalid enrolment status"}), 400

    try:
        existing = run_query("""
            SELECT enrollment_id FROM enrollments
            WHERE enrollment_id = %s
        """, (enrollment_id,), fetch="one")

        if existing is None:
            return jsonify({"error": "Enrolment not found"}), 404

        run_query("""
            UPDATE enrollments
            SET learner_id = %s, course_id = %s, status = %s
            WHERE enrollment_id = %s
        """, (learner_id, course_id, status, enrollment_id), commit=True)

        return jsonify({"message": "Enrolment updated successfully"}), 200
    except mysql.connector.IntegrityError:
        return jsonify({
            "error": "Learner or course does not exist"
        }), 400
    except mysql.connector.Error:
        return database_error("Could not update enrolment")


@app.route("/api/enrollments/<int:enrollment_id>", methods=["DELETE"])
def delete_enrollment(enrollment_id):
    try:
        result = run_query(
            "DELETE FROM enrollments WHERE enrollment_id = %s",
            (enrollment_id,), commit=True
        )

        if result["rowcount"] == 0:
            return jsonify({"error": "Enrolment not found"}), 404

        return jsonify({"message": "Enrolment deleted successfully"}), 200

    except mysql.connector.IntegrityError:
        return jsonify({
            "error": "Cannot delete enrolment because activity records reference it"
        }), 409
    except mysql.connector.Error:
        return database_error("Could not delete enrolment")


# ==================================================
# ACTIVITIES CRUD
# ==================================================

@app.route("/api/activities", methods=["GET"])
def get_activities():
    try:
        rows = run_query("""
            SELECT
                activity_id,
                enrollment_id,
                activity_date,
                activity_type,
                completed
            FROM activities
            ORDER BY activity_date DESC
        """, fetch="all")
        return jsonify(rows), 200
    except mysql.connector.Error:
        return database_error("Could not retrieve activities")


@app.route("/api/activities/<int:activity_id>", methods=["GET"])
def get_activity(activity_id):
    try:
        row = run_query("""
            SELECT activity_id, enrollment_id, activity_date,
                   activity_type, completed
            FROM activities
            WHERE activity_id = %s
        """, (activity_id,), fetch="one")

        if row is None:
            return jsonify({"error": "Activity not found"}), 404

        return jsonify(row), 200
    except mysql.connector.Error:
        return database_error("Could not retrieve activity")


@app.route("/api/activities", methods=["POST"])
def add_activity():
    data = read_json()

    if data is None:
        return jsonify({"error": "Send a JSON object"}), 400

    enrollment_id = data.get("enrollment_id")
    activity_type, error = required_text(data, "activity_type", 50)

    if not positive_id(enrollment_id):
        return jsonify({
            "error": "enrollment_id must be a positive integer"
        }), 400

    if error:
        return jsonify({"error": error}), 400

    completed = data.get("completed", False)

    if not valid_boolean(completed):
        return jsonify({"error": "completed must be true or false"}), 400

    activity_date = data.get("activity_date")

    if activity_date is not None:
        if not isinstance(activity_date, str):
            return jsonify({
                "error": "activity_date must be a date-time string"
            }), 400

        try:
            datetime.fromisoformat(activity_date)
        except ValueError:
            return jsonify({
                "error": "Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS for activity_date"
            }), 400

    try:
        if activity_date is None:
            result = run_query("""
                INSERT INTO activities
                    (enrollment_id, activity_type, completed)
                VALUES (%s, %s, %s)
            """, (enrollment_id, activity_type, completed), commit=True)
        else:
            result = run_query("""
                INSERT INTO activities
                    (enrollment_id, activity_date, activity_type, completed)
                VALUES (%s, %s, %s, %s)
            """, (
                enrollment_id, activity_date, activity_type, completed
            ), commit=True)

        return jsonify({
            "message": "Activity added successfully",
            "activity_id": result["lastrowid"]
        }), 201

    except mysql.connector.IntegrityError:
        return jsonify({"error": "Enrolment does not exist"}), 400
    except mysql.connector.Error:
        return database_error("Could not add activity")


@app.route("/api/activities/<int:activity_id>", methods=["PUT"])
def update_activity(activity_id):
    data = read_json()

    if data is None:
        return jsonify({"error": "Send a JSON object"}), 400

    enrollment_id = data.get("enrollment_id")
    activity_type, error = required_text(data, "activity_type", 50)

    if not positive_id(enrollment_id):
        return jsonify({
            "error": "enrollment_id must be a positive integer"
        }), 400

    if error:
        return jsonify({"error": error}), 400

    completed = data.get("completed")

    if not valid_boolean(completed):
        return jsonify({
            "error": "completed must be true or false"
        }), 400

    activity_date = data.get("activity_date")

    if not isinstance(activity_date, str):
        return jsonify({
            "error": "activity_date is required in YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format"
        }), 400

    try:
        datetime.fromisoformat(activity_date)
    except ValueError:
        return jsonify({"error": "Invalid activity_date format"}), 400

    try:
        existing = run_query("""
            SELECT activity_id FROM activities
            WHERE activity_id = %s
        """, (activity_id,), fetch="one")

        if existing is None:
            return jsonify({"error": "Activity not found"}), 404

        run_query("""
            UPDATE activities
            SET enrollment_id = %s,
                activity_date = %s,
                activity_type = %s,
                completed = %s
            WHERE activity_id = %s
        """, (
            enrollment_id, activity_date, activity_type,
            completed, activity_id
        ), commit=True)

        return jsonify({"message": "Activity updated successfully"}), 200

    except mysql.connector.IntegrityError:
        return jsonify({"error": "Enrolment does not exist"}), 400
    except mysql.connector.Error:
        return database_error("Could not update activity")


@app.route("/api/activities/<int:activity_id>", methods=["DELETE"])
def delete_activity(activity_id):
    try:
        result = run_query(
            "DELETE FROM activities WHERE activity_id = %s",
            (activity_id,), commit=True
        )

        if result["rowcount"] == 0:
            return jsonify({"error": "Activity not found"}), 404

        return jsonify({"message": "Activity deleted successfully"}), 200

    except mysql.connector.Error:
        return database_error("Could not delete activity")


# --------------------------------------------------
# START FLASK
# --------------------------------------------------

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
        use_reloader=False
    )
