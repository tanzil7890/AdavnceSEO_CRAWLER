import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  Box,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  Timer as TimerIcon,
  Memory as MemoryIcon,
} from '@mui/icons-material';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
} from 'chart.js';
import axios from 'axios';
import DomainSubmission from '../components/DomainSubmission';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  ChartTooltip,
  Legend
);

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [crawlHistory, setCrawlHistory] = useState({
    labels: [],
    datasets: [],
  });
  const [domainStats, setDomainStats] = useState({
    labels: [],
    datasets: [],
  });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchData = async () => {
    try {
      setIsRefreshing(true);
      const [statsResponse, metricsResponse] = await Promise.all([
        axios.get('http://localhost:3001/api/stats'),
        axios.get('http://localhost:3001/api/metrics'),
      ]);

      setStats(statsResponse.data);

      // Process metrics for charts
      const crawlTimes = metricsResponse.data.crawl_times;
      const timestamps = Object.keys(crawlTimes).sort();
      const values = timestamps.map(t => crawlTimes[t]);

      // Format timestamps for display
      const formattedLabels = timestamps.map(t => {
        const date = new Date(t);
        return date.toLocaleTimeString();
      });

      setCrawlHistory({
        labels: formattedLabels,
        datasets: [
          {
            label: 'Pages Crawled',
            data: values,
            fill: false,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 5,
          },
        ],
      });

      // Process domain statistics
      const domains = statsResponse.data.domain_stats || [];
      setDomainStats({
        labels: domains.map(d => d.domain),
        datasets: [
          {
            label: 'Pages per Domain',
            data: domains.map(d => d.pages_count),
            backgroundColor: 'rgba(54, 162, 235, 0.5)',
            borderColor: 'rgb(54, 162, 235)',
            borderWidth: 1,
          },
        ],
      });

      setLastUpdated(new Date());
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const StatCard = ({ title, value, icon, color }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={1}>
          {icon}
          <Typography color="textSecondary" ml={1}>
            {title}
          </Typography>
        </Box>
        <Typography variant="h4" component="div">
          {value}
        </Typography>
      </CardContent>
    </Card>
  );

  const AnalyticsSection = () => (
    <>
      {/* Main Stats */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <StatCard
            title="Pages Crawled"
            value={stats?.pages_crawled || 0}
            icon={<SpeedIcon color="primary" />}
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatCard
            title="URLs Discovered"
            value={stats?.urls_discovered || 0}
            icon={<StorageIcon color="secondary" />}
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatCard
            title="Active Crawlers"
            value={stats?.active_crawlers || 0}
            icon={<MemoryIcon color="success" />}
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatCard
            title="Frontier Size"
            value={stats?.frontier_size || 0}
            icon={<TimerIcon color="warning" />}
          />
        </Grid>

        {/* Detailed Stats */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%', position: 'relative' }}>
            <Typography variant="h6" gutterBottom>
              Performance Metrics
            </Typography>
            <List>
              <ListItem>
                <ListItemText
                  primary="Average Crawl Time"
                  secondary={`${stats?.avg_crawl_time?.toFixed(2) || 0} seconds`}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Success Rate"
                  secondary={`${(stats?.success_rate * 100)?.toFixed(1) || 0}%`}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Failed Requests"
                  secondary={stats?.failed_requests || 0}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Average Content Size"
                  secondary={`${(stats?.avg_content_size / 1024)?.toFixed(2) || 0} KB`}
                />
              </ListItem>
            </List>
            {isRefreshing && (
              <CircularProgress
                size={24}
                sx={{
                  position: 'absolute',
                  top: '16px',
                  right: '16px',
                }}
              />
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%', position: 'relative' }}>
            <Typography variant="h6" gutterBottom>
              Queue Statistics
            </Typography>
            <List>
              <ListItem>
                <ListItemText
                  primary="Processing Queue Size"
                  secondary={stats?.processing_queue_size || 0}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Completed URLs"
                  secondary={stats?.completed_urls || 0}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Failed URLs"
                  secondary={stats?.failed_urls || 0}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Retry Queue Size"
                  secondary={stats?.retry_queue_size || 0}
                />
              </ListItem>
            </List>
            {isRefreshing && (
              <CircularProgress
                size={24}
                sx={{
                  position: 'absolute',
                  top: '16px',
                  right: '16px',
                }}
              />
            )}
          </Paper>
        </Grid>

        {/* Charts */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, position: 'relative' }}>
            <Typography variant="h6" gutterBottom>
              Crawl History
            </Typography>
            <Line
              data={crawlHistory}
              options={{
                responsive: true,
                plugins: {
                  legend: {
                    position: 'top',
                  },
                  title: {
                    display: true,
                    text: 'Pages Crawled Over Time',
                  },
                  tooltip: {
                    mode: 'index',
                    intersect: false,
                  },
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    title: {
                      display: true,
                      text: 'Number of Pages',
                    },
                  },
                  x: {
                    title: {
                      display: true,
                      text: 'Time',
                    },
                    ticks: {
                      maxRotation: 45,
                      minRotation: 45,
                    },
                  },
                },
                interaction: {
                  mode: 'nearest',
                  axis: 'x',
                  intersect: false,
                },
              }}
            />
            {isRefreshing && (
              <CircularProgress
                size={24}
                sx={{
                  position: 'absolute',
                  top: '16px',
                  right: '16px',
                }}
              />
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, position: 'relative' }}>
            <Typography variant="h6" gutterBottom>
              Top Domains
            </Typography>
            <Bar
              data={domainStats}
              options={{
                responsive: true,
                plugins: {
                  legend: {
                    position: 'top',
                  },
                },
                scales: {
                  y: {
                    beginAtZero: true,
                  },
                },
              }}
            />
            {isRefreshing && (
              <CircularProgress
                size={24}
                sx={{
                  position: 'absolute',
                  top: '16px',
                  right: '16px',
                }}
              />
            )}
          </Paper>
        </Grid>
      </Grid>
    </>
  );

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h4">Crawler Dashboard</Typography>
          <Box>
            <Typography variant="body2" color="textSecondary" display="inline" mr={2}>
              Last updated: {lastUpdated.toLocaleTimeString()}
            </Typography>
            <Tooltip title="Refresh Data">
              <IconButton 
                onClick={fetchData} 
                size="small"
                disabled={isRefreshing}
              >
                {isRefreshing ? <CircularProgress size={20} /> : <RefreshIcon />}
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </Grid>

      {/* Domain Submission */}
      <Grid item xs={12}>
        <DomainSubmission />
      </Grid>

      {/* Analytics Section */}
      <Grid item xs={12}>
        <AnalyticsSection />
      </Grid>
    </Grid>
  );
}

export default Dashboard; 