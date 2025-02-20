import React from 'react';
import { Container, Typography, Paper } from '@mui/material';
import Search from '../components/Search';

const SearchPage = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3, display: 'flex', flexDirection: 'column' }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Search Crawled Pages
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Search through all crawled web pages with real-time results from Elasticsearch.
        </Typography>
        <Search />
      </Paper>
    </Container>
  );
};

export default SearchPage; 