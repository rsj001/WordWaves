from flask import Flask, render_template, jsonify, request, send_file, abort
import sqlite3, psutil, os, pyjson5, git
import hmac, hashlib

w_secret = os.getenv("SECRET_KEY")
app = Flask(__name__)
DB_FILE = 'english_practice.db'

def fetch_all_texts():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM texts')
    texts = cursor.fetchall()
    conn.close()
    return texts

def execute_query(query, params=()):
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()
    cursor.execute(query, params)
    connection.commit()
    connection.close()

def fetch_query(query, params=(), fetchone=False):
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()
    cursor.execute(query, params)
    result = cursor.fetchone() if fetchone else cursor.fetchall()
    connection.close()
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/exercises')
def exercises():
    texts = fetch_all_texts()
    exercises = [{'id': text[0], 'title': text[1], 'visibility': text[3]} for text in texts]
    return render_template('exercises.html', exercises=exercises)

@app.route('/exercise/<text_id>')
def exercise(text_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM texts WHERE id = ? AND visibility = "public"', (text_id,))
    fetched = cursor.fetchone()
    conn.close()
    if not fetched:
        abort(404)
    return render_template('exercise.html', text_id=text_id)

@app.route('/get_text_content/<text_id>')
def get_text_content(text_id):

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM texts WHERE id = ? AND visibility = "public"', (text_id,))
    fetched = cursor.fetchone()
    conn.close()
    if not fetched:
        return jsonify({'error': 'Text not found'}), 404
    content = fetched[0]
    return jsonify({'content': content})

@app.route('/get_audio/<audio_id>')
def get_audio(audio_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT file FROM audios WHERE id = ?', (audio_id,))
    audio = cursor.fetchone()
    conn.close()
    audio_file = audio[0] if audio else None
    if audio_file:
        return send_file(audio_file)
    else:
        return jsonify({'error': 'Audio not found'}), 404

@app.route('/get_problem/<problem_id>')
def get_problem(problem_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT problem_data FROM problems WHERE id = ?', (problem_id,))
    fetched = cursor.fetchone()
    conn.close()
    if not fetched:
        return jsonify({'error': 'Problem not found'}), 404
    problem_data = pyjson5.loads(fetched[0])
    del problem_data["answer"]  # To prevent cheating
    return jsonify(problem_data)

@app.route('/check_results', methods=['POST'])
def check_results():
    answers = request.json['answers']
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    total_score = 0
    total_questions = len(answers)

    correct_answers = {}
    for problem_id, answer in answers.items():
        cursor.execute('SELECT problem_data FROM problems WHERE id = ?', (problem_id,))
        problem_data = pyjson5.loads(cursor.fetchone()[0])

        if problem_data['type'] in ('radio', 'checkbox'):
            correct_answers[problem_id] = set(answer) == set(str(i) for i in problem_data['answer'])
        elif problem_data['type'] == 'blank':
            correct_answers[problem_id] = answer.lower() in set(str(i).lower() for i in problem_data['answer'])
        if correct_answers[problem_id]:
            total_score += 1

    conn.close()
    return jsonify({'correct_answers': correct_answers, 'total_score': total_score, 'total_questions': total_questions})

@app.route('/problem_manage')
def problem_manage():
    return render_template('problem_manage.html')

@app.route('/add_problem', methods=['POST'])
def add_problem():
    text_id = request.form['text_id']
    problem_data = request.form['problem_data']

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO problems (text_id, problem_data) VALUES (?, ?)', (text_id, problem_data))
    problem_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'problem_id': problem_id})

@app.route('/add_text', methods=['POST'])
def add_text():
    text_content = request.form['text_content']
    text_title = request.form['text_title']

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO texts (content, title) VALUES (?, ?)', (text_content, text_title))
    text_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'text_id': text_id})

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM audios')
    last_id = cursor.fetchone()[0]
    conn.close()
    if last_id is None:
        last_id = 0
    audio_id = last_id + 1
    file = request.files['audio_file']
    filename = f"audio/{audio_id}.mp3"
    file.save(os.path.join(app.root_path, filename))

    text_id = request.form['text_id']
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO audios (file, text_id) VALUES (?, ?)', (filename, text_id))
    audio_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'audio_id': audio_id})

@app.route('/save_problem_changes', methods=['POST'])
def save_problem_changes():
    edit_problem_id = request.form['edit_problem_id']
    edit_text_id = request.form['edit_text_id']
    edit_problem_data = request.form['edit_problem_data']
    query = "UPDATE problems SET text_id = ?, problem_data = ? WHERE id = ?"
    execute_query(query, (edit_text_id, edit_problem_data, edit_problem_id))
    return jsonify({'success': True})

@app.route('/save_text_changes', methods=['POST'])
def save_text_changes():
    edit_text_id = request.form['edit_text_id']
    edit_text_title = request.form['edit_text_title']
    edit_text_content = request.form['edit_text_content']
    edit_text_visibility = request.form['edit_text_visibility']
    query = "UPDATE texts SET title = ?, content = ?, visibility = ? WHERE id = ?"
    execute_query(query, (edit_text_title, edit_text_content, edit_text_visibility, edit_text_id))
    return jsonify({'success': True})

@app.route('/edit_text/<text_id>')
def edit_text(text_id):
    query = "SELECT title, content, visibility FROM texts WHERE id = ?"
    text_data = fetch_query(query, (text_id,), fetchone=True)
    return render_template('text_editor.html', original_text_visibility=text_data[2], original_text_id=text_id, original_text_title=text_data[0], original_text_content=text_data[1])

@app.route('/edit_problem/<problem_id>')
def edit_problem(problem_id):
    query = "SELECT text_id, problem_data FROM problems WHERE id = ?"
    problem_data = fetch_query(query, (problem_id,), fetchone=True)
    return render_template('problem_editor.html', original_problem_id=problem_id, original_text_id=problem_data[0], original_problem_data=problem_data[1])

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

def get_dir_size(path='../'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

@app.route('/status')
def server_status():
    cpu_percent = psutil.cpu_percent()
    used_disk = round(get_dir_size() / (1024 ** 2), 2)
    return render_template('status.html', cpu_percent=cpu_percent, used_disk=used_disk)

def is_valid_signature(x_hub_signature, data, private_key):
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method != 'POST':
        return 'OK'
    else:
        abort_code = 418
        # Do initial validations on required headers
        if 'X-Github-Event' not in request.headers:
            abort(abort_code)
        if 'X-Github-Delivery' not in request.headers:
            abort(abort_code)
        if 'X-Hub-Signature' not in request.headers:
            abort(abort_code)
        if not request.is_json:
            abort(abort_code)
        if 'User-Agent' not in request.headers:
            abort(abort_code)
        ua = request.headers.get('User-Agent')
        if not ua.startswith('GitHub-Hookshot/'):
            abort(abort_code)

        event = request.headers.get('X-GitHub-Event')
        if event == "ping":
            return pyjson5.dumps({'msg': 'Hi!'})
        if event != "push":
            return pyjson5.dumps({'msg': "Wrong event type"})

        x_hub_signature = request.headers.get('X-Hub-Signature')
        # webhook content type should be application/json for request.data to have the payload
        # request.data is empty in case of x-www-form-urlencoded
        if not is_valid_signature(x_hub_signature, request.data, w_secret):
            print('Deploy signature failed: {sig}'.format(sig=x_hub_signature))
            abort(abort_code)

        payload = request.get_json()
        if payload is None:
            print('Deploy payload is empty: {payload}'.format(
                payload=payload))
            abort(abort_code)

        if payload['ref'] != 'refs/heads/main':
            return pyjson5.dumps({'msg': 'Not master; ignoring'})

        repo = git.Repo(app.root_path)
        origin = repo.remotes.origin

        pull_info = origin.pull()

        if len(pull_info) == 0:
            return pyjson5.dumps({'msg': "Didn't pull any information from remote!"})
        if pull_info[0].flags > 128:
            return pyjson5.dumps({'msg': "Didn't pull any information from remote!"})

        commit_hash = pull_info[0].commit.hexsha
        build_commit = f'build_commit = "{commit_hash}"'
        print(f'{build_commit}')
        return 'Updated PythonAnywhere server to commit {commit}'.format(commit=commit_hash)

if __name__ == '__main__':
    app.run(debug=True)