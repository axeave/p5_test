import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DATABASE = 'lines.db'  # データベース名を変更

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def close_db(conn):
    if conn:
        conn.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Initialize the database."""
    init_db()
    print('Initialized the database.')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/save_line', methods=['POST'])
def save_line():
    data = request.get_json()
    if not data or 'start_x' not in data or 'start_y' not in data or 'end_x' not in data or 'end_y' not in data:
        return jsonify({'error': 'Invalid data for line'}), 400

    start_x = data['start_x']
    start_y = data['start_y']
    end_x = data['end_x']
    end_y = data['end_y']

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO lines (start_x, start_y, end_x, end_y) VALUES (?, ?, ?, ?)", (start_x, start_y, end_x, end_y))
        conn.commit()
        close_db(conn)
        return jsonify({'message': 'Line data saved successfully'}), 201
    except sqlite3.Error as e:
        conn.rollback()
        close_db(conn)
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_lines', methods=['GET'])
def get_lines():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT start_x, start_y, end_x, end_y FROM lines")
    lines = cursor.fetchall()
    close_db(conn)
    return jsonify([dict(row) for row in lines])

if __name__ == '__main__':
    app.run(debug=True)