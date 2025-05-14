import sqlite3
from flask import Flask, render_template, request, jsonify
from collections import defaultdict

app = Flask(__name__)
DATABASE = 'lines.db'

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

@app.route('/api/save_lines', methods=['POST']) # エンドポイント名を複数形に変更 (save_line -> save_lines)
def save_lines():
    """複数の線データを指定されたスケッチIDで保存します。"""
    data = request.get_json()
    if not data or 'sketch_id' not in data or 'lines' not in data or not isinstance(data['lines'], list):
        return jsonify({'error': 'Invalid data. sketch_id and a list of lines are required.'}), 400

    sketch_id = data['sketch_id']
    lines_data = data['lines']

    conn = get_db()
    cursor = conn.cursor()
    try:
        # まず、指定されたsketch_idが存在するか確認 (任意ですが、より堅牢になります)
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


@app.route('/api/get_all_sketch_lines', methods=['GET'])
def get_all_sketch_lines():
    """保存されている全てのスケッチの線画データを取得し、各スケッチの開始点と終了点を返す。"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                l.start_x, l.start_y, l.end_x, l.end_y, 
                s.created_at, s.id as sketch_id,
                FIRST_VALUE(l.start_x) OVER (PARTITION BY s.id ORDER BY l.id ASC) as sketch_start_x,
                FIRST_VALUE(l.start_y) OVER (PARTITION BY s.id ORDER BY l.id ASC) as sketch_start_y,
                LAST_VALUE(l.end_x) OVER (PARTITION BY s.id ORDER BY l.id DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as sketch_end_x,
                LAST_VALUE(l.end_y) OVER (PARTITION BY s.id ORDER BY l.id DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as sketch_end_y
            FROM lines l
            JOIN sketches s ON l.sketch_id = s.id
            ORDER BY s.created_at, l.id
        """)
        lines = cursor.fetchall()
        close_db(conn)
        return jsonify([dict(row) for row in lines])
    except sqlite3.Error as e:
        close_db(conn)
        return jsonify({'error': str(e)}), 500


# 以前の /api/get_lines と /api/save_line は新しいエンドポイントに役割を譲るため削除またはコメントアウトします。
# もし古いAPIを何らかの理由で残したい場合はその旨お伝えください。
# 今回は、新しい機能に完全に移行するため、古いAPIは不要と判断します。

@app.route('/api/get_latest_sketch_id', methods=['GET'])
def get_latest_sketch_id():
    """最も新しいスケッチのIDを取得します。"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM sketches ORDER BY created_at DESC LIMIT 1")
        latest_sketch = cursor.fetchone()
        if latest_sketch:
            latest_id = latest_sketch['id']
            close_db(conn)
            return jsonify({'latest_sketch_id': latest_id}), 200
        else:
            close_db(conn)
            return jsonify({'latest_sketch_id': None}), 200
    except sqlite3.Error as e:
        close_db(conn)
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_surrounding_sketches/<int:center_sketch_id>', methods=['GET'])
def get_surrounding_sketches(center_sketch_id):
    """指定されたスケッチIDを中心とした前後のスケッチデータを取得します。"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                l.start_x, l.start_y, l.end_x, l.end_y, 
                s.created_at, s.id as sketch_id,
                FIRST_VALUE(l.start_x) OVER (PARTITION BY s.id ORDER BY l.id ASC) as sketch_start_x,
                FIRST_VALUE(l.start_y) OVER (PARTITION BY s.id ORDER BY l.id ASC) as sketch_start_y,
                LAST_VALUE(l.end_x) OVER (PARTITION BY s.id ORDER BY l.id DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as sketch_end_x,
                LAST_VALUE(l.end_y) OVER (PARTITION BY s.id ORDER BY l.id DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as sketch_end_y
            FROM lines l
            JOIN sketches s ON l.sketch_id = s.id
            WHERE s.created_at BETWEEN (
                SELECT datetime(created_at, '-5 seconds') FROM sketches WHERE id = ?
            ) AND (
                SELECT datetime(created_at, '+5 seconds') FROM sketches WHERE id = ?
            )
            ORDER BY s.created_at, l.id
        """, (center_sketch_id, center_sketch_id))  # 前後5秒の範囲で取得 (調整可能)
        lines = cursor.fetchall()
        close_db(conn)
        return jsonify([dict(row) for row in lines])
    except sqlite3.Error as e:
        close_db(conn)
        return jsonify({'error': str(e)}), 500



@app.route('/api/get_surrounding_sketch_lines/<int:sketch_id>', methods=['GET'])
def get_surrounding_sketch_lines(sketch_id):
    """
    指定されたsketch_idを中心とした前後5件のスケッチの線画データを取得し、Python側で処理します。
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        # まず、中心となるスケッチのcreated_atを取得
        cursor.execute("SELECT created_at FROM sketches WHERE id = ?", (sketch_id,))
        result = cursor.fetchone()
        if not result:
            close_db(conn)
            return jsonify({'error': f'Sketch with id {sketch_id} not found.'}), 404
        target_created_at = dict(result)['created_at']

        # 前後のスケッチIDを取得
        cursor.execute("""
            SELECT id FROM sketches 
            WHERE created_at <= ? ORDER BY created_at DESC LIMIT 6
        """, (target_created_at,))
        prev_sketch_ids = [row['id'] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT id FROM sketches 
            WHERE created_at > ? ORDER BY created_at ASC LIMIT 5
        """, (target_created_at,))
        next_sketch_ids = [row['id'] for row in cursor.fetchall()]

        all_sketch_ids = list(dict.fromkeys(prev_sketch_ids + next_sketch_ids))  # 重複を削除し、順序を保持

        # 全ての線データを取得
        cursor.execute("""
            SELECT l.*, s.created_at FROM lines l
            JOIN sketches s ON l.sketch_id = s.id
            WHERE l.sketch_id IN ({})
            ORDER BY s.created_at, l.id
        """.format(','.join('?' * len(all_sketch_ids))), all_sketch_ids)
        lines = [dict(row) for row in cursor.fetchall()]

        # 各スケッチの開始点と終了点を計算
        sketch_lines = defaultdict(list)
        for line in lines:
            sketch_lines[line['sketch_id']].append(line)

        processed_lines = []
        for sketch_id in all_sketch_ids:
            if sketch_id in sketch_lines:
                sketch_lines_for_id = sketch_lines[sketch_id]
                if sketch_lines_for_id:
                    first_line = sketch_lines_for_id[0]
                    last_line = sketch_lines_for_id[-1]
                    for line in sketch_lines_for_id:
                        line['sketch_start_x'] = first_line['start_x']
                        line['sketch_start_y'] = first_line['start_y']
                        line['sketch_end_x'] = last_line['end_x']
                        line['sketch_end_y'] = last_line['end_y']
                        processed_lines.append(line)

        close_db(conn)
        return jsonify(processed_lines)

    except sqlite3.Error as e:
        close_db(conn)
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    # staticフォルダの場所を明示的に指定 (通常は自動で認識されますが、念のため)
    # app.static_folder = 'static'
    app.run(debug=True)