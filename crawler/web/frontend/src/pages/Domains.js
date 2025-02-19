import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import axios from 'axios';

function Domains() {
  const [domains, setDomains] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDomain, setSelectedDomain] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const columns = [
    { field: 'domain', headerName: 'Domain', width: 200 },
    { field: 'pages_crawled', headerName: 'Pages Crawled', width: 150 },
    { field: 'queue_size', headerName: 'Queue Size', width: 130 },
    { field: 'avg_crawl_time', headerName: 'Avg. Crawl Time (s)', width: 180 },
    { field: 'success_rate', headerName: 'Success Rate (%)', width: 150 },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 200,
      renderCell: (params) => (
        <Button
          variant="contained"
          size="small"
          onClick={() => handleViewDetails(params.row.domain)}
        >
          View Details
        </Button>
      ),
    },
  ];

  useEffect(() => {
    fetchDomains();
    const interval = setInterval(fetchDomains, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchDomains = async () => {
    try {
      const response = await axios.get('http://localhost:8000/domains');
      const domainsData = response.data.map((domain, index) => ({
        id: index,
        ...domain,
        success_rate: ((domain.success_count / domain.total_count) * 100).toFixed(2),
      }));
      setDomains(domainsData);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching domains:', error);
      setLoading(false);
    }
  };

  const handleViewDetails = async (domain) => {
    try {
      const response = await axios.get(`http://localhost:8000/domain/${domain}/stats`);
      setSelectedDomain(response.data);
      setDetailsOpen(true);
    } catch (error) {
      console.error('Error fetching domain details:', error);
    }
  };

  const DomainDetails = () => {
    if (!selectedDomain) return null;

    return (
      <Dialog
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{selectedDomain.domain} Statistics</DialogTitle>
        <DialogContent>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Typography variant="h6">Content Types</Typography>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Type</TableCell>
                      <TableCell align="right">Count</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {selectedDomain.content_types.map((type) => (
                      <TableRow key={type.key}>
                        <TableCell>{type.key}</TableCell>
                        <TableCell align="right">{type.doc_count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="h6">Performance Metrics</Typography>
              <Typography>
                Average Content Length: {selectedDomain.avg_content_length.value.toFixed(2)} bytes
              </Typography>
              <Typography>
                Average Crawl Time: {selectedDomain.avg_crawl_time.value.toFixed(2)} seconds
              </Typography>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  };

  if (loading) {
    return (
      <Grid container justifyContent="center" alignItems="center" style={{ height: '100vh' }}>
        <CircularProgress />
      </Grid>
    );
  }

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Domain Statistics
          </Typography>
          <div style={{ height: 400, width: '100%' }}>
            <DataGrid
              rows={domains}
              columns={columns}
              pageSize={5}
              rowsPerPageOptions={[5]}
              checkboxSelection
              disableSelectionOnClick
            />
          </div>
        </Paper>
      </Grid>
      <DomainDetails />
    </Grid>
  );
}

export default Domains; 