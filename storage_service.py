# storage_service.py
from flask import Flask, request, jsonify
import psycopg2
import redis
import json
from datetime import datetime

app = Flask(__name__)

# Database connections
pg_conn = psycopg2.connect(
    host="localhost",
    database="url_shortener",
    user="postgres",
    password="password"
)
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Initialize database
def init_db():
    with pg_conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id SERIAL PRIMARY KEY,
                short_code VARCHAR(10) UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_short_code 
            ON urls(short_code)
        """)
        
        pg_conn.commit()

init_db()

@app.route('/store', methods=['POST'])
def store_url():
    """Store URL mapping in database"""
    data = request.get_json()
    short_code = data['short_code']
    original_url = data['original_url']
    
    try:
        with pg_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO urls (short_code, original_url)
                VALUES (%s, %s)
            """, (short_code, original_url))
            pg_conn.commit()
            
            # Cache in Redis for fast access
            redis_client.setex(
                f"url:{short_code}",
                3600,  # 1 hour cache
                original_url
            )
            
            return jsonify({'status': 'stored'}), 200
            
    except psycopg2.IntegrityError:
        return jsonify({'error': 'Short code already exists'}), 409

@app.route('/get/<short_code>')
def get_url(short_code):
    """Get original URL with Redis cache"""
    
    # Check Redis cache first
    cached_url = redis_client.get(f"url:{short_code}")
    if cached_url:
        return jsonify({
            'original_url': cached_url,
            'source': 'cache'
        })
    
    # Fallback to PostgreSQL
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT original_url, is_active 
            FROM urls 
            WHERE short_code = %s
        """, (short_code,))
        
        result = cur.fetchone()
        if result and result[1]:  # if active
            original_url = result[0]
            # Update cache
            redis_client.setex(f"url:{short_code}", 3600, original_url)
            return jsonify({
                'original_url': original_url,
                'source': 'database'
            })
        else:
            return jsonify({'error': 'URL not found'}), 404

@app.route('/update', methods=['PUT'])
def update_url():
    """Update URL mapping"""
    data = request.get_json()
    short_code = data['short_code']
    new_url = data['new_url']
    
    with pg_conn.cursor() as cur:
        cur.execute("""
            UPDATE urls 
            SET original_url = %s 
            WHERE short_code = %s
        """, (new_url, short_code))
        pg_conn.commit()
        
        # Update cache
        redis_client.setex(f"url:{short_code}", 3600, new_url)
        
        return jsonify({'status': 'updated'})

@app.route('/delete/<short_code>', methods=['DELETE'])
def delete_url(short_code):
    """Soft delete URL"""
    with pg_conn.cursor() as cur:
        cur.execute("""
            UPDATE urls 
            SET is_active = FALSE 
            WHERE short_code = %s
        """, (short_code,))
        pg_conn.commit()
        
        # Remove from cache
        redis_client.delete(f"url:{short_code}")
        
        return jsonify({'status': 'deleted'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8083, debug=True)
