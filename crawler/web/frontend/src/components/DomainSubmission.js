import React, { useState, useEffect } from 'react';
import {
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Tooltip,
  Collapse,
  ListItemSecondaryAction,
  Divider,
  ListItemIcon,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Link as LinkIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import axios from 'axios';

const DomainSubmission = () => {
  const [domain, setDomain] = useState('');
  const [domains, setDomains] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [crawledLinks, setCrawledLinks] = useState({});
  const [expandedDomain, setExpandedDomain] = useState(null);
  const [domainStatuses, setDomainStatuses] = useState({});

  useEffect(() => {
    // Fetch domain statuses periodically
    const fetchStatuses = async () => {
      try {
        const response = await axios.get('http://localhost:3001/api/crawl/domains/status');
        const statusMap = {};
        response.data.forEach(domain => {
          statusMap[domain.domain] = domain;
        });
        setDomainStatuses(statusMap);
      } catch (error) {
        console.error('Error fetching domain statuses:', error);
      }
    };

    const interval = setInterval(fetchStatuses, 5000);
    return () => clearInterval(interval);
  }, []);

  const validateDomain = (domain) => {
    const pattern = /^([a-zA-Z0-9][a-zA-Z0-9-]*\.)+[a-zA-Z]{2,}$/;
    return pattern.test(domain);
  };

  const handleAddDomain = () => {
    if (!domain) return;
    
    if (!validateDomain(domain)) {
      setError('Please enter a valid domain name');
      return;
    }

    if (domains.includes(domain)) {
      setError('Domain already added to the list');
      return;
    }

    setDomains([...domains, domain]);
    setDomain('');
    setError(null);
  };

  const handleRemoveDomain = (index) => {
    const newDomains = domains.filter((_, i) => i !== index);
    setDomains(newDomains);
    const removedDomain = domains[index];
    if (crawledLinks[removedDomain]) {
      const newCrawledLinks = { ...crawledLinks };
      delete newCrawledLinks[removedDomain];
      setCrawledLinks(newCrawledLinks);
    }
  };

  const handleExpandDomain = (domain) => {
    setExpandedDomain(expandedDomain === domain ? null : domain);
    if (!crawledLinks[domain]) {
      fetchDomainLinks(domain);
    }
  };

  const fetchDomainLinks = async (domain) => {
    try {
      const response = await axios.get(`http://localhost:3001/api/search`, {
        params: {
          q: `domain:${domain}`,
          size: 100
        }
      });

      const links = response.data.hits.hits.map(hit => ({
        url: hit._source.url,
        title: hit._source.title || 'Untitled',
        crawled_at: new Date(hit._source.timestamp).toLocaleString()
      }));

      setCrawledLinks(prev => ({
        ...prev,
        [domain]: links
      }));
    } catch (error) {
      console.error(`Error fetching links for ${domain}:`, error);
    }
  };

  const handleStopCrawler = async (domain) => {
    try {
      await axios.post(`http://localhost:3001/api/crawl/domains/${domain}/stop`);
      setSuccess(`Stopped crawler for ${domain}`);
    } catch (error) {
      setError(`Failed to stop crawler for ${domain}`);
    }
  };

  const handleSubmit = async () => {
    if (domains.length === 0) {
      setError('Please add at least one domain');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await axios.post('http://localhost:3001/api/crawl/domains', {
        domains: domains
      });

      setSuccess(response.data.message || 'Domains submitted successfully for crawling!');

      // Start polling for updates
      domains.forEach(domain => {
        fetchDomainLinks(domain);
      });

    } catch (error) {
      console.error('Error submitting domains:', error);
      setError(error.response?.data?.error || 'Failed to submit domains. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getDomainStatus = (domain) => {
    const status = domainStatuses[domain];
    if (!status) return 'Waiting to start...';
    
    if (status.is_active) {
      return `Active - ${status.pages_found || 0} pages found`;
    }
    
    if (status.status === 'completed') {
      return `Completed - ${status.pages_found || 0} pages found`;
    }
    
    return `${status.status} - ${status.pages_found || 0} pages found`;
  };

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Add Domains to Crawl
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            fullWidth
            label="Domain Name"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="example.com"
            disabled={loading}
            onKeyPress={(e) => e.key === 'Enter' && handleAddDomain()}
            error={Boolean(error)}
            helperText={error}
          />
          <Tooltip title="Add Domain">
            <IconButton
              onClick={handleAddDomain}
              disabled={!domain || loading}
              color="primary"
            >
              <AddIcon />
            </IconButton>
          </Tooltip>
        </Box>

        {domains.length > 0 && (
          <List>
            {domains.map((domain, index) => (
              <React.Fragment key={domain}>
                <ListItem>
                  <ListItemText 
                    primary={domain}
                    secondary={getDomainStatus(domain)}
                  />
                  <ListItemSecondaryAction>
                    {domainStatuses[domain]?.is_active && (
                      <IconButton
                        edge="end"
                        onClick={() => handleStopCrawler(domain)}
                        color="error"
                      >
                        <StopIcon />
                      </IconButton>
                    )}
                    <IconButton
                      edge="end"
                      onClick={() => handleRemoveDomain(index)}
                      disabled={loading || domainStatuses[domain]?.is_active}
                    >
                      <DeleteIcon />
                    </IconButton>
                    {crawledLinks[domain] && crawledLinks[domain].length > 0 && (
                      <IconButton
                        edge="end"
                        onClick={() => handleExpandDomain(domain)}
                      >
                        {expandedDomain === domain ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    )}
                  </ListItemSecondaryAction>
                </ListItem>
                <Collapse in={expandedDomain === domain} timeout="auto" unmountOnExit>
                  <List component="div" disablePadding sx={{ 
                    ml: 4, 
                    maxHeight: '200px', 
                    overflowY: 'auto',
                    bgcolor: 'background.paper',
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'divider'
                  }}>
                    {crawledLinks[domain]?.map((link, i) => (
                      <ListItem key={i} dense>
                        <ListItemIcon>
                          <LinkIcon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={link.title}
                          secondary={
                            <>
                              <Typography component="span" variant="body2" color="text.secondary">
                                {link.url}
                              </Typography>
                              <br />
                              <Typography component="span" variant="caption" color="text.secondary">
                                Crawled: {link.crawled_at}
                              </Typography>
                            </>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                </Collapse>
                <Divider />
              </React.Fragment>
            ))}
          </List>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleSubmit}
        disabled={domains.length === 0 || loading}
        startIcon={loading ? <CircularProgress size={20} /> : <StartIcon />}
        fullWidth
      >
        {loading ? 'Submitting...' : 'Start Crawling'}
      </Button>
    </Paper>
  );
};

export default DomainSubmission; 