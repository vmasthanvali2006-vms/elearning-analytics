
import getpass
import mysql.connector
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# 1. Connect Python to MySQL
password = getpass.getpass("Enter your MySQL password: ")

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=password,
    database="elearning_analytics"
)

print("MySQL connected successfully!")


# 2. Fetch course enrolment and completion data
query = """
SELECT
    c.course_id,
    c.course_name,
    e.enrollment_id,
    e.enrolled_at,
    e.status
FROM courses c
LEFT JOIN enrollments e
    ON c.course_id = e.course_id
"""

enrollments = pd.read_sql(query, conn)

# Cancelled enrolments are excluded from the report
eligible = enrollments[
    enrollments["status"].notna()
    & (enrollments["status"] != "cancelled")
].copy()

eligible["is_completed"] = (
    eligible["status"] == "completed"
).astype(int)


# 3. Calculate course completion rates
report = eligible.groupby(
    ["course_id", "course_name"],
    as_index=False
).agg(
    enrolments=("enrollment_id", "count"),
    completions=("is_completed", "sum")
)

report["completion_rate"] = np.divide(
    report["completions"] * 100,
    report["enrolments"],
    out=np.zeros(len(report), dtype=float),
    where=report["enrolments"].to_numpy() != 0
)

print("\nCOURSE COMPLETION REPORT")
print(report.to_string(index=False))

report.to_csv("course_completion_report.csv", index=False)


# 4. Fetch recorded learning activities
activity_query = """
SELECT
    a.activity_id,
    a.enrollment_id,
    a.activity_date,
    a.activity_type,
    a.completed,
    e.status,
    c.course_name
FROM activities a
JOIN enrollments e
    ON a.enrollment_id = e.enrollment_id
JOIN courses c
    ON e.course_id = c.course_id
WHERE e.status != 'cancelled'
"""

activities = pd.read_sql(activity_query, conn)

if not activities.empty:
    activities["activity_date"] = pd.to_datetime(
        activities["activity_date"]
    )

    # Summarize recorded activities by week
    activities["week"] = (
        activities["activity_date"]
        .dt.to_period("W")
        .astype(str)
    )

    weekly = activities.groupby(
        "week"
    ).size().reset_index(name="activity_count")

    print("\nWEEKLY ACTIVITY REPORT")
    print(weekly.to_string(index=False))

    weekly.to_csv("weekly_activity_report.csv", index=False)

    # Weekly activity chart
    plt.figure(figsize=(10, 5))
    plt.bar(weekly["week"], weekly["activity_count"])
    plt.title("Recorded Learning Activity by Week")
    plt.xlabel("Week")
    plt.ylabel("Number of Recorded Activities")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("weekly_activity.png")
    plt.show()

else:
    print("\nNo activity records available for analysis.")


# 5. Course enrolment and completion chart
plt.figure(figsize=(10, 5))

x = np.arange(len(report))
width = 0.35

plt.bar(
    x - width / 2,
    report["enrolments"],
    width,
    label="Enrolments"
)

plt.bar(
    x + width / 2,
    report["completions"],
    width,
    label="Completions"
)

plt.xticks(x, report["course_name"], rotation=25)
plt.ylabel("Number of Enrolments")
plt.title("Course Enrolment vs Completion")
plt.legend()
plt.tight_layout()
plt.savefig("course_comparison.png")
plt.show()


# 6. Identify inactive enrolments
# Rule: active enrolment, at least 14 days old,
# and no activity in the last 14 days.

inactive_query = """
SELECT
    e.enrollment_id,
    l.roll_no,
    c.course_name,
    e.enrolled_at,
    MAX(a.activity_date) AS last_activity
FROM enrollments e
JOIN learners l
    ON e.learner_id = l.learner_id
JOIN courses c
    ON e.course_id = c.course_id
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
"""

inactive = pd.read_sql(inactive_query, conn)

print("\nINACTIVE ENROLMENTS")
print(inactive.to_string(index=False))

inactive.to_csv("inactive_enrollments.csv", index=False)


# 7. Close database connection
conn.close()

print("\nAnalytics completed successfully!")
print("Reports and charts have been generated.")
