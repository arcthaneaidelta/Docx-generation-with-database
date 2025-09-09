# Demand Letter Generator Web System

A fully responsive web application for generating professional demand letters using AI-powered processing. Built with Flask, SQLite, and modern web technologies.

## Features

### 🏠 **Home Page (`/`)**
- Welcome page with system overview
- Feature highlights and how-it-works section
- Animated UI with AOS (Animate On Scroll) effects

### 📄 **Document Generator (`/main`)**
- Upload TXT template and CSV data files
- Real-time processing status updates
- Automatic webhook integration for AI processing
- Download generated DOCX files
- File validation and error handling

### 💬 **AI Chat Assistant (`/chat`)**
- Interactive chatbot interface
- Real-time messaging with webhook integration
- Chat history persistence
- Sample questions for quick start
- Typing indicators and smooth animations

### 📊 **History Dashboard (`/history`)**
- Complete document generation history
- Advanced filtering and search functionality
- Status tracking (Processing, Completed, Failed)
- Bulk download capabilities
- Statistics overview

## Tech Stack

- **Backend**: Python 3.8+, Flask 3.0.0
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Animations**: AOS (Animate On Scroll)
- **Icons**: Font Awesome 6.4.0
- **Styling**: Custom CSS with gradients and modern design

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### 1. Clone or Create Project
```bash
mkdir demand-letter-generator
cd demand-letter-generator
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Project Structure
Create the following directory structure:
```
demand-letter-generator/
│
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
│
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── main.html
│   ├── chat.html
│   └── history.html
│
├── uploads/              # File upload directory (auto-created)
└── demand_letters.db     # SQLite database (auto-created)
```

### 5. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Configuration

### Webhook URLs
The system uses two webhook endpoints:

1. **Document Generation**: 
   - URL: `https://primary-production-d168.up.railway.app/webhook/fe0bef47-853a-4e8b-bbf0-a2cdee4e18b1`
   - Purpose: Process TXT/CSV files and return DOCX document

2. **Chat Assistant**: 
   - URL: `https://primary-production-d168.up.railway.app/webhook/71882e84-1d48-49bc-94b7-0de906a04df2`
   - Purpose: Handle chat messages and return responses

### File Limits
- Maximum file size: 16MB
- Supported formats: TXT, CSV
- Generated format: DOCX

### Security Settings
- Update `app.config['SECRET_KEY']` in `app.py` for production
- Consider implementing user authentication for production use

## API Endpoints

### File Upload & Processing
- `POST /upload` - Upload TXT and CSV files
- `GET /check_status/<file_id>` - Check processing status
- `GET /download/<file_id>` - Download generated DOCX

### Chat System
- `POST /send_message` - Send message to AI chat assistant

### Navigation
- `GET /` - Home page
- `GET /main` - Document generator
- `GET /chat` - Chat interface
- `GET /history` - Document history

## Database Schema

### Files Table
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txt_filename TEXT,
    csv_filename TEXT,
    txt_content TEXT,
    csv_content TEXT,
    docx_filename TEXT,
    docx_content BLOB,
    upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'processing'
);
```

### Chat History Table
```sql
CREATE TABLE chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_message TEXT,
    bot_response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Features in Detail

### 🎨 **Responsive Design**
- Mobile-first approach
- Flexible grid layouts
- Touch-friendly interface
- Cross-browser compatibility

### 🔄 **Real-time Updates**
- Processing status checking
- Auto-refresh for pending documents
- Live chat interface
- Progress indicators

### 🎭 **Animations & UX**
- Smooth transitions and hover effects
- Loading indicators and progress bars
- Toast notifications and feedback
- Modern glassmorphism design elements

### 🔍 **Advanced Filtering**
- Search by filename
- Filter by status
- Date-based sorting
- Quick statistics overview

## Deployment

### Environment Variables (Production)
```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here
```

### Production Considerations
1. Use a production WSGI server (Gunicorn, uWSGI)
2. Configure proper logging
3. Set up database backups
4. Implement rate limiting
5. Add SSL/HTTPS support
6. Configure file upload limits

### Example Gunicorn Deployment
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Troubleshooting

### Common Issues

1. **Database Lock Error**
   - Ensure proper database connection handling
   - Check file permissions

2. **Webhook Timeout**
   - Webhooks run without timeout by design
   - Check network connectivity

3. **File Upload Issues**
   - Verify file size limits
   - Check file permissions in uploads directory

4. **Chat Not Responding**
   - Verify webhook URL accessibility
   - Check network connectivity and firewall settings

### Logs and Debugging
Enable Flask debug mode for development:
```python
app.run(debug=True)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the code comments
3. Test with sample files
4. Verify webhook endpoints are accessible

---

**Note**: This system requires active webhook endpoints for full functionality. Ensure the provided webhook URLs are accessible and properly configured for your use case.
