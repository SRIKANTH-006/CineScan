from flask import Flask, render_template, request, jsonify, g
import sqlite3, os

# --- Paths and setup ---
HERE = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(HERE, 'tickets.db')

app = Flask(__name__, static_folder='static', template_folder='templates')


# --- Database connection helpers ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/admin')
def admin():
    return render_template('admin.html')


@app.route('/api/tickets')
def tickets():
    rows = get_db().execute(
        'SELECT ticket_id, holder_name, used FROM tickets ORDER BY id'
    ).fetchall()
    return jsonify({
        'tickets': [
            {'ticket_id': r['ticket_id'], 'holder_name': r['holder_name'], 'used': bool(r['used'])}
            for r in rows
        ]
    })


@app.route('/api/ticket/<ticket_id>')
def ticket(ticket_id):
    r = get_db().execute(
        'SELECT ticket_id, holder_name, used FROM tickets WHERE ticket_id=?', (ticket_id,)
    ).fetchone()
    if r:
        return jsonify({
            'found': True,
            'ticket_id': r['ticket_id'],
            'holder_name': r['holder_name'],
            'used': bool(r['used'])
        })
    return jsonify({'found': False}), 404


@app.route('/api/mark_used', methods=['POST'])
def mark_used():
    data = request.get_json() or {}
    ticket_id = data.get('ticket_id')
    if not ticket_id:
        return jsonify({'ok': False, 'error': 'ticket_id required'}), 400

    cur = get_db().cursor()
    cur.execute('SELECT used FROM tickets WHERE ticket_id=?', (ticket_id,))
    r = cur.fetchone()

    if not r:
        return jsonify({'ok': False, 'error': 'not found'}), 404
    if r['used']:
        return jsonify({'ok': False, 'error': 'already used'}), 409

    cur.execute('UPDATE tickets SET used=1 WHERE ticket_id=?', (ticket_id,))
    get_db().commit()
    return jsonify({'ok': True, 'ticket_id': ticket_id})


# --- App entry point ---
if __name__ == '__main__':
    # Initialize DB if missing
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE,
                holder_name TEXT,
                used INTEGER DEFAULT 0
            )
        ''')
        sample = [
            ('TICKET-1001', 'Amit Sharma', 0),
            ('TICKET-1002', 'Neha Verma', 0),
            ('TICKET-1003', 'Ravi Kumar', 1),
            ('TICKET-1004', 'Priya Singh', 0)
        ]
        c.executemany('INSERT INTO tickets (ticket_id, holder_name, used) VALUES (?,?,?)', sample)
        conn.commit()
        conn.close()

    # Dynamic port for Render or local run
    port = int(os.environ.get('PORT', 8000))
    app.run(debug=True, host='0.0.0.0', port=port)
