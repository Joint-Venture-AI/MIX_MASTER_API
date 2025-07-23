import os
import pymysql
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME", "mix_master_ai")
        
        # Initialize database and tables
        self._init_database()
    
    def get_connection(self):
        """Get a database connection"""
        try:
            conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.database,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
            )
            return conn
        except Exception as e:
            logging.error(f"Database connection failed: {str(e)}")
            raise
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist"""
        try:
            # First connect without specifying database to create it if needed
            conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
            )
            
            with conn.cursor() as cursor:
                # Create database if it doesn't exist
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                cursor.execute(f"USE `{self.database}`")
                
                # Drop tables if they exist to avoid key conflicts, then recreate
                cursor.execute("DROP TABLE IF EXISTS `chat_messages`")
                cursor.execute("DROP TABLE IF EXISTS `sessions`")
                
                # Create sessions table for analytics
                cursor.execute("""
                    CREATE TABLE `sessions` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `session_id` varchar(255) NOT NULL,
                        `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        `last_activity` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        `message_count` int(11) DEFAULT 0,
                        PRIMARY KEY (`id`),
                        UNIQUE KEY `unique_session_id` (`session_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # Create chat_messages table
                cursor.execute("""
                    CREATE TABLE `chat_messages` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `session_id` varchar(255) NOT NULL,
                        `message_type` enum('user','assistant') NOT NULL,
                        `content` text NOT NULL,
                        `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (`id`),
                        KEY `idx_session_id` (`session_id`),
                        KEY `idx_timestamp` (`timestamp`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
            conn.close()
            logging.info("Database and tables initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize database: {str(e)}")
            # For development purposes, we'll continue without database
            logging.warning("Continuing without database - some features may not work")
    
    def save_message(self, session_id, message_type, content):
        """Save a chat message to the database"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Insert the message
                cursor.execute(
                    "INSERT INTO chat_messages (session_id, message_type, content) VALUES (%s, %s, %s)",
                    (session_id, message_type, content)
                )
                
                # Update or create session record
                cursor.execute("""
                    INSERT INTO sessions (session_id, message_count) 
                    VALUES (%s, 1) 
                    ON DUPLICATE KEY UPDATE 
                    message_count = message_count + 1,
                    last_activity = CURRENT_TIMESTAMP
                """, (session_id,))
                
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Failed to save message: {str(e)}")
            return False
    
    def get_chat_history(self, session_id, limit=50):
        """Retrieve chat history for a session"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT message_type as role, content 
                    FROM chat_messages 
                    WHERE session_id = %s 
                    ORDER BY timestamp ASC 
                    LIMIT %s
                """, (session_id, limit))
                
                rows = cursor.fetchall()
                # Convert tuples to list of dictionaries
                messages = [{"role": row[0], "content": row[1]} for row in rows]
            conn.close()
            return messages
        except Exception as e:
            logging.error(f"Failed to get chat history: {str(e)}")
            return []
    
    def clear_chat_history(self, session_id):
        """Clear chat history for a session"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM chat_messages WHERE session_id = %s", (session_id,))
                cursor.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Failed to clear chat history: {str(e)}")
            return False
    
    def get_analytics(self):
        """Get overall usage analytics"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Total sessions
                cursor.execute("SELECT COUNT(*) as total_sessions FROM sessions")
                total_sessions = cursor.fetchone()['total_sessions']
                
                # Total messages
                cursor.execute("SELECT COUNT(*) as total_messages FROM chat_messages")
                total_messages = cursor.fetchone()['total_messages']
                
                # Messages by type
                cursor.execute("""
                    SELECT message_type, COUNT(*) as count 
                    FROM chat_messages 
                    GROUP BY message_type
                """)
                messages_by_type = {row['message_type']: row['count'] for row in cursor.fetchall()}
                
                # Active sessions (last 24 hours)
                cursor.execute("""
                    SELECT COUNT(*) as active_sessions 
                    FROM sessions 
                    WHERE last_activity >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                """)
                active_sessions = cursor.fetchone()['active_sessions']
                
                # Average messages per session
                avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
                
            conn.close()
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'messages_by_type': messages_by_type,
                'active_sessions_24h': active_sessions,
                'avg_messages_per_session': round(avg_messages, 2)
            }
        except Exception as e:
            logging.error(f"Failed to get analytics: {str(e)}")
            return {
                'total_sessions': 0,
                'total_messages': 0,
                'messages_by_type': {},
                'active_sessions_24h': 0,
                'avg_messages_per_session': 0
            }
    
    def get_session_stats(self, session_id):
        """Get statistics for a specific session"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Session info
                cursor.execute("""
                    SELECT session_id, created_at, last_activity, message_count 
                    FROM sessions 
                    WHERE session_id = %s
                """, (session_id,))
                session = cursor.fetchone()
                
                if not session:
                    return None
                
                # Message breakdown
                cursor.execute("""
                    SELECT message_type, COUNT(*) as count 
                    FROM chat_messages 
                    WHERE session_id = %s 
                    GROUP BY message_type
                """, (session_id,))
                message_breakdown = {row['message_type']: row['count'] for row in cursor.fetchall()}
                
            conn.close()
            
            return {
                'session_id': session['session_id'],
                'created_at': session['created_at'].isoformat() if session['created_at'] else None,
                'last_activity': session['last_activity'].isoformat() if session['last_activity'] else None,
                'total_messages': session['message_count'],
                'message_breakdown': message_breakdown
            }
        except Exception as e:
            logging.error(f"Failed to get session stats: {str(e)}")
            return None

# Create global instance
db_manager = DatabaseManager()
