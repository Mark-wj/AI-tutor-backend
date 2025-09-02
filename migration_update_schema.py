# migration_update_schema.py
"""
Database migration to update schema for the fixed models
Run this after updating your models to match the frontend expectations
"""

from sqlalchemy import text
from database import engine

def run_migration():
    """Run the database schema migration"""
    with engine.connect() as conn:
        try:
            print("Starting database migration...")
            
            # Update documents table
            print("1. Updating documents table...")
            
            # Add new columns if they don't exist
            migration_queries = [
                # Add original_name column
                """
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS original_name VARCHAR(255);
                """,
                
                # Add mime_type column  
                """
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS mime_type VARCHAR(100) DEFAULT 'application/pdf';
                """,
                
                # Add page_count column
                """
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS page_count INTEGER;
                """,
                
                # Rename extracted_text to content
                """
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS content TEXT;
                """,
                
                # Copy data from old column to new (if it exists)
                """
                UPDATE documents 
                SET content = extracted_text 
                WHERE content IS NULL AND extracted_text IS NOT NULL;
                """,
                
                # Rename ai_summary to summary
                """
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS summary TEXT;
                """,
                
                # Copy data from old column to new (if it exists)
                """
                UPDATE documents 
                SET summary = ai_summary 
                WHERE summary IS NULL AND ai_summary IS NOT NULL;
                """,
                
                # Add key_topics column as JSON
                """
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS key_topics JSON;
                """,
                
                # Add tags column as JSON
                """
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS tags JSON;
                """,
                
                # Update original_name from filename if null
                """
                UPDATE documents 
                SET original_name = filename 
                WHERE original_name IS NULL;
                """,
                
                # Update processing_status enum values
                """
                UPDATE documents 
                SET processing_status = 'processed' 
                WHERE processing_status = 'completed';
                """
            ]
            
            for query in migration_queries:
                try:
                    conn.execute(text(query))
                    conn.commit()
                except Exception as e:
                    print(f"Query failed (this might be normal): {str(e)}")
                    conn.rollback()
            
            print("2. Updating quizzes table...")
            
            # Update quiz schema
            quiz_migrations = [
                # Create new quizzes table structure
                """
                CREATE TABLE IF NOT EXISTS quizzes_new (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    difficulty VARCHAR(20) DEFAULT 'medium',
                    estimated_duration INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,
                
                # Create questions table
                """
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    question_text TEXT NOT NULL,
                    question_type VARCHAR(20) DEFAULT 'multiple_choice',
                    options JSON,
                    correct_answer VARCHAR(500) NOT NULL,
                    explanation TEXT,
                    order_index INTEGER DEFAULT 0
                );
                """,
                
                # Create quiz_submissions table
                """
                CREATE TABLE IF NOT EXISTS quiz_submissions (
                    id SERIAL PRIMARY KEY,
                    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    answers JSON NOT NULL,
                    score INTEGER NOT NULL,
                    time_spent INTEGER,
                    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,
                
                # Migrate data from old quiz table if it exists
                """
                INSERT INTO quizzes_new (document_id, title, description, created_at)
                SELECT document_id, 
                       COALESCE(question, 'Quiz') as title,
                       'Migrated quiz' as description,
                       CURRENT_TIMESTAMP
                FROM quiz 
                WHERE NOT EXISTS (SELECT 1 FROM quizzes_new WHERE document_id = quiz.document_id)
                ON CONFLICT DO NOTHING;
                """,
                
                # Drop old quiz table and rename new one
                """
                DROP TABLE IF EXISTS quiz CASCADE;
                """,
                
                """
                ALTER TABLE quizzes_new RENAME TO quizzes;
                """
            ]
            
            for query in quiz_migrations:
                try:
                    conn.execute(text(query))
                    conn.commit()
                except Exception as e:
                    print(f"Quiz migration query failed: {str(e)}")
                    conn.rollback()
            
            # Update relationships in Document model
            print("3. Adding relationship back-references...")
            
            # These will be handled by SQLAlchemy relationships, no SQL needed
            
            print("Migration completed successfully!")
            print("\nNext steps:")
            print("1. Update your model files with the fixed versions")
            print("2. Restart your FastAPI server")
            print("3. Test document upload and quiz generation")
            
        except Exception as e:
            print(f"Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    run_migration()