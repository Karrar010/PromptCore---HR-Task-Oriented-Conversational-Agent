-- Supabase Database Schema for HR Conversational Agent
-- Run this SQL in your Supabase SQL Editor to create the required tables

-- Table: conversations
-- Stores conversation metadata
CREATE TABLE IF NOT EXISTS public.conversations (
    conversation_id TEXT PRIMARY KEY,
    user_id TEXT,
    channel TEXT,
    platform TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table: fsm_states
-- Stores FSM state snapshots
CREATE TABLE IF NOT EXISTS public.fsm_states (
    conversation_id TEXT PRIMARY KEY,
    state_snapshot JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id) ON DELETE CASCADE
);

-- Table: messages
-- Stores conversation messages (user and bot)
CREATE TABLE IF NOT EXISTS public.messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    message_type TEXT NOT NULL CHECK (message_type IN ('user', 'bot')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id) ON DELETE CASCADE
);

-- Table: action_executions
-- Stores action execution logs
CREATE TABLE IF NOT EXISTS public.action_executions (
    id BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    intent_name TEXT NOT NULL,
    slot_values JSONB NOT NULL,
    execution_status TEXT NOT NULL CHECK (execution_status IN ('success', 'failure')),
    message_content TEXT,
    error_message TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON public.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON public.messages(created_at);
CREATE INDEX IF NOT EXISTS idx_action_executions_conversation_id ON public.action_executions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_action_executions_intent_name ON public.action_executions(intent_name);
CREATE INDEX IF NOT EXISTS idx_action_executions_executed_at ON public.action_executions(executed_at);

-- Enable Row Level Security (RLS) - adjust policies as needed
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fsm_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.action_executions ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all for now - adjust based on your security needs)
-- For production, you should create proper RLS policies
CREATE POLICY "Allow all operations on conversations" ON public.conversations
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on fsm_states" ON public.fsm_states
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on messages" ON public.messages
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on action_executions" ON public.action_executions
    FOR ALL USING (true) WITH CHECK (true);

