import sqlite3
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit  # 追加

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # セッション管理に必要な設定
socketio = SocketIO(app)  # SocketIOインスタンスを作成
DATABASE = 'lines.db'

# --- データベース接続関連の関数 (変更なし) ---
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
        close_db(db) # データベースを閉じる処理を追加

@app.cli.command('initdb')
def initdb_command():
    """Initialize the database."""
    init_db()
    print('Initialized the database.')

# --- ルートとAPIエンドポイント ---

@app.route('/')
def index():
    """メインの描画ページを表示します。"""
    return render_template('index.html')

@app.route('/log')
def log_page():
    """スケッチのログページを表示します。"""
    return render_template('log.html') # 新しいHTMLファイル

@app.route('/screen')
def screen_page():
    """リアルタイム描画ページを表示します。"""
    return render_template('screen.html')  # 新しいHTMLファイル

@app.route('/api/create_sketch', methods=['POST'])
def create_sketch():
    """新しいスケッチを作成し、そのIDを返します。"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO sketches DEFAULT VALUES") # created_atは自動で入る
        conn.commit()
        sketch_id = cursor.lastrowid # 作成されたスケッチのIDを取得
        close_db(conn)
        return jsonify({'message': 'Sketch created successfully', 'sketch_id': sketch_id}), 201
    except sqlite3.Error as e:
        conn.rollback()
        close_db(conn)
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_lines', methods=['POST'])
def save_lines():
    """複数の線データを指定されたスケッチIDで保存し、WebSocketで通知します。"""
    data = request.get_json()
    if not data or 'sketch_id' not in data or 'lines' not in data or not isinstance(data['lines'], list):
        return jsonify({'error': 'Invalid data. sketch_id and a list of lines are required.'}), 400

    sketch_id = data['sketch_id']
    lines_data = data['lines']

    conn = get_db()
    cursor = conn.cursor()
    try:
        # まず、指定されたsketch_idが存在するか確認
        cursor.execute("SELECT id FROM sketches WHERE id = ?", (sketch_id,))
        sketch = cursor.fetchone()
        if not sketch:
            close_db(conn)
            return jsonify({'error': f'Sketch with id {sketch_id} not found.'}), 404

        for line in lines_data:
            if 'start_x' not in line or 'start_y' not in line or 'end_x' not in line or 'end_y' not in line:
                # 一つでも不正な線データがあればロールバックしてエラーを返す
                conn.rollback()
                close_db(conn)
                return jsonify({'error': 'Invalid line data found in the list.'}), 400
            cursor.execute(
                "INSERT INTO lines (sketch_id, start_x, start_y, end_x, end_y) VALUES (?, ?, ?, ?, ?)",
                (sketch_id, line['start_x'], line['start_y'], line['end_x'], line['end_y'])
            )
        conn.commit()

        # WebSocketでクライアントに通知 (sketch_idとlines_dataを送信)
        socketio.emit('new_sketch', {'sketch_id': sketch_id, 'lines': lines_data}, namespace='/screen')

        close_db(conn)
        return jsonify({'message': f'{len(lines_data)} lines saved successfully for sketch {sketch_id}'}), 201
    except sqlite3.Error as e:
        conn.rollback()
        close_db(conn)
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_sketches', methods=['GET'])
def get_sketches():
    """保存されている全てのスケッチのリストを取得します。"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, created_at FROM sketches ORDER BY created_at DESC")
        sketches = cursor.fetchall()
        close_db(conn)
        return jsonify([dict(row) for row in sketches])
    except sqlite3.Error as e:
        close_db(conn)
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_sketch_lines/<int:sketch_id>', methods=['GET'])
def get_sketch_lines(sketch_id):
    """指定されたsketch_idに紐づく全ての線データを取得します。"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 指定されたsketch_idが存在するか確認
        cursor.execute("SELECT id FROM sketches WHERE id = ?", (sketch_id,))
        sketch = cursor.fetchone()
        if not sketch:
            close_db(conn)
            return jsonify({'error': f'Sketch with id {sketch_id} not found.'}), 404

        cursor.execute("SELECT start_x, start_y, end_x, end_y FROM lines WHERE sketch_id = ?", (sketch_id,))
        lines = cursor.fetchall()
        close_db(conn)
        return jsonify([dict(row) for row in lines])
    except sqlite3.Error as e:
        close_db(conn)
        return jsonify({'error': str(e)}), 500

# WebSocketイベントハンドラ
@socketio.on('connect', namespace='/screen')
def test_connect():
    print('Client connected')

if __name__ == '__main__':
    # staticフォルダの場所を明示的に指定 (通常は自動で認識されますが、念のため)
    # app.static_folder = 'static'
    socketio.run(app, debug=True) # app.run() の代わりに socketio.run() を使用