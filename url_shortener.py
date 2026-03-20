# url_shortener.py
import hashlib
import sqlite3
import json
from datetime import datetime
from flask import Flask, request, redirect, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class URLShortener:
    def __init__(self, db_path='urls.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_table()
    
    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                clicks INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()
    
    def generate_short_code(self, url, length=6):
        """Generate a short code from URL"""
        hash_obj = hashlib.md5(url.encode())
        hash_hex = hash_obj.hexdigest()
        # Convert hex to base62 for shorter codes
        base62_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        decimal = int(hash_hex[:8], 16)
        code = ""
        while decimal > 0 and len(code) < length:
            code = base62_chars[decimal % 62] + code
            decimal //= 62
        return code.zfill(length)
    
    def shorten_url(self, original_url, custom_code=None):
        """Create a shortened URL"""
        if custom_code:
            short_code = custom_code
            # Check if custom code exists
            self.cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
            if self.cursor.fetchone():
                return None, "Custom code already exists"
        else:
            short_code = self.generate_short_code(original_url)
        
        self.cursor.execute(
            "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
            (short_code, original_url)
        )
        self.conn.commit()
        return short_code, None
    
    def get_original_url(self, short_code):
        """Retrieve original URL and increment click count"""
        self.cursor.execute(
            "UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?",
            (short_code,)
        )
        self.cursor.execute(
            "SELECT original_url FROM urls WHERE short_code = ?",
            (short_code,)
        )
        result = self.cursor.fetchone()
        self.conn.commit()
        return result[0] if result else None
    
    def get_stats(self, short_code):
        """Get statistics for a short URL"""
        self.cursor.execute(
            "SELECT original_url, clicks, created_at FROM urls WHERE short_code = ?",
            (short_code,)
        )
        result = self.cursor.fetchone()
        if result:
            return {
                'short_code': short_code,
                'original_url': result[0],
                'clicks': result[1],
                'created_at': result[2]
            }
        return None

# Flask Routes
shortener = URLShortener()

@app.route('/shorten', methods=['POST'])
def shorten():
    data = request.get_json()
    url = data.get('url')
    custom = data.get('custom_code')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    short_code, error = shortener.shorten_url(url, custom)
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'short_url': f"http://localhost:5000/{short_code}",
        'short_code': short_code
    })

@app.route('/<short_code>')
def redirect_to_url(short_code):
    original_url = shortener.get_original_url(short_code)
    if original_url:
        return redirect(original_url)
    return jsonify({'error': 'URL not found'}), 404

@app.route('/stats/<short_code>')
def get_stats(short_code):
    stats = shortener.get_stats(short_code)
    if stats:
        return jsonify(stats)
    return jsonify({'error': 'URL not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
