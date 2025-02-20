import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Search.css';

const Search = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResults = async () => {
      if (!query.trim()) {
        setResults([]);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await axios.get(`http://localhost:3001/api/search`, {
          params: {
            q: query
          }
        });

        const hits = response.data.hits.hits;
        setResults(hits.map(hit => ({
          id: hit._id,
          score: hit._score,
          ...hit._source
        })));
      } catch (err) {
        setError('Failed to fetch search results. Please try again.');
        console.error('Search error:', err);
      } finally {
        setLoading(false);
      }
    };

    // Debounce search requests
    const timeoutId = setTimeout(fetchResults, 300);
    return () => clearTimeout(timeoutId);
  }, [query]);

  return (
    <div className="search-container">
      <div className="search-input-wrapper">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search web pages..."
          className="search-input"
        />
        {loading && <div className="search-spinner"></div>}
      </div>

      {error && (
        <div className="search-error">
          {error}
        </div>
      )}

      <div className="search-results">
        {results.map((result) => (
          <div key={result.id} className="search-result-item">
            <h3>{result.title || 'Untitled'}</h3>
            <p className="result-url">{result.url}</p>
            <p className="result-content">{result.content?.substring(0, 200)}...</p>
            <div className="result-metadata">
              <span>Score: {result.score?.toFixed(2)}</span>
              <span>Crawled: {new Date(result.timestamp).toLocaleString()}</span>
            </div>
          </div>
        ))}
        
        {results.length === 0 && query && !loading && (
          <div className="no-results">
            No results found for "{query}"
          </div>
        )}
      </div>
    </div>
  );
};

export default Search; 