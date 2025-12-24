# HR Task-Oriented Conversational Agent

A production-grade, deterministic HR task-oriented conversational agent built in Python. This system enables employees to interact with HR services through natural language conversations, handling tasks like time-off requests, meeting scheduling, IT ticket submission, and medical claim filing.

## 🚀 Features

- **Deterministic Architecture**: True FSM (Finite State Machine) controls all state transitions
- **Multi-Intent Support**: Handles 4 task intents with structured slot collection
- **Intelligent Intent Detection**: Uses Groq LLM for accurate intent classification
- **Natural Language Processing**: Groq-powered conversational responses for general HR queries
- **Multi-Slot Selection**: Can extract multiple slot values from a single utterance
- **Span-Based Extraction**: Verbatim extraction only (no generation or inference)
- **Intent Queuing**: New intents are queued during active task execution
- **Slot Retry Logic**: Maximum 3 retries per slot with graceful fallback
- **Normalization Support**: Handles ambiguous values (dates, times) with user confirmation
- **Action Execution**: Integrates with Slack and Twilio for real-world task completion
- **Web Interface**: Beautiful Flask-based web UI for easy interaction
- **Monitoring**: Prometheus metrics for observability
- **Persistent Storage**: Supabase integration for conversation history and audit logs

## 📋 Supported Intents

1. **`request_time_off`** - Request vacation, sick leave, or personal time off
2. **`schedule_meeting`** - Schedule meetings with participants
3. **`submit_it_ticket`** - Submit IT support tickets
4. **`file_medical_claim`** - File medical insurance claims

## 🏗️ Architecture

The system follows a strict deterministic architecture with clear separation of concerns:

### Core Components

- **Intent Detection**: Groq LLM-based classification (with rule-based fallback)
- **Slot Selection**: Multi-label classifier using Hugging Face models
- **Slot Extraction**: Span-based QA model (extractive only, no generation)
- **Dialogue Management**: True FSM (Finite State Machine) - NOT if/else logic
- **LLM Integration**: Groq used ONLY for natural language generation (UX enhancement)
- **Action Execution**: Deterministic API calls with LLM-assisted message composition
- **Storage**: Supabase for persistence and audit (FSM is source of truth)

### Technology Stack

- **Language**: Python 3.8+
- **LLM**: Groq API (Llama 3.1 8B Instant)
- **ML Models**: Hugging Face Transformers (DistilBERT, MobileBERT)
- **Web Framework**: Flask
- **Database**: Supabase (PostgreSQL)
- **APIs**: Slack SDK, Twilio SDK
- **Monitoring**: Prometheus
- **Dependencies**: PyTorch, Transformers, python-dotenv

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- API keys for:
  - Groq API
  - Slack Bot Token
  - Twilio Account (optional, for SMS notifications)
  - Supabase Project (optional, for persistence)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd HR-Project
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv myhrvenv
myhrvenv\Scripts\activate

# Linux/Mac
python3 -m venv myhrvenv
source myhrvenv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: On first run, Hugging Face models will be downloaded (~2.1 GB). This is a one-time download and models are cached locally.

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Option 1: Use the setup script
python setup_env.py

# Option 2: Copy from example
cp env.example .env
```

Edit `.env` with your actual credentials:

```env
# Required: Groq API Key
GROQ_API_KEY=your_groq_api_key

# Required: Slack Bot Token
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token

# Optional: Twilio Credentials (for SMS notifications)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=+1234567890
MANAGER_PHONE_NUMBER=+1234567890

# Optional: Supabase Credentials (for persistence)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Optional: Slack Channel Configuration
IT_CHANNEL=#it-support
IT_USER_ID=U1234567890
MANAGER_CHANNEL=#managers
MANAGER_USER_ID=U1234567890
HR_CHANNEL=#hr-department
HR_USER_ID=U1234567890
MEETING_CHANNEL=#meetings

# Optional: Flask Secret Key
FLASK_SECRET_KEY=your-secret-key-here
```

### Step 5: Set Up Supabase (Optional)

If you want to persist conversations:

1. Create a Supabase project at https://supabase.com
2. Run the SQL schema from `supabase_schema.sql` in the Supabase SQL Editor
3. Add your Supabase credentials to `.env`

See `setup_supabase.md` for detailed instructions.

## 🚀 Running the Application

### Web Interface (Recommended)

```bash
cd interface
python app.py
```

Then open your browser to: **http://localhost:5000**

The web interface provides:
- Real-time chat interface
- Conversation state tracking
- Reset conversation functionality
- Beautiful, responsive UI

### Command Line

```bash
python app.py
```

## 📁 Project Structure

```
HR-Project/
├── actions/              # External service integrations
│   ├── slack_service.py  # Slack API integration
│   └── twilio_service.py # Twilio SMS integration
├── dialogue/             # Dialogue management
│   ├── dialogue_manager.py  # Main dialogue orchestrator
│   └── fsm.py           # Finite State Machine implementation
├── intent/               # Intent detection
│   └── intent_router.py # Groq-based intent classifier
├── interface/           # Web interface
│   ├── app.py           # Flask web application
│   └── templates/       # HTML templates
├── llm/                 # LLM integration
│   ├── groq_client.py   # Groq API client
│   ├── message_composer.py  # Message generation
│   ├── normalizer.py    # Slot value normalization
│   └── question_rewriter.py # Question rephrasing
├── monitoring/          # Monitoring setup
│   ├── docker-compose.yml  # Prometheus + Grafana
│   └── prometheus.yml   # Prometheus configuration
├── slots/               # Slot handling
│   ├── schemas.py       # Intent and slot schemas
│   ├── slot_extractor.py # Value extraction
│   └── slot_selector.py # Slot selection
├── storage/             # Data persistence
│   ├── conversation_store.py  # Conversation storage
│   └── supabase_client.py     # Supabase client
├── tests/               # Test suite
├── utils/               # Utilities
│   └── model_loader.py  # Model pre-loading
├── app.py              # Main orchestrator
├── requirements.txt    # Python dependencies
├── env.example         # Environment variable template
└── README.md           # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for LLM services |
| `SLACK_BOT_TOKEN` | Yes | Slack bot token (starts with `xoxb-`) |
| `TWILIO_ACCOUNT_SID` | No | Twilio Account SID (starts with `AC`) |
| `TWILIO_AUTH_TOKEN` | No | Twilio authentication token |
| `TWILIO_FROM_NUMBER` | No | Twilio phone number (with country code) |
| `MANAGER_PHONE_NUMBER` | No | Manager phone for SMS notifications |
| `SUPABASE_URL` | No | Supabase project URL |
| `SUPABASE_KEY` | No | Supabase anon key |
| `IT_CHANNEL` | No | Slack IT support channel |
| `MANAGER_CHANNEL` | No | Slack manager channel |
| `HR_CHANNEL` | No | Slack HR channel |
| `MEETING_CHANNEL` | No | Slack meeting channel |
| `FLASK_SECRET_KEY` | No | Flask session secret key |

### Slack Setup

1. Create a Slack app at https://api.slack.com/apps
2. Add the following OAuth scopes:
   - `chat:write`
   - `channels:read`
   - `users:read`
   - `im:write`
3. Install the app to your workspace
4. Copy the Bot User OAuth Token to `.env`

### Twilio Setup

1. Create a Twilio account at https://www.twilio.com
2. Get a phone number from Twilio Console
3. Copy Account SID (starts with `AC`) and Auth Token
4. Add credentials to `.env`

**Important**: Account SID must start with `AC`, not `SK` (Secret Key).

## 🎯 How It Works

### Conversation Flow

1. **User Input**: User sends a message via web interface
2. **Intent Detection**: Groq LLM classifies the intent (or returns "none" for general chat)
3. **Slot Collection**: If task intent detected, FSM guides slot collection:
   - Slot selector identifies which slots can be answered
   - Slot extractor extracts values verbatim from user text
   - Questions are asked one at a time (structured TOD pattern)
4. **Action Execution**: When all slots filled:
   - Groq composes professional message content
   - Slack API sends message to appropriate channel/user
   - Twilio sends SMS notification to manager (if configured)
5. **State Management**: FSM tracks conversation state, handles retries, and manages intent queuing

### Action Execution

Actions are executed deterministically:

- **Message Composition**: Groq generates professional message text
- **API Execution**: SlackService/TwilioService execute via APIs
- **Channel Discovery**: Auto-discovers channels or uses environment variables
- **Fallback Chain**: Tries multiple channels/users before failing
- **Logging**: All actions logged to Supabase for audit

## 📊 Monitoring

### Prometheus Metrics

The application exposes Prometheus metrics at `/metrics`:

- `hr_chat_requests_total` - Total chat requests
- `hr_chat_request_errors_total` - Total errors
- `hr_chat_response_latency_seconds` - Response latency histogram

### Running Prometheus

```bash
cd monitoring
docker-compose up -d
```

Access Prometheus at: http://localhost:9090

## 🧪 Testing

Run the test suite:

```bash
# All tests
python tests/run_all_tests.py

# Windows
tests\run_tests.bat

# Linux/Mac
tests/run_tests.sh
```

Test coverage includes:
- Intent detection accuracy
- Slot extraction performance
- Slot selection accuracy
- Slack API integration
- Twilio SMS functionality

## 🔍 Troubleshooting

### Models Not Loading

- **Issue**: Models fail to download or load
- **Solution**: 
  - Check internet connection (needed for first download)
  - Ensure ~3 GB disk space available
  - Update transformers: `pip install --upgrade transformers`
  - System will automatically fall back to rule-based methods

### Slack Channel Not Found

- **Issue**: `channel_not_found` error
- **Solution**:
  - System auto-discovers channels - ensure channel exists
  - Set `IT_CHANNEL`, `MANAGER_CHANNEL`, etc. in `.env`
  - System falls back to general channel or workspace admins

### Twilio SMS Not Sending

- **Issue**: SMS notifications not working
- **Solution**:
  - Verify Account SID starts with `AC` (not `SK`)
  - Ensure FROM number is a Twilio-purchased number
  - Check phone numbers include country code with `+`
  - See `tests/TWILIO_SETUP_GUIDE.md` for detailed help

### Supabase Connection Issues

- **Issue**: Database errors
- **Solution**:
  - Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
  - Ensure schema is created (run `supabase_schema.sql`)
  - Check Supabase project is active

## 📚 Additional Documentation

- **MODELS.md** - Details about ML models used
- **CHANGES_SUMMARY.md** - Recent changes and improvements
- **interface/README.md** - Web interface documentation
- **tests/README.md** - Testing documentation
- **setup_supabase.md** - Supabase setup guide

## 🔐 Security Notes

- All API keys stored in `.env` file (gitignored)
- Never commit `.env` file to version control
- Use `env.example` as a template
- Rotate API keys regularly
- Use environment-specific credentials for production


## 📧 Support

For issues and questions, please open an issue in the repository.

---

**Built with ❤️ using Python, Groq, and Hugging Face Transformers**
