# Supabase Database Setup Guide

## Step 1: Access Supabase SQL Editor

1. Go to your Supabase project: https://werhpwxmikuzbzcnqbzt.supabase.co
2. Log in to your Supabase dashboard
3. Click on "SQL Editor" in the left sidebar

## Step 2: Run the Schema Script

1. Open the `supabase_schema.sql` file in this project
2. Copy the entire SQL script
3. Paste it into the Supabase SQL Editor
4. Click "Run" to execute the script

## Step 3: Verify Tables Created

After running the script, verify the tables were created:

1. Go to "Table Editor" in Supabase dashboard
2. You should see these tables:
   - `conversations`
   - `fsm_states`
   - `messages`
   - `action_executions`

## Step 4: Test the Application

Once the tables are created, run the application again:

```bash
python app.py
```

The Supabase errors should be gone, and the system will save conversation data properly.

## Troubleshooting

### If you get permission errors:
- Check that your Supabase API key has the correct permissions
- Verify Row Level Security (RLS) policies are set correctly
- You may need to use the service role key instead of the anon key for full access

### If tables already exist:
- The script uses `CREATE TABLE IF NOT EXISTS`, so it's safe to run multiple times
- If you need to reset, you can drop tables first (be careful!)

