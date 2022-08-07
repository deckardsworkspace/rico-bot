from dataclass.recommendation import Recommendation
from dataclass.spotify_auth import SpotifyCredentials
from typing import Any, Dict, List, Tuple
from .enums import RecommendationType
import psycopg2


def rec_enum_from_row(row: Tuple[Any, ...]) -> RecommendationType:
    return Recommendation(
        id=row[0],
        timestamp=row[1],
        recommendee=row[2],
        recommender=row[3],
        type=RecommendationType(row[4]),
        title=row[5],
        url=row[6]
    )


class Database:
    def __init__(self, config: Dict[str, Any]):
        # Open connection to database
        try:
            self._con = psycopg2.connect(
                host=config['db']['host'],
                port=config['db']['port'],
                user=config['db']['user'],
                password=config['db']['password'],
                database=config['db']['database']
            )
            self._cur = self._con.cursor()
        except Exception as e:
            raise RuntimeError(f'Error connecting to database: {e}')

        # Create tables if they don't exist yet
        try:
            # Table for users
            self._cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY NOT NULL,
                    username VARCHAR(255) NOT NULL,
                    discriminator VARCHAR(255) NOT NULL
                )
            ''')

            # Table for guilds
            self._cur.execute('''
                CREATE TABLE IF NOT EXISTS guilds (
                    id BIGINT PRIMARY KEY NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    manage_threads BOOLEAN NOT NULL DEFAULT FALSE
                )
            ''')

            # Table for excluded threads
            self._cur.execute('''
                CREATE TABLE IF NOT EXISTS excluded_threads (
                    thread_id BIGINT PRIMARY KEY NOT NULL,
                    guild_id BIGINT NOT NULL REFERENCES guilds(id) ON DELETE CASCADE
                )
            ''')

            # Table for user recommendations
            self._cur.execute('''
                CREATE TABLE IF NOT EXISTS user_recs (
                    id VARCHAR(255) PRIMARY KEY NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    recommendee BIGINT NOT NULL REFERENCES users(id),
                    recommender BIGINT NOT NULL REFERENCES users(id),
                    type VARCHAR(255) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    url VARCHAR(255) NOT NULL
                )
            ''')

            # Table for guild recommendations
            self._cur.execute('''
                CREATE TABLE IF NOT EXISTS guild_recs (
                    id VARCHAR(255) PRIMARY KEY NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    recommendee BIGINT NOT NULL REFERENCES guilds(id) ON DELETE CASCADE,
                    recommender BIGINT NOT NULL REFERENCES users(id),
                    type VARCHAR(255) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    url VARCHAR(255) NOT NULL
                )
            ''')

            # Table for Spotify authentication data
            self._cur.execute('''
                CREATE TABLE IF NOT EXISTS spotify_auth (
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    refresh_token VARCHAR(255) NOT NULL,
                    access_token VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    verifier VARCHAR(255),
                    state VARCHAR(255)
                )
            ''')
        except Exception as e:
            raise RuntimeError(f'Error creating tables: {e}')
        else:
            self._con.commit()
    
    def update_guild(self, guild_id: int, guild_name: str):
        """
        Insert new guild record, or update existing record if guild already exists
        """
        try:
            self._cur.execute('''
                INSERT INTO guilds (id, name)
                VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
            ''', (guild_id, guild_name))
        except Exception as e:
            raise RuntimeError(f'Error updating guild: {e}')
    
    def update_user(self, user_id: int, username: str, discriminator: str):
        """
        Insert new user record, or update existing record if user already exists
        """
        try:
            self._cur.execute('''
                INSERT INTO users (id, username, discriminator)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET username = EXCLUDED.username, discriminator = EXCLUDED.discriminator
            ''', (user_id, username, discriminator))
        except Exception as e:
            raise RuntimeError(f'Error updating user: {e}')
    
    def add_user_recommendation(self, user_id: int, recommendation: Recommendation):
        try:
            self._cur.execute('''
                INSERT INTO user_recs (id, timestamp, recommendee, recommender, type, title, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                recommendation.id,
                recommendation.timestamp,
                user_id,
                recommendation.recommender,
                recommendation.type.value,
                recommendation.title,
                recommendation.url
            ))
        except Exception as e:
            raise RuntimeError(f'Error adding user recommendation: {e}')
        else:
            self._con.commit()

    def get_user_recommendations(self, user_id: int) -> List[Recommendation]:
        try:
            self._cur.execute('''
                SELECT * FROM user_recs WHERE recommendee = %s
            ''', (user_id,))
            return [rec_enum_from_row(row) for row in self._cur.fetchall()]
        except Exception as e:
            raise RuntimeError(f'Error getting user recommendations: {e}')
    
    def remove_user_recommendation(self, user_id: str, recommendation_id: str):
        try:
            self._cur.execute('''
                DELETE FROM user_recs WHERE recommendee = %s AND id = %s
            ''', (user_id, recommendation_id))
        except Exception as e:
            raise RuntimeError(f'Error removing user recommendation: {e}')
        else:
            self._con.commit()
    
    def remove_all_user_recommendations(self, user_id: int):
        try:
            self._cur.execute('''
                DELETE FROM user_recs WHERE recommendee = %s
            ''', (user_id,))
        except Exception as e:
            raise RuntimeError(f'Error removing user recommendations: {e}')
        else:
            self._con.commit()

    def add_guild_recommendation(self, guild_id: int, recommendation: Recommendation):
        try:
            self._cur.execute('''
                INSERT INTO guild_recs (id, timestamp, recommendee, recommender, type, title, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                recommendation.id,
                recommendation.timestamp,
                guild_id,
                recommendation.recommender,
                recommendation.type.value,
                recommendation.title,
                recommendation.url
            ))
        except Exception as e:
            raise RuntimeError(f'Error adding guild recommendation: {e}')
        else:
            self._con.commit()
    
    def get_guild_recommendations(self, guild_id: int) -> List[Recommendation]:
        try:
            self._cur.execute('''
                SELECT * FROM guild_recs WHERE recommendee = %s
            ''', (guild_id,))
            return [rec_enum_from_row(row) for row in self._cur.fetchall()]
        except Exception as e:
            raise RuntimeError(f'Error getting guild recommendations: {e}')
    
    def remove_guild_recommendation(self, guild_id: str, recommendation_id: str):
        try:
            self._cur.execute('''
                DELETE FROM guild_recs WHERE recommendee = %s AND id = %s
            ''', (guild_id, recommendation_id))
        except Exception as e:
            raise RuntimeError(f'Error removing guild recommendation: {e}')
        else:
            self._con.commit()
    
    def remove_all_guild_recommendations(self, guild_id: int):
        try:
            self._cur.execute('''
                DELETE FROM guild_recs WHERE recommendee = %s
            ''', (guild_id,))
        except Exception as e:
            raise RuntimeError(f'Error removing guild recommendations: {e}')
        else:
            self._con.commit()
    
    def add_excluded_thread(self, guild_id: int, thread_id: int):
        try:
            self._cur.execute('''
                INSERT INTO excluded_threads (guild_id, thread_id)
                VALUES (%s, %s)
            ''', (guild_id, thread_id))
        except Exception as e:
            raise RuntimeError(f'Error adding excluded thread: {e}')
        else:
            self._con.commit()
    
    def check_excluded_thread(self, guild_id: int, thread_id: int) -> bool:
        try:
            self._cur.execute('''
                SELECT * FROM excluded_threads WHERE guild_id = %s AND thread_id = %s
            ''', (guild_id, thread_id))
            return self._cur.rowcount > 0
        except Exception as e:
            raise RuntimeError(f'Error checking excluded thread: {e}')

    def get_excluded_threads(self, guild_id: int) -> List[int]:
        try:
            self._cur.execute('''
                SELECT thread_id FROM excluded_threads WHERE guild_id = %s
            ''', (guild_id,))
            return [row[0] for row in self._cur.fetchall()]
        except Exception as e:
            raise RuntimeError(f'Error getting excluded threads: {e}')
    
    def remove_excluded_thread(self, guild_id: int, thread_id: int):
        try:
            self._cur.execute('''
                DELETE FROM excluded_threads WHERE guild_id = %s AND thread_id = %s
            ''', (guild_id, thread_id))
        except Exception as e:
            raise RuntimeError(f'Error removing excluded thread: {e}')
        else:
            self._con.commit()
    
    def get_thread_manage_status(self, guild_id: int) -> bool:
        try:
            self._cur.execute('''
                SELECT manage_threads FROM guilds WHERE id = %s
            ''', (guild_id,))
            return self._cur.fetchone()[0]
        except Exception as e:
            raise RuntimeError(f'Error checking if threads are managed for server: {e}')

    def set_thread_manage_status(self, guild_id: int, status: bool):
        try:
            self._cur.execute('''
                UPDATE guilds SET manage_threads = %s WHERE id = %s
            ''', (status, guild_id))
        except Exception as e:
            raise RuntimeError(f'Error setting thread manage status: {e}')
        else:
            self._con.commit()
    
    def get_thread_managed_guilds(self) -> List[int]:
        try:
            self._cur.execute('''
                SELECT id FROM guilds WHERE manage_threads = TRUE
            ''')
            return [row[0] for row in self._cur.fetchall()]
        except Exception as e:
            raise RuntimeError(f'Error getting thread-managed guilds: {e}')
    
    def get_user_spotify_creds(self, user_id: int) -> SpotifyCredentials:
        try:
            self._cur.execute('''
                SELECT user_id, refresh_token, access_token, expires_at
                FROM spotify_auth WHERE user_id = %s
            ''', (user_id,))
            return SpotifyCredentials(*self._cur.fetchone())
        except Exception as e:
            raise RuntimeError(f'Error getting user Spotify credentials: {e}')
    
    def set_user_spotify_creds(self, user_id: int, creds: SpotifyCredentials):
        try:
            self._cur.execute('''
                INSERT INTO spotify_auth (user_id, refresh_token, access_token, expires_at)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, creds.refresh_token, creds.access_token, creds.expires_at))
        except Exception as e:
            raise RuntimeError(f'Error setting user Spotify credentials: {e}')
        else:
            self._con.commit()
    
    def remove_user_spotify_creds(self, user_id: int):
        try:
            self._cur.execute('''
                DELETE FROM spotify_auth WHERE user_id = %s
            ''', (user_id,))
        except Exception as e:
            raise RuntimeError(f'Error removing user Spotify credentials: {e}')
        else:
            self._con.commit()
    
    def get_user_spotify_pkce(self, user_id: int) -> Tuple[str, str]:
        try:
            self._cur.execute('''
                SELECT verifier, state FROM spotify_auth WHERE user_id = %s
            ''', (user_id,))
            return self._cur.fetchone()
        except Exception as e:
            raise RuntimeError(f'Error getting user Spotify PKCE data: {e}')
    
    def set_user_spotify_pkce(self, user_id: int, verifier: str, state: str):
        try:
            self._cur.execute('''
                UPDATE spotify_auth SET verifier = %s, state = %s WHERE user_id = %s
            ''', (verifier, state, user_id))
        except Exception as e:
            raise RuntimeError(f'Error setting user Spotify PKCE data: {e}')
        else:
            self._con.commit()
