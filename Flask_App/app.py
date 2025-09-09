from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import sqlite3
import os
import requests
from datetime import datetime
import io
from werkzeug.utils import secure_filename
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('demand_letters.db')
    cursor = conn.cursor()
    
    # Create files table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txt_filename TEXT,
            csv_filename TEXT,
            txt_content TEXT,
            csv_content TEXT,
            docx_filename TEXT,
            docx_content BLOB,
            upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'processing'
        )
    ''')
    
    # Create chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/main')
def main():
    return render_template('main.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        if 'txt_file' not in request.files or 'csv_file' not in request.files:
            return jsonify({'error': 'Both TXT and CSV files are required'}), 400
        
        txt_file = request.files['txt_file']
        csv_file = request.files['csv_file']
        
        if txt_file.filename == '' or csv_file.filename == '':
            return jsonify({'error': 'Please select both files'}), 400
        
        if not (allowed_file(txt_file.filename, ['txt']) and allowed_file(csv_file.filename, ['csv'])):
            return jsonify({'error': 'Invalid file types. Only TXT and CSV files are allowed'}), 400
        
        # Read file contents
        txt_content = txt_file.read().decode('utf-8')
        csv_content = csv_file.read().decode('utf-8')
        
        # Save to database
        conn = sqlite3.connect('demand_letters.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO files (txt_filename, csv_filename, txt_content, csv_content)
            VALUES (?, ?, ?, ?)
        ''', (secure_filename(txt_file.filename), secure_filename(csv_file.filename), txt_content, csv_content))
        file_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Send to webhook in background
        threading.Thread(target=process_webhook, args=(file_id, txt_content, csv_content)).start()
        
        return jsonify({'success': True, 'file_id': file_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_webhook(file_id, txt_content, csv_content):
    try:
        # Prepare data for webhook
        files = {
            'txt_file': ('document.txt', txt_content, 'text/plain'),
            'csv_file': ('data.csv', csv_content, 'text/csv')
        }
        
        webhook_url = "https://primary-production-d168.up.railway.app/webhook/fe0bef47-853a-4e8b-bbf0-a2cdee4e18b1"
        
        # Send to webhook (no timeout)
        response = requests.post(webhook_url, files=files)
        
        if response.status_code == 200:
            # Save the docx response
            conn = sqlite3.connect('demand_letters.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE files SET docx_content = ?, docx_filename = ?, status = ?
                WHERE id = ?
            ''', (response.content, f'demand_letter_{file_id}.docx', 'completed', file_id))
            conn.commit()
            conn.close()
        else:
            # Update status to failed
            conn = sqlite3.connect('demand_letters.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE files SET status = ? WHERE id = ?', ('failed', file_id))
            conn.commit()
            conn.close()
            
    except Exception as e:
        # Update status to failed
        conn = sqlite3.connect('demand_letters.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE files SET status = ? WHERE id = ?', ('failed', file_id))
        conn.commit()
        conn.close()

@app.route('/check_status/<int:file_id>')
def check_status(file_id):
    conn = sqlite3.connect('demand_letters.db')
    cursor = conn.cursor()
    cursor.execute('SELECT status, docx_filename FROM files WHERE id = ?', (file_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return jsonify({'status': result[0], 'filename': result[1]})
    return jsonify({'error': 'File not found'}), 404

@app.route('/download/<int:file_id>')
def download_file(file_id):
    conn = sqlite3.connect('demand_letters.db')
    cursor = conn.cursor()
    cursor.execute('SELECT docx_content, docx_filename FROM files WHERE id = ?', (file_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        return send_file(
            io.BytesIO(result[0]),
            as_attachment=True,
            download_name=result[1],
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    return jsonify({'error': 'File not found or not ready'}), 404

@app.route('/chat')
def chat():
    # Get chat history
    conn = sqlite3.connect('demand_letters.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_message, bot_response, timestamp FROM chat_history ORDER BY timestamp')
    history = cursor.fetchall()
    conn.close()
    return render_template('chat.html', history=history)

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Send to chat webhook
        webhook_url = "https://primary-production-d168.up.railway.app/webhook/71882e84-1d48-49bc-94b7-0de906a04df2"
        response = requests.post(webhook_url, json={'message': user_message})
        
        if response.status_code == 200:
            bot_response = response.text
        else:
            bot_response = "Sorry, I couldn't process your message at the moment."
        
        # Save to database
        conn = sqlite3.connect('demand_letters.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (user_message, bot_response)
            VALUES (?, ?)
        ''', (user_message, bot_response))
        conn.commit()
        conn.close()
        
        return jsonify({'response': bot_response})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def history():
    conn = sqlite3.connect('demand_letters.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, txt_filename, csv_filename, docx_filename, upload_timestamp, status
        FROM files ORDER BY upload_timestamp DESC
    ''')
    files = cursor.fetchall()
    conn.close()
    return render_template('history.html', files=files)

if __name__ == '__main__':
    app.run(debug=True)
