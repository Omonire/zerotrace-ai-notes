from supabase import create_client
import os

data_config = {
    "url": os.environ.get("SUPABASE_URL"),
    "key": os.environ.get("SUPABASE_KEY"),
    "anon": os.environ.get("SUPABASE_ANON_KEY"),
    "public": os.environ.get("SUPABASE_PUBLIC_KEY"),
    "service": os.environ.get("SUPABASE_SERVICE_KEY"),
    # Add more envs here
}

from . import db, notes, users, tags, bot, ai
# Migrate the Sqlite database to Supabase
def migrate_sqlite_to_supabase():
    # Initialize the Supabase client
    supabase = create_client(data_config["url"], data_config["key"])

    # Migrate users
    db.migrate_users(supabase)

    # Migrate notes
    db.migrate_notes(supabase)

    # Migrate tags
    db.migrate_tags(supabase)

    # Migrate bot
    bot.migrate_bot(supabase)

    # Migrate ai
    ai.migrate_ai(supabase)

# Create helper functions to interact with Supabase
def get_supabase_client():
    # Add block of configs code
    sb = create_client(data_config["url"], data_config["key"])
    return sb

    
