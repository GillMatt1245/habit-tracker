from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime, date

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# Detect if running on Vercel (production) or locally (development)
USE_POSTGRES = 'POSTGRES_URL' in os.environ

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    import sqlite3

# Database connection


def get_db_connection():
    if USE_POSTGRES:
        conn = psycopg2.connect(os.environ.get('POSTGRES_URL'))
        return conn
    else:
        conn = sqlite3.connect('habit_tracker.db')
        conn.row_factory = sqlite3.Row
        return conn

# Helper function for safe day name calculation


def get_day_name(year, month, day):
    """Safely get day name, return empty string if invalid date"""
    try:
        date_obj = date(year, month, day)
        return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][date_obj.weekday()]
    except ValueError:
        return ''

# Initialize database tables


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        # Months table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS months (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                best_day INTEGER,
                UNIQUE(year, month)
            )
        ''')

        # Habits table (5 habits per month)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS habits (
                id SERIAL PRIMARY KEY,
                month_id INTEGER REFERENCES months(id) ON DELETE CASCADE,
                habit_number INTEGER NOT NULL,
                habit_name TEXT,
                UNIQUE(month_id, habit_number)
            )
        ''')

        # Daily entries table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS daily_entries (
                id SERIAL PRIMARY KEY,
                month_id INTEGER REFERENCES months(id) ON DELETE CASCADE,
                day INTEGER NOT NULL,
                one_liner TEXT,
                detailed_journal TEXT,
                word_count INTEGER DEFAULT 0,
                habit1 INTEGER DEFAULT 0,
                habit2 INTEGER DEFAULT 0,
                habit3 INTEGER DEFAULT 0,
                habit4 INTEGER DEFAULT 0,
                habit5 INTEGER DEFAULT 0,
                UNIQUE(month_id, day),
                FOREIGN KEY (month_id) REFERENCES months(id) ON DELETE CASCADE
            )
        ''')
    else:
        # SQLite version
        cur.execute('''
            CREATE TABLE IF NOT EXISTS months (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                best_day INTEGER,
                UNIQUE(year, month)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_id INTEGER,
                habit_number INTEGER NOT NULL,
                habit_name TEXT,
                UNIQUE(month_id, habit_number),
                FOREIGN KEY (month_id) REFERENCES months(id) ON DELETE CASCADE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS daily_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_id INTEGER,
                day INTEGER NOT NULL,
                one_liner TEXT,
                detailed_journal TEXT,
                word_count INTEGER DEFAULT 0,
                habit1 INTEGER DEFAULT 0,
                habit2 INTEGER DEFAULT 0,
                habit3 INTEGER DEFAULT 0,
                habit4 INTEGER DEFAULT 0,
                habit5 INTEGER DEFAULT 0,
                UNIQUE(month_id, day),
                FOREIGN KEY (month_id) REFERENCES months(id) ON DELETE CASCADE
            )
        ''')

    conn.commit()
    conn.close()

# Get or create month


def get_or_create_month(year, month):
    conn = get_db_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute(
            'SELECT * FROM months WHERE year = %s AND month = %s', (year, month))
        month_record = cur.fetchone()

        if not month_record:
            cur.execute(
                'INSERT INTO months (year, month) VALUES (%s, %s) RETURNING id', (year, month))
            month_id = cur.fetchone()[0]

            for i in range(1, 6):
                cur.execute('INSERT INTO habits (month_id, habit_number, habit_name) VALUES (%s, %s, %s)',
                            (month_id, i, f'Habit {i}'))

            for day in range(1, 32):
                cur.execute(
                    'INSERT INTO daily_entries (month_id, day) VALUES (%s, %s)', (month_id, day))
        else:
            month_id = month_record[0]
    else:
        cur.execute(
            'SELECT * FROM months WHERE year = ? AND month = ?', (year, month))
        month_record = cur.fetchone()

        if not month_record:
            cur.execute(
                'INSERT INTO months (year, month) VALUES (?, ?)', (year, month))
            month_id = cur.lastrowid

            for i in range(1, 6):
                cur.execute('INSERT INTO habits (month_id, habit_number, habit_name) VALUES (?, ?, ?)',
                            (month_id, i, f'Habit {i}'))

            for day in range(1, 32):
                cur.execute(
                    'INSERT INTO daily_entries (month_id, day) VALUES (?, ?)', (month_id, day))
        else:
            month_id = month_record['id']

    conn.commit()
    conn.close()
    return month_id

# Get month data


def get_month_data(year, month):
    month_id = get_or_create_month(year, month)
    conn = get_db_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute('SELECT * FROM months WHERE id = %s', (month_id,))
        month_info = cur.fetchone()

        cur.execute(
            'SELECT * FROM habits WHERE month_id = %s ORDER BY habit_number', (month_id,))
        habits = cur.fetchall()

        cur.execute(
            'SELECT * FROM daily_entries WHERE month_id = %s ORDER BY day', (month_id,))
        entries = cur.fetchall()

        month_dict = dict(
            zip([desc[0] for desc in cur.description], month_info)) if month_info else {}
        habits_list = [
            dict(zip([desc[0] for desc in cur.description], h)) for h in habits]
        entries_list = [
            dict(zip([desc[0] for desc in cur.description], e)) for e in entries]
    else:
        cur.execute('SELECT * FROM months WHERE id = ?', (month_id,))
        month_info = cur.fetchone()

        cur.execute(
            'SELECT * FROM habits WHERE month_id = ? ORDER BY habit_number', (month_id,))
        habits = cur.fetchall()

        cur.execute(
            'SELECT * FROM daily_entries WHERE month_id = ? ORDER BY day', (month_id,))
        entries = cur.fetchall()

        month_dict = dict(month_info) if month_info else {}
        habits_list = [dict(h) for h in habits]
        entries_list = [dict(e) for e in entries]

    conn.close()

    return {
        'month_info': month_dict,
        'habits': habits_list,
        'entries': entries_list
    }


@app.route('/')
def index():
    init_db()

    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)

    data = get_month_data(year, month)

    # Add day names to entries
    for entry in data['entries']:
        entry['day_name'] = get_day_name(year, month, entry['day'])

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    return render_template('index.html',
                           current_year=year,
                           current_month=month,
                           month_data=data,
                           today=date.today(),
                           next_year=next_year,
                           next_month=next_month,
                           prev_year=prev_year,
                           prev_month=prev_month)


@app.route('/journal/<int:year>/<int:month>/<int:day>')
def journal_page(year, month, day):
    month_id = get_or_create_month(year, month)
    conn = get_db_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute(
            'SELECT * FROM daily_entries WHERE month_id = %s AND day = %s', (month_id, day))
        entry = cur.fetchone()
        entry_dict = dict(
            zip([desc[0] for desc in cur.description], entry)) if entry else {}
    else:
        cur.execute(
            'SELECT * FROM daily_entries WHERE month_id = ? AND day = ?', (month_id, day))
        entry = cur.fetchone()
        entry_dict = dict(entry) if entry else {}

    conn.close()

    return render_template('journal.html',
                           year=year,
                           month=month,
                           day=day,
                           entry=entry_dict)

# API: Save one-liner


@app.route('/api/save-oneliner', methods=['POST'])
def save_oneliner():
    data = request.json
    month_id = get_or_create_month(data['year'], data['month'])

    conn = get_db_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute('UPDATE daily_entries SET one_liner = %s WHERE month_id = %s AND day = %s',
                    (data['text'], month_id, data['day']))
    else:
        cur.execute('UPDATE daily_entries SET one_liner = ? WHERE month_id = ? AND day = ?',
                    (data['text'], month_id, data['day']))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

# API: Save habit check


@app.route('/api/save-habit', methods=['POST'])
def save_habit():
    data = request.json
    month_id = get_or_create_month(data['year'], data['month'])
    habit_col = f"habit{data['habit_number']}"

    conn = get_db_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute(f'UPDATE daily_entries SET {habit_col} = %s WHERE month_id = %s AND day = %s',
                    (1 if data['checked'] else 0, month_id, data['day']))
    else:
        cur.execute(f'UPDATE daily_entries SET {habit_col} = ? WHERE month_id = ? AND day = ?',
                    (1 if data['checked'] else 0, month_id, data['day']))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

# API: Save detailed journal


@app.route('/api/save-journal', methods=['POST'])
def save_journal():
    data = request.json
    month_id = get_or_create_month(data['year'], data['month'])
    text = data['text']
    word_count = len(text.split()) if text else 0

    conn = get_db_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute('UPDATE daily_entries SET detailed_journal = %s, word_count = %s WHERE month_id = %s AND day = %s',
                    (text, word_count, month_id, data['day']))
    else:
        cur.execute('UPDATE daily_entries SET detailed_journal = ?, word_count = ? WHERE month_id = ? AND day = ?',
                    (text, word_count, month_id, data['day']))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success', 'word_count': word_count})

# API: Update habit name


@app.route('/api/update-habit-name', methods=['POST'])
def update_habit_name():
    data = request.json
    month_id = get_or_create_month(data['year'], data['month'])

    conn = get_db_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute('UPDATE habits SET habit_name = %s WHERE month_id = %s AND habit_number = %s',
                    (data['name'], month_id, data['habit_number']))
    else:
        cur.execute('UPDATE habits SET habit_name = ? WHERE month_id = ? AND habit_number = ?',
                    (data['name'], month_id, data['habit_number']))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

# API: Save best day


@app.route('/api/save-best-day', methods=['POST'])
def save_best_day():
    data = request.json
    month_id = get_or_create_month(data['year'], data['month'])

    conn = get_db_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute('UPDATE months SET best_day = %s WHERE id = %s',
                    (data['best_day'], month_id))
    else:
        cur.execute('UPDATE months SET best_day = ? WHERE id = ?',
                    (data['best_day'], month_id))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})


if __name__ == '__main__':
    app.run(debug=True)
