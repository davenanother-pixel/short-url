# gateway/app.py
from flask import Flask, request, jsonify, redirect
import requests
import redis
import json
from functools import wraps

app = Flask(__name__)

# Service URLs
SHORTENER_SERVICE = "http://localhost:8081"
ANALYTICS_SERVICE = "http://localhost:8082"
STORAGE_SERVICE = "http://localhost:8083"

# Redis for rate limiting
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def rate_limit(limit=100, window=3600):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            key = f"rate_limit:{client_ip}"
            current = redis_client.get(key)
            
            if current and int(current) >= limit:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            pipe.execute()
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/api/shorten', methods=['POST'])
@rate_limit(limit=10, window=60)  # 10 requests per minute
def shorten_url():
    """API Gateway endpoint for URL shortening"""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400
    
    # Forward to C++ shortener service
    try:
        response = requests.post(
            f"{SHORTENER_SERVICE}/generate",
            json={
                'url': data['url'],
                'custom_code': data.get('custom_code')
            },
            timeout=2
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Store in database via storage service
            requests.post(
                f"{STORAGE_SERVICE}/store",
                json={
                    'short_code': result['short_code'],
                    'original_url': data['url']
                }
            )
            
            # Log analytics via Java service (async)
            requests.post(
                f"{ANALYTICS_SERVICE}/log",
                json={
                    'short_code': result['short_code'],
                    'ip': request.remote_addr,
                    'user_agent': request.user_agent.string
                }
            )
            
            return jsonify({
                'short_url': f"http://localhost:5000/{result['short_code']}",
                'short_code': result['short_code']
            })
        else:
            return jsonify(response.json()), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Service timeout'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<short_code>')
def redirect_to_url(short_code):
    """Redirect endpoint"""
    try:
        # Get original URL from storage service
        response = requests.get(
            f"{STORAGE_SERVICE}/get/{short_code}",
            timeout=1
        )
        
        if response.status_code == 200:
            original_url = response.json()['original_url']
            
            # Log click to analytics (async)
            requests.post(
                f"{ANALYTICS_SERVICE}/click",
                json={
                    'short_code': short_code,
                    'ip': request.remote_addr,
                    'referer': request.referrer
                }
            )
            
            return redirect(original_url)
        else:
            return jsonify({'error': 'URL not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/<short_code>')
def get_stats(short_code):
    """Get statistics for a short URL"""
    try:
        response = requests.get(
            f"{ANALYTICS_SERVICE}/stats/{short_code}",
            timeout=2
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Stats not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
