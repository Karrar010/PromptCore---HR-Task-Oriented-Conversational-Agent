# HR Task-Oriented Conversational Agent

A production-grade,  deterministic HR task-oriented conversational agent built in Python with strict architecture compliance.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with your API credentials:

```bash
# Option 1: Run the setup script
python setup_env.py

# Option 2: Manually copy env.example to .env
cp env.example .env
```

Then edit `.env` with your actual credentials:

```env
# Groq API Key
GROQ_API_KEY=your_groq_api_key

# Slack Bot Token
SLACK_BOT_TOKEN=your_slack_bot_token

# Twilio Credentials
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=your_twilio_phone_number

# Supabase Credentials
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 3. Run the Application

```bash
python app.py
```

## Architecture

The system follows a strict deterministic architecture:

- **Intent Detection**: Rule-based router (keyword + pattern matching)
- **Slot Selection**: Multi-label selector using Hugging Face models
- **Slot Extraction**: Span-based QA model (extractive only)
- **Dialogue Management**: True FSM (Finite State Machine) - NOT if/else logic
- **LLM Integration**: Groq used ONLY for natural language generation (UX)
- **Action Execution**: Deterministic with LLM-assisted message composition
- **Storage**: Supabase for persistence and audit (FSM is source of truth)

## Project Structure

```
/intent/          - Intent router (rule-based)
/slots/           - Slot selector, extractor, schemas
/dialogue/        - FSM and dialogue manager
/llm/             - Groq client, question rewriter, normalizer, message composer
/storage/         - Supabase client and conversation store
/actions/         - Slack and Twilio services
app.py            - Main orchestrator
```

## Key Features

- ✅ Deterministic FSM controls all state transitions
- ✅ Multi-slot selection (returns list, not single slot)
- ✅ Span-based extraction (verbatim only, no generation)
- ✅ Intent queuing (new intents queued during active task)
- ✅ Slot retry limits (max 3 retries per slot)
- ✅ Confirmation required for normalization
- ✅ Supabase as audit layer only (FSM is source of truth)

## Supported Intents

- `request_time_off` - Request time off/vacation
- `schedule_meeting` - Schedule a meeting
- `submit_it_ticket` - Submit IT support ticket
- `file_medical_claim` - File medical insurance claim

## Notes

- All API keys are stored in `.env` file (not committed to version control)
- The `.env` file is gitignored for security
- Use `env.example` as a template for your `.env` file

