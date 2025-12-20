"""
Setup script to create .env file from env.example
Run this script to set up your environment variables.
"""

import shutil
import os

def setup_env():
    """Create .env file from env.example if it doesn't exist."""
    env_file = ".env"
    env_example = "env.example"
    
    if os.path.exists(env_file):
        print(f"{env_file} already exists. Skipping setup.")
        return
    
    if not os.path.exists(env_example):
        print(f"Error: {env_example} not found. Please create it manually.")
        return
    
    try:
        shutil.copy(env_example, env_file)
        print(f"✓ Created {env_file} from {env_example}")
        print(f"✓ Please review and update {env_file} with your actual credentials if needed.")
    except Exception as e:
        print(f"Error creating {env_file}: {e}")
        print(f"Please manually copy {env_example} to {env_file}")

if __name__ == "__main__":
    setup_env()

