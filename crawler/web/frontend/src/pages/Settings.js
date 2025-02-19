import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Slider,
  Divider,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Save as SaveIcon } from '@mui/icons-material';
import axios from 'axios';

function Settings() {
  const [settings, setSettings] = useState({
    max_workers: 5,
    request_delay: 1.0,
    max_depth: 3,
    respect_robots: true,
    follow_links: true,
    max_retries: 3,
    timeout: 30,
    user_agent: 'Distributed Web Crawler',
    allowed_domains: '',
    excluded_patterns: '',
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [alert, setAlert] = useState(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get('http://localhost:8000/settings');
      setSettings(response.data);
    } catch (error) {
      console.error('Error fetching settings:', error);
      setAlert({
        severity: 'error',
        message: 'Failed to load settings. Please try again.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.post('http://localhost:8000/settings', settings);
      setAlert({
        severity: 'success',
        message: 'Settings saved successfully!',
      });
    } catch (error) {
      console.error('Error saving settings:', error);
      setAlert({
        severity: 'error',
        message: 'Failed to save settings. Please try again.',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setSettings((prev) => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <Grid container justifyContent="center">
        <CircularProgress />
      </Grid>
    );
  }

  return (
    <Grid container spacing={3}>
      {alert && (
        <Grid item xs={12}>
          <Alert severity={alert.severity} onClose={() => setAlert(null)}>
            {alert.message}
          </Alert>
        </Grid>
      )}

      <Grid item xs={12}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Crawler Configuration
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="User Agent"
                value={settings.user_agent}
                onChange={handleChange('user_agent')}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Max Workers"
                value={settings.max_workers}
                onChange={handleChange('max_workers')}
                inputProps={{ min: 1, max: 20 }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>Request Delay (seconds)</Typography>
              <Slider
                value={settings.request_delay}
                onChange={(_, value) => setSettings((prev) => ({ ...prev, request_delay: value }))}
                step={0.1}
                min={0.1}
                max={5}
                valueLabelDisplay="auto"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Max Depth"
                value={settings.max_depth}
                onChange={handleChange('max_depth')}
                inputProps={{ min: 1, max: 10 }}
              />
            </Grid>
          </Grid>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Crawling Rules
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.respect_robots}
                    onChange={handleChange('respect_robots')}
                  />
                }
                label="Respect robots.txt"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.follow_links}
                    onChange={handleChange('follow_links')}
                  />
                }
                label="Follow Links"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Allowed Domains (one per line)"
                value={settings.allowed_domains}
                onChange={handleChange('allowed_domains')}
                helperText="Leave empty to allow all domains"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Excluded Patterns (one per line)"
                value={settings.excluded_patterns}
                onChange={handleChange('excluded_patterns')}
                helperText="Regular expressions to exclude URLs"
              />
            </Grid>
          </Grid>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Network Settings
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Request Timeout (seconds)"
                value={settings.timeout}
                onChange={handleChange('timeout')}
                inputProps={{ min: 5, max: 120 }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Max Retries"
                value={settings.max_retries}
                onChange={handleChange('max_retries')}
                inputProps={{ min: 0, max: 5 }}
              />
            </Grid>
          </Grid>

          <Button
            variant="contained"
            color="primary"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={saving}
            sx={{ mt: 3 }}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </Paper>
      </Grid>
    </Grid>
  );
}

export default Settings; 