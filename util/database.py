from dataclass.recommendation import Recommendation
from typing import Any, Dict, List
from uuid6 import uuid7
import psycopg2


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
                    manage_threads BOOLEAN NOT NULL DEFAULT FALSE,
                    excluded_threads BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[] 
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
                    recommendee BIGINT NOT NULL REFERENCES guilds(id),
                    recommender BIGINT NOT NULL REFERENCES users(id),
                    type VARCHAR(255) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    url VARCHAR(255) NOT NULL
                )
            ''')

            # Table for Spotify authentication data
            self._cur.execute('''
                CREATE TABLE IF NOT EXISTS spotify_auth (
                    user_id BIGINT NOT NULL REFERENCES users(id),
                    refresh_token VARCHAR(255) NOT NULL,
                    access_token VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            ''')
        except Exception as e:
            raise RuntimeError(f'Error creating tables: {e}')
        else:
            self._con.commit()
    
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
            return [Recommendation(**row) for row in self._cur.fetchall()]
        except Exception as e:
            raise RuntimeError(f'Error getting user recommendations: {e}')

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
            return [Recommendation(**row) for row in self._cur.fetchall()]
        except Exception as e:
            raise RuntimeError(f'Error getting guild recommendations: {e}')
