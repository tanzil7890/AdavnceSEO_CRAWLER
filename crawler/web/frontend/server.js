const express = require('express');
const cors = require('cors');
const axios = require('axios');
const { spawn } = require('child_process');
require('dotenv').config();

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// Track active crawlers
const activeCrawlers = new Map();

// Initialize Elasticsearch indices
async function initializeElasticsearch() {
  try {
    // Create web_pages index if it doesn't exist
    await axios.put('http://localhost:9200/web_pages', {
      mappings: {
        properties: {
          url: { type: 'keyword' },
          domain: { type: 'keyword' },
          title: { type: 'text' },
          content: { type: 'text' },
          timestamp: { type: 'date' },
          status: { type: 'keyword' }
        }
      }
    }, {
      auth: {
        username: 'elastic',
        password: 'changeme'
      }
    }).catch(err => {
      if (err.response?.status !== 400) throw err; // 400 means index already exists
    });

    // Create crawler_domains index if it doesn't exist
    await axios.put('http://localhost:9200/crawler_domains', {
      mappings: {
        properties: {
          domain: { type: 'keyword' },
          status: { type: 'keyword' },
          added_at: { type: 'date' },
          last_crawled: { type: 'date' },
          pages_found: { type: 'integer' },
          crawl_status: {
            properties: {
              success: { type: 'integer' },
              failed: { type: 'integer' },
              in_progress: { type: 'integer' }
            }
          }
        }
      }
    }, {
      auth: {
        username: 'elastic',
        password: 'changeme'
      }
    }).catch(err => {
      if (err.response?.status !== 400) throw err;
    });

    console.log('Elasticsearch indices initialized');
  } catch (error) {
    console.error('Error initializing Elasticsearch:', error);
  }
}

// Initialize on startup
initializeElasticsearch();

// Helper function to start crawler for a domain
function startCrawler(domain) {
  if (activeCrawlers.has(domain)) {
    return; // Crawler already running for this domain
  }

  // Start the Python crawler process
  const crawler = spawn('python', [
    '-m', 'crawler.main',
    '--seed-urls', 'data/seed_urls.json',
    '--domain', domain
  ]);

  activeCrawlers.set(domain, crawler);

  crawler.stdout.on('data', (data) => {
    console.log(`Crawler output for ${domain}:`, data.toString());
  });

  crawler.stderr.on('data', (data) => {
    console.error(`Crawler error for ${domain}:`, data.toString());
  });

  crawler.on('close', (code) => {
    console.log(`Crawler for ${domain} exited with code ${code}`);
    activeCrawlers.delete(domain);
  });
}

// Elasticsearch proxy endpoint
app.get('/api/search', async (req, res) => {
  try {
    const { q, size = 20 } = req.query;
    
    let searchQuery = {
      size: size,
      sort: [{ timestamp: 'desc' }]
    };

    if (q.startsWith('domain:')) {
      const domain = q.replace('domain:', '');
      searchQuery.query = {
        term: {
          'domain.keyword': domain
        }
      };
    } else {
      searchQuery.query = {
        multi_match: {
          query: q,
          fields: ['title^3', 'content^2', 'url']
        }
      };
    }

    const response = await axios.post(
      'http://localhost:9200/web_pages/_search',
      searchQuery,
      {
        auth: {
          username: 'elastic',
          password: 'changeme'
        }
      }
    );

    res.json(response.data);
  } catch (error) {
    console.error('Elasticsearch error:', error);
    res.status(500).json({ 
      error: 'Failed to fetch search results',
      details: error.message 
    });
  }
});

// Get crawler statistics
app.get('/api/stats', async (req, res) => {
  try {
    // Get Elasticsearch stats
    const esStats = await axios.get(`http://localhost:9200/web_pages/_stats`, {
      auth: {
        username: 'elastic',
        password: 'changeme'
      }
    });

    // Get domain statistics
    const domainStats = await axios.get(`http://localhost:9200/web_pages/_search`, {
      auth: {
        username: 'elastic',
        password: 'changeme'
      },
      data: {
        size: 0,
        aggs: {
          domains: {
            terms: {
              field: 'domain.keyword',
              size: 10
            },
            aggs: {
              avg_crawl_time: { avg: { field: 'crawl_time' } },
              avg_content_size: { avg: { field: 'content_length' } }
            }
          }
        }
      }
    });

    // Calculate statistics
    const stats = {
      pages_crawled: esStats.data._all.total.docs.count,
      urls_discovered: esStats.data._all.total.docs.count + 1000, // Including queued URLs
      active_crawlers: 5, // Example value
      frontier_size: 1000, // Example value
      avg_crawl_time: 2.5, // Example value in seconds
      success_rate: 0.95, // Example value
      failed_requests: 50, // Example value
      avg_content_size: 15000, // Example value in bytes
      processing_queue_size: 100, // Example value
      completed_urls: esStats.data._all.total.docs.count,
      failed_urls: 50, // Example value
      retry_queue_size: 20, // Example value
      domain_stats: domainStats.data.aggregations.domains.buckets.map(bucket => ({
        domain: bucket.key,
        pages_count: bucket.doc_count,
        avg_crawl_time: bucket.avg_crawl_time.value,
        avg_content_size: bucket.avg_content_size.value
      }))
    };

    res.json(stats);
  } catch (error) {
    console.error('Stats error:', error);
    res.status(500).json({
      error: 'Failed to fetch statistics',
      details: error.message
    });
  }
});

// Get metrics for charts
app.get('/api/metrics', async (req, res) => {
  try {
    // Generate sample time-series data for the last 24 hours
    const metrics = {
      crawl_times: {}
    };

    const now = new Date();
    for (let i = 24; i >= 0; i--) {
      const time = new Date(now - i * 3600000); // Go back i hours
      const timeStr = time.toISOString();
      // Generate random count between 50-200 for demo
      metrics.crawl_times[timeStr] = Math.floor(Math.random() * 150) + 50;
    }

    // Add some sample real-time data
    const realtimeResponse = await axios.get(`http://localhost:9200/web_pages/_count`, {
      auth: {
        username: 'elastic',
        password: 'changeme'
      }
    }).catch(() => ({ data: { count: 0 } }));

    metrics.crawl_times[new Date().toISOString()] = realtimeResponse.data.count;

    res.json(metrics);
  } catch (error) {
    console.error('Metrics error:', error);
    res.status(500).json({
      error: 'Failed to fetch metrics',
      details: error.message
    });
  }
});

// Add domains to crawl
app.post('/api/crawl/domains', async (req, res) => {
  try {
    const { domains } = req.body;

    if (!domains || !Array.isArray(domains) || domains.length === 0) {
      return res.status(400).json({
        error: 'Please provide a valid list of domains'
      });
    }

    // Check Elasticsearch connection first
    try {
      await axios.get('http://localhost:9200', {
        auth: {
          username: 'elastic',
          password: 'changeme'
        }
      });
    } catch (error) {
      throw new Error('Cannot connect to Elasticsearch. Please ensure it is running.');
    }

    // Add domains to Elasticsearch for tracking
    const bulkBody = domains.flatMap(domain => [
      { index: { _index: 'crawler_domains' } },
      {
        domain: domain,
        status: 'pending',
        added_at: new Date().toISOString(),
        last_crawled: null,
        pages_found: 0,
        crawl_status: {
          success: 0,
          failed: 0,
          in_progress: 0
        }
      }
    ]);

    await axios.post(
      'http://localhost:9200/_bulk',
      bulkBody.map(item => JSON.stringify(item)).join('\n') + '\n',
      {
        auth: {
          username: 'elastic',
          password: 'changeme'
        },
        headers: {
          'Content-Type': 'application/x-ndjson'
        }
      }
    );

    // Start crawlers for each domain
    for (const domain of domains) {
      startCrawler(domain);
    }

    // Update seed_urls.json
    const fs = require('fs');
    const seedUrls = domains.map(domain => `https://${domain}`);
    fs.writeFileSync('data/seed_urls.json', JSON.stringify(seedUrls, null, 2));

    res.json({
      message: 'Domains added successfully',
      domains: domains
    });
  } catch (error) {
    console.error('Error adding domains:', error);
    res.status(500).json({
      error: error.message || 'Failed to add domains. Please try again.'
    });
  }
});

// Get domain crawl status
app.get('/api/crawl/domains/status', async (req, res) => {
  try {
    const response = await axios.get(
      'http://localhost:9200/crawler_domains/_search',
      {
        auth: {
          username: 'elastic',
          password: 'changeme'
        },
        data: {
          size: 100,
          sort: [{ added_at: 'desc' }]
        }
      }
    );

    const domains = response.data.hits.hits.map(hit => ({
      domain: hit._source.domain,
      status: hit._source.status,
      added_at: hit._source.added_at,
      last_crawled: hit._source.last_crawled,
      pages_found: hit._source.pages_found,
      crawl_status: hit._source.crawl_status,
      is_active: activeCrawlers.has(hit._source.domain)
    }));

    res.json(domains);
  } catch (error) {
    console.error('Error fetching domain status:', error);
    res.status(500).json({
      error: 'Failed to fetch domain status',
      details: error.message
    });
  }
});

// Stop crawler for a domain
app.post('/api/crawl/domains/:domain/stop', async (req, res) => {
  const { domain } = req.params;
  
  if (activeCrawlers.has(domain)) {
    const crawler = activeCrawlers.get(domain);
    crawler.kill();
    activeCrawlers.delete(domain);
    res.json({ message: `Crawler stopped for domain: ${domain}` });
  } else {
    res.status(404).json({ error: `No active crawler found for domain: ${domain}` });
  }
});

app.listen(port, () => {
  console.log(`Search API server running on port ${port}`);
}); 