import sqlite3

def initialize_database():
    conn = sqlite3.connect('english_practice.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS texts (
        id INTEGER PRIMARY KEY,
        title VARCHAR,
        content TEXT,
        visibility VARCHAR CHECK(visibility IN ('public', 'private')) DEFAULT 'public' NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audios (
        id INTEGER PRIMARY KEY,
        file TEXT,
        text_id INTEGER,
        FOREIGN KEY (text_id) REFERENCES texts(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY,
        text_id INTEGER,
        problem_data TEXT,
        FOREIGN KEY (text_id) REFERENCES texts(id)
    )
    ''')

    texts_data = [
        (1, "Next Car Drive Itself", """#### Read the following text, and then listen to the audio, and answer problems. 
        Will Your Next Car Drive Itself?
        \nYou know how much your telephone has changed over the past 10 years? 
        Your car will change even more than that in the **next 10 years**.\n
        Now listen this audio: \n[audio=1]\n
        Answer problem below:\n[problem=1]\n[problem=2]\n
        So what do you think:\n[problem=3]""", "public")
    ]

    audios_data = [
        (1, "audio/audio_file.mp3", 1)
    ]

    problems_data = [
        (1, 1, '{"type": "radio", "question": "What is the main topic of the text?", "options": ["Telephones", "Cars", "Technology"], "answer": [1]}'),
        (2, 1, '{"type": "checkbox", "question": "What may change significantly in the **next 10 years**?", "options": ["Telephones", "Cars", "Weather", "People\'s preferences"], "answer": [1, 3]}'),
        (3, 1, '{"type": "blank", "question": "Give your opinion on the future of cars.", "answer": "opinion"}')
    ]

    cursor.executemany('INSERT INTO texts VALUES (?, ?, ?, ?)', texts_data)
    cursor.executemany('INSERT INTO audios VALUES (?, ?, ?)', audios_data)
    cursor.executemany('INSERT INTO problems VALUES (?, ?, ?)', problems_data)

    conn.commit()
    conn.close()

    print("Database initialization completed.")

if __name__ == '__main__':
    initialize_database()
