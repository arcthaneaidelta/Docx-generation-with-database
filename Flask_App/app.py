from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import sqlite3
import os
from datetime import datetime
import requests
import io
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database initialization
def init_db():
    conn = sqlite3.connect('chat_processor.db')
    cursor = conn.cursor()
    
    # Create files table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            content BLOB,
            upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            associated_message TEXT,
            chat_session_id TEXT
        )
    ''')
    
    # Create chat_history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_message TEXT,
            csv_file_info TEXT,
            txt_file_info TEXT,
            response_file_info TEXT,
            chat_messages TEXT,
            status TEXT DEFAULT 'completed'
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def store_file_in_db(filename, file_content, file_type, message, session_id):
    """Store file in database and return file ID"""
    conn = sqlite3.connect('chat_processor.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO files (filename, file_type, content, associated_message, chat_session_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (filename, file_type, file_content, message, session_id))
    
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return file_id

def get_file_from_db(file_id):
    """Retrieve file from database"""
    conn = sqlite3.connect('chat_processor.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT filename, content, file_type FROM files WHERE id = ?', (file_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result

def store_chat_history(session_id, user_message, csv_info, txt_info, response_info, chat_messages):
    """Store chat session in database"""
    conn = sqlite3.connect('chat_processor.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO chat_history (session_id, user_message, csv_file_info, txt_file_info, response_file_info, chat_messages)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, user_message, csv_info, txt_info, response_info, chat_messages))
    
    conn.commit()
    conn.close()

def get_chat_history():
    """Get last 10 chat sessions"""
    conn = sqlite3.connect('chat_processor.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT session_id, timestamp, user_message, csv_file_info, txt_file_info, response_file_info, status
        FROM chat_history 
        ORDER BY timestamp DESC 
        LIMIT 10
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    # Debug: Print the results to console
    print(f"Chat history results: {len(results)} sessions found")
    for i, result in enumerate(results):
        print(f"Session {i+1}: {result}")
    
    return results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat-history')
def chat_history():
    try:
        history = get_chat_history()
        print(f"Rendering chat history with {len(history)} items")
        return render_template('chat_history.html', history=history)
    except Exception as e:
        print(f"Error in chat_history route: {str(e)}")
        return render_template('chat_history.html', history=[])

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # Check if files and message are present
        if 'csv_file' not in request.files or 'txt_file' not in request.files:
            return jsonify({'error': 'Both CSV and TXT files are required'}), 400
        
        csv_file = request.files['csv_file']
        txt_file = request.files['txt_file']
        message = request.form.get('message', '')
        
        if csv_file.filename == '' or txt_file.filename == '':
            return jsonify({'error': 'Both files must be selected'}), 400
        
        # Validate file types
        if not allowed_file(csv_file.filename, {'csv'}):
            return jsonify({'error': 'CSV file must have .csv extension'}), 400
            
        if not allowed_file(txt_file.filename, {'txt'}):
            return jsonify({'error': 'Text file must have .txt extension'}), 400
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Read file contents
        csv_content = csv_file.read()
        txt_content = txt_file.read()
        
        # Store files in database
        csv_file_id = store_file_in_db(
            secure_filename(csv_file.filename),
            csv_content,
            'csv',
            message,
            session_id
        )
        
        txt_file_id = store_file_in_db(
            secure_filename(txt_file.filename),
            txt_content,
            'txt',
            message,
            session_id
        )
        
        # Prepare data for webhook
        files = {
            'csv_file': (csv_file.filename, io.BytesIO(csv_content), 'text/csv'),
            'txt_file': (txt_file.filename, io.BytesIO(txt_content), 'text/plain')
        }
        
        data = {'message': message}
        
        try:
            # Send to webhook
            webhook_url = 'https://primary-production-d168.up.railway.app/webhook/fe0bef47-853a-4e8b-bbf0-a2cdee4e18b1'
            response = requests.post(webhook_url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                # Check if response is a DOCX file
                content_type = response.headers.get('content-type', '')
                if 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                    # Store response file in database
                    response_filename = f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                    response_file_id = store_file_in_db(
                        response_filename,
                        response.content,
                        'docx',
                        f"Response for: {message}",
                        session_id
                    )
                    
                    # Store chat history
                    store_chat_history(
                        session_id,
                        message,
                        f"{csv_file.filename} (ID: {csv_file_id})",
                        f"{txt_file.filename} (ID: {txt_file_id})",
                        f"{response_filename} (ID: {response_file_id})",
                        f"Files processed successfully"
                    )
                    
                    print(f"Stored chat history for session: {session_id}")  # Debug log
                    
                    return jsonify({
                        'success': True,
                        'message': 'Files processed successfully',
                        'download_file_id': response_file_id,
                        'download_filename': response_filename
                    })
                else:
                    # Handle text response
                    response_text = response.text
                    store_chat_history(
                        session_id,
                        message,
                        f"{csv_file.filename} (ID: {csv_file_id})",
                        f"{txt_file.filename} (ID: {txt_file_id})",
                        "Text response",
                        response_text
                    )
                    
                    return jsonify({
                        'success': True,
                        'message': response_text
                    })
            else:
                raise Exception(f"Webhook returned status code: {response.status_code}")
                
        except Exception as webhook_error:
            # Simulate response for demo (webhook not available)
            print(f"Webhook error: {webhook_error}")
            
            # Create simulated response file
            simulated_content = f"""Processed Response Document

Original Message: {message}
CSV File: {csv_file.filename}
TXT File: {txt_file.filename}
Processing Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is a simulated response document for demonstration purposes.
In a real implementation, this would be the processed result from your webhook."""
            
            response_filename = f"processed_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            response_file_id = store_file_in_db(
                response_filename,
                simulated_content.encode('utf-8'),
                'docx',
                f"Simulated response for: {message}",
                session_id
            )
            
            # Store chat history
            store_chat_history(
                session_id,
                message,
                f"{csv_file.filename} (ID: {csv_file_id})",
                f"{txt_file.filename} (ID: {txt_file_id})",
                f"{response_filename} (ID: {response_file_id})",
                "Files processed successfully (simulated)"
            )
            
            print(f"Stored simulated chat history for session: {session_id}")  # Debug log
            
            return jsonify({
                'success': True,
                'message': 'Files processed successfully (Demo Mode)',
                'download_file_id': response_file_id,
                'download_filename': response_filename,
                'demo_mode': True
            })
            
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/download/<int:file_id>')
def download_file(file_id):
    try:
        file_data = get_file_from_db(file_id)
        if not file_data:
            return "File not found", 404
        
        filename, content, file_type = file_data
        
        # Create appropriate MIME type
        if file_type == 'docx':
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif file_type == 'csv':
            mimetype = 'text/csv'
        elif file_type == 'txt':
            mimetype = 'text/plain'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(
            io.BytesIO(content),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return f"Error downloading file: {str(e)}", 500

@app.route('/view-chat/<session_id>')
def view_chat_details(session_id):
    """View detailed chat information"""
    conn = sqlite3.connect('chat_processor.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM chat_history WHERE session_id = ?
    ''', (session_id,))
    
    chat_data = cursor.fetchone()
    
    # Get associated files
    cursor.execute('''
        SELECT id, filename, file_type, upload_timestamp FROM files WHERE chat_session_id = ?
    ''', (session_id,))
    
    files_data = cursor.fetchall()
    conn.close()
    
    if not chat_data:
        return "Chat not found", 404
    
    return render_template('chat_details.html', chat=chat_data, files=files_data)

if __name__ == '__main__':

    app.run(debug=True, port=5000)
