# Mix Master AI Chatbot

A Flask-powered AI chatbot that specializes in cocktails, beverages, and alcohol identification using OpenAI's GPT-4 Vision API.

## Features

- 🍷 **Image Analysis**: Upload images of drinks/bottles for AI identification
- 🍸 **Chat Interface**: Ask questions about cocktails, recipes, and ingredients  
- 💾 **Session Management**: Persistent chat history stored in database
- 📱 **Responsive Design**: Works on desktop and mobile devices
- 🎨 **Modern UI**: Beautiful gradient design with smooth animations

## API Endpoints

### Main Chatbot Endpoint
- **POST** `/api/alcoholbot`
  - **Text Message**: Send JSON with `{"text": "your message", "session_id": "optional"}`
  - **Image Upload**: Send form-data with `image` file and `session_id`
  - **Base64 Image**: Send JSON with `{"image_base64": "data:image/jpeg;base64,..."}`

### Utility Endpoints
- **GET** `/` - Serve the main chatbot interface
- **POST** `/api/alcoholbot/clear` - Clear chat history for a session
- **GET** `/api/health` - Health check endpoint
- **GET** `/api/analytics` - Get overall usage analytics
- **GET** `/api/session/<session_id>/stats` - Get session statistics
- **GET** `/static/uploads/<filename>` - Serve uploaded images

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Copy the example environment file and fill in your values:
```bash
copy .env.example .env
```

Edit `.env` with your actual values:
```env
OPENAI_API_KEY=your_openai_api_key
DB_HOST=localhost
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=mix_master_ai
```

### 3. Database Setup

#### Option A: Automatic Setup (Recommended)
```bash
python setup_database.py
```

#### Option B: Manual Setup
Run the SQL files in your MySQL client:
```bash
# For quick setup (minimal tables)
mysql -u your_user -p < quick_setup.sql

# For full setup (all features)
mysql -u your_user -p < database_schema.sql
```

### 4. Run the Application
```bash
python chatbot.py
```

The application will be available at `http://localhost:5000`

## Usage

### Web Interface
1. Open `http://localhost:5000` in your browser
2. Type messages in the chat input
3. Upload images by clicking the "📷 Image" button or drag & drop
4. Use "🗑️ Clear Chat" to reset conversation history

### API Usage Examples

#### Text Message
```bash
curl -X POST http://localhost:5000/api/alcoholbot \
  -H "Content-Type: application/json" \
  -d '{"text": "What makes a good Old Fashioned?", "session_id": "my_session"}'
```

#### Image Upload
```bash
curl -X POST http://localhost:5000/api/alcoholbot \
  -F "image=@whiskey_bottle.jpg" \
  -F "session_id=my_session"
```

#### Clear History
```bash
curl -X POST http://localhost:5000/api/alcoholbot/clear \
  -H "Content-Type: application/json" \
  -d '{"session_id": "my_session"}'
```

## Frontend Features

### Interactive Elements
- **Auto-resizing text input**
- **Drag & drop image upload**
- **Paste images from clipboard**
- **Typing indicators**
- **Smooth scrolling**
- **Mobile-responsive design**

### Visual Design
- **Gradient backgrounds**
- **Rounded chat bubbles**
- **Smooth animations**
- **Clean typography**
- **Accessible color contrast**

## File Structure
```
MIX_MASTER_API/
├── chatbot.py              # Main Flask application
├── chatbot.html            # Frontend interface
├── database.py             # Database utilities and manager
├── setup_database.py       # Database setup script
├── test_api.py             # API testing script
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── database_schema.sql     # Complete database schema
├── quick_setup.sql        # Minimal database setup
├── static/uploads/        # Image upload directory
└── .env                   # Environment variables (create from .env.example)
```

## Testing

Run the test script to verify all endpoints:
```bash
python test_api.py
```

## Technologies Used

- **Backend**: Flask, OpenAI API, PyMySQL
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **AI**: GPT-4 Vision for image analysis, GPT-4 for text responses
- **Database**: MySQL for chat history storage
- **Styling**: CSS Grid/Flexbox, CSS animations

## Browser Support

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
