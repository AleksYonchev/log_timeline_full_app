from flask import Flask, request, jsonify, send_from_directory, session, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import os
from datetime import datetime
from pytz import timezone
import re

app = Flask(__name__)
app.secret_key = 'very_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timeline.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
CORS(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    timelines = db.relationship('Timeline', backref='user', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)

class Timeline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone('Europe/Sofia')))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    events = db.relationship('Event', backref='timeline', lazy=True)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(32))
    timestamp = db.Column(db.String(64))
    title = db.Column(db.String(128))
    description = db.Column(db.String(256))
    datetime_iso = db.Column(db.String(64))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    timeline_id = db.Column(db.Integer, db.ForeignKey('timeline.id'), nullable=False)

@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def home():
    logged_in = 'user_id' in session
    return render_template('index.html', logged_in=logged_in)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return 'Username already exists'
        if User.query.filter_by(email=email).first():
            return 'Email already registered'
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        return render_template('login.html', error='Невалидно име или парола')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        print("⚠️ Няма подаден файл")
        return jsonify({'error': 'Няма подаден файл'}), 400

    file = request.files['file']
    print("🚀 Получен файл:", file.filename)
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    user_id = session.get('user_id')
    lines = file.read().decode('utf-8').splitlines()
    lines = list(filter(None, lines))

    timeline = Timeline(filename=file.filename, user_id=user_id)
    db.session.add(timeline)
    db.session.commit()

    pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\|\s+(.*?)\s+\|\s+lat:([\-\d.]+)\s+\|\s+lon:([\-\d.]+)'
    )

    for line in lines:
        match = pattern.match(line)
        if match:
            dt_str, desc, lat, lon = match.groups()
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                event = Event(
                    title=desc.strip().split(':')[0],
                    description=desc.strip(),
                    datetime_iso=dt.isoformat(),
                    timestamp=dt_str,
                    level='INFO',
                    latitude=float(lat),
                    longitude=float(lon),
                    timeline_id=timeline.id
                )
                db.session.add(event)
            except Exception as e:
                print(f"Error parsing line: {line}\n{e}")

    db.session.commit()

    response = {'status': 'ok', 'timeline_id': timeline.id}
    if not user_id:
        response['message'] = 'Файлът беше качен! Ако искате да видите времевата линия и картата, влезте в профила си.'
    return jsonify(response)

@app.route('/timeline/<int:timeline_id>', methods=['GET'])
def get_timeline(timeline_id):
    if 'user_id' not in session:
        return jsonify({'events': []})
    events = Event.query.filter_by(timeline_id=timeline_id).order_by(Event.datetime_iso).all()

    return jsonify({'events': [e.to_dict() for e in events]})

@app.route('/my-timelines', methods=['GET'])
def my_timelines():
    if 'user_id' not in session:
        return jsonify({'timelines': []})

    user_id = session['user_id']
    timelines = Timeline.query.filter_by(user_id=user_id).order_by(Timeline.created_at.desc()).all()

    return jsonify({
        'timelines': [{
            'id': t.id,
            'filename': t.filename,
            'created_at': t.created_at.strftime('%Y-%m-%d %H:%M')
        } for t in timelines]
    })

Event.to_dict = lambda self: {
    'level': self.level,
    'timestamp': self.timestamp,
    'title': self.title,
    'description': self.description,
    'datetime': self.datetime_iso,
    'latitude': self.latitude,
    'longitude': self.longitude
}

@app.route('/admin')
def admin_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user or not user.is_admin:
        return redirect(url_for('home'))

    timelines = Timeline.query.all()

    # Подготовка на филтри
    unique_usernames = sorted(set(
        t.user.username if t.user else 'Анонимен' for t in timelines
    ))

    unique_dates = sorted(set(
        t.created_at.strftime('%Y-%m-%d') for t in timelines
    ))

    return render_template(
        'admin.html',
        timelines=timelines,
        users=User.query.all(),
        unique_usernames=unique_usernames,
        unique_dates=unique_dates
    )


@app.route('/view_timeline/<int:timeline_id>')
def view_timeline(timeline_id):
    return render_template('index.html', logged_in=True, timeline_id=timeline_id, hide_upload_form = True)

if __name__ == '__main__':
    app.run(debug=True)
