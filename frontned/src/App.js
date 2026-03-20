// frontend/src/App.js
import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const API_GATEWAY = 'http://localhost:5000';

function URLShortener() {
  const [url, setUrl] = useState('');
  const [customCode, setCustomCode] = useState('');
  const [shortUrl, setShortUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await axios.post(`${API_GATEWAY}/api/shorten`, {
        url,
        custom_code: customCode || undefined
      });
      
      setShortUrl(response.data.short_url);
    } catch (err) {
      setError(err.response?.data?.error || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(shortUrl);
    alert('Copied to clipboard!');
  };

  return (
    <div className="container">
      <h1>🔗 URL Shortener</h1>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <input
            type="url"
            placeholder="Enter your long URL here..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
        </div>
        
        <div className="form-group">
          <input
            type="text"
            placeholder="Custom code (optional)"
            value={customCode}
            onChange={(e) => setCustomCode(e.target.value)}
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Shortening...' : 'Shorten URL'}
        </button>
      </form>
      
      {error && <div className="error">{error}</div>}
      
      {shortUrl && (
        <div className="result">
          <h3>Your shortened URL:</h3>
          <div className="short-url">
            <a href={shortUrl} target="_blank" rel="noopener noreferrer">
              {shortUrl}
            </a>
            <button onClick={copyToClipboard}>Copy</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default URLShortener;
