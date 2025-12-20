# HR Conversational Agent Web Interface

A beautiful web interface for interacting with the HR Conversational Agent.

## Running the Interface

1. Make sure you're in the project root directory
2. Activate your virtual environment:
   ```bash
   # Windows
   myhrvenv\Scripts\activate
   
   # Linux/Mac
   source myhrvenv/bin/activate
   ```

3. Navigate to the interface directory:
   ```bash
   cd interface
   ```

4. Run the Flask application:
   ```bash
   python app.py
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Features

- **Real-time Chat Interface**: Clean, modern chat UI
- **Conversation Management**: Start new conversations with the reset button
- **Background Processing**: All HR agent processing happens in the background
- **State Tracking**: See current conversation state and active intent
- **Responsive Design**: Works on desktop and mobile devices

## Usage

1. Type your message in the input field
2. Press Enter or click Send
3. The HR agent will process your request and respond
4. Continue the conversation to complete tasks like:
   - Request time off
   - Schedule meetings
   - Submit IT tickets
   - File medical claims

## API Endpoints

- `GET /` - Main chat interface
- `POST /api/chat` - Send a message and get response
- `GET /api/state` - Get current conversation state
- `POST /api/reset` - Reset the conversation

## Notes

- Each browser session gets its own conversation
- Conversations are saved to Supabase automatically
- The interface handles all backend processing transparently

