import React, { useState } from 'react';
import {
  Grid,
  Paper,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  CardActions,
  CircularProgress,
  Chip,
  Box,
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import axios from 'axios';

function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/search', {
        query: query,
        size: 20,
      });
      setResults(response.data);
    } catch (error) {
      console.error('Error searching:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Paper sx={{ p: 2 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs>
              <TextField
                fullWidth
                label="Search crawled content"
                variant="outlined"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
              />
            </Grid>
            <Grid item>
              <Button
                variant="contained"
                startIcon={<SearchIcon />}
                onClick={handleSearch}
                disabled={loading}
              >
                Search
              </Button>
            </Grid>
          </Grid>
        </Paper>
      </Grid>

      {loading ? (
        <Grid item xs={12} container justifyContent="center">
          <CircularProgress />
        </Grid>
      ) : (
        results.map((result, index) => (
          <Grid item xs={12} key={index}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="h2" gutterBottom>
                  {result.title || 'Untitled'}
                </Typography>
                <Typography color="textSecondary" gutterBottom>
                  {result.url}
                </Typography>
                <Typography variant="body2" paragraph>
                  {result.description || result.text_content?.slice(0, 200) + '...'}
                </Typography>
                <Box sx={{ mb: 1 }}>
                  {result.keywords?.slice(0, 5).map((keyword, idx) => (
                    <Chip
                      key={idx}
                      label={keyword}
                      size="small"
                      sx={{ mr: 0.5, mb: 0.5 }}
                    />
                  ))}
                </Box>
                <Typography variant="caption" color="textSecondary">
                  Crawled: {new Date(result.timestamp).toLocaleString()}
                </Typography>
              </CardContent>
              <CardActions>
                <Button size="small" href={result.url} target="_blank">
                  Visit Page
                </Button>
                <Button
                  size="small"
                  onClick={() => window.open(`/page/${result.url_hash}`, '_blank')}
                >
                  View Details
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))
      )}

      {!loading && results.length === 0 && query && (
        <Grid item xs={12}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="body1" color="textSecondary">
              No results found for "{query}"
            </Typography>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
}

export default Search; 