# E-Learning Course Analytics System

## Project Overview
The E-Learning Course Analytics System is a Python and MySQL-based project that analyzes course enrolments, learner progress, activity completion, and weekly learning activity.

It generates reports and visualizations to help administrators understand course participation and completion trends.

## Features
- Manage courses, learners, enrolments, and learning activities.
- Track activity completion and enrolment status.
- Compare enrolments and completions across courses.
- Generate weekly activity summaries.
- Identify inactive enrolments using a defined rule.
- Export analytics reports to CSV.
- Generate charts for course comparisons and weekly activity.
- Provide a Flask web interface and API endpoints.

## Technologies Used
- Python
- Flask
- MySQL
- Pandas
- NumPy
- Matplotlib
- HTML and CSS
- Chart.js

## Project Structure
- `app.py` — Flask application and API routes
- `analytics.py` — Data analysis and report generation
- `database.sql` — Database schema and setup
- `templates/` — HTML templates
- `static/` — CSS, charts, and static assets
- `reports/` — Generated reports and charts
- `test_app.py` — Automated application tests
- `requirements.txt` — Python dependencies

## Setup Instructions

1. Clone or download this repository.
2. Create and activate a Python virtual environment.
3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create the MySQL database and tables using `database.sql`.
5. Start MySQL and run the Flask application:

   ```bash
   python3 app.py
   ```

6. Open `http://127.0.0.1:5001` in your browser if the application starts on port 5001.

The application asks for the MySQL password in the terminal when required.

## Run Tests

```bash
python3 -m unittest -v test_app
```

## Project Goal
To demonstrate database management, Python backend development, data analysis, report generation, and visualization using an e-learning analytics use case.