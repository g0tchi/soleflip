import { useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { 
  Database as DatabaseIcon, 
  Terminal, 
  Play, 
  Download,
  AlertTriangle,
  CheckCircle 
} from 'lucide-react';

interface QueryResult {
  [key: string]: any;
}

const Database = () => {
  const [query, setQuery] = useState('SELECT * FROM inventory_items LIMIT 10;');
  const [results, setResults] = useState<QueryResult[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);

  const executeQuery = async () => {
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setIsExecuting(true);
    setError(null);
    setResults([]);
    const startTime = Date.now();
    
    try {
      const data = await invoke<QueryResult[]>('run_database_query', {
        query: query.trim()
      });
      
      setResults(data);
      setExecutionTime(Date.now() - startTime);
    } catch (err) {
      setError(err as string);
      console.error('Query failed:', err);
    } finally {
      setIsExecuting(false);
    }
  };

  const exportResults = () => {
    if (results.length === 0) return;
    
    // Convert results to CSV
    const headers = Object.keys(results[0]);
    const csvContent = [
      headers.join(','),
      ...results.map(row => 
        headers.map(header => {
          const value = row[header];
          return typeof value === 'string' && value.includes(',') 
            ? `"${value}"` 
            : value;
        }).join(',')
      )
    ].join('\n');
    
    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const sampleQueries = [
    {
      name: 'Top 10 Most Valuable Items',
      query: 'SELECT sku, name, brand, current_value FROM inventory_items ORDER BY current_value DESC LIMIT 10;'
    },
    {
      name: 'Brand Performance',
      query: 'SELECT brand, COUNT(*) as items, AVG(current_value) as avg_value FROM inventory_items GROUP BY brand ORDER BY items DESC;'
    },
    {
      name: 'Recent Transactions',
      query: 'SELECT * FROM transactions WHERE created_at >= NOW() - INTERVAL \'30 days\' ORDER BY created_at DESC LIMIT 20;'
    },
    {
      name: 'Inventory Summary',
      query: 'SELECT status, COUNT(*) as count, SUM(current_value) as total_value FROM inventory_items GROUP BY status;'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-retro font-bold text-retro-cyan animate-glow">
          DATABASE
        </h1>
        <p className="text-retro-cyan/70 font-mono mt-1">
          Execute SQL queries and manage database
        </p>
      </div>

      {/* Security Warning */}
      <div className="retro-card border-retro-yellow">
        <div className="flex items-center space-x-3 mb-2">
          <AlertTriangle className="w-6 h-6 text-retro-yellow" />
          <h3 className="text-lg font-retro text-retro-yellow">SECURITY NOTICE</h3>
        </div>
        <p className="text-sm text-retro-yellow/80 font-mono">
          Only SELECT queries are allowed for security reasons. 
          Write operations must be performed through the API.
        </p>
      </div>

      {/* Query Interface */}
      <div className="retro-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <Terminal className="w-6 h-6 text-retro-cyan" />
            <h2 className="text-xl font-retro text-retro-cyan">SQL QUERY INTERFACE</h2>
          </div>
          <div className="flex items-center space-x-2">
            {results.length > 0 && (
              <button
                onClick={exportResults}
                className="retro-button-success flex items-center space-x-2"
              >
                <Download className="w-4 h-4" />
                <span>EXPORT</span>
              </button>
            )}
            <button
              onClick={executeQuery}
              disabled={isExecuting || !query.trim()}
              className="retro-button flex items-center space-x-2 disabled:opacity-50"
            >
              {isExecuting ? (
                <DatabaseIcon className="w-4 h-4 animate-pulse" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>{isExecuting ? 'EXECUTING...' : 'EXECUTE'}</span>
            </button>
          </div>
        </div>

        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your SQL query here..."
          className="retro-input w-full h-32 font-mono text-sm resize-none"
          disabled={isExecuting}
        />

        {error && (
          <div className="mt-4 p-3 border border-retro-magenta bg-retro-magenta/10 text-retro-magenta font-mono text-sm">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4" />
              <span>Query Error:</span>
            </div>
            <div className="mt-1">{error}</div>
          </div>
        )}

        {executionTime !== null && !error && (
          <div className="mt-4 flex items-center justify-between text-sm font-mono text-retro-green">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-4 h-4" />
              <span>Query executed successfully</span>
            </div>
            <span>Execution time: {executionTime}ms</span>
          </div>
        )}
      </div>

      {/* Sample Queries */}
      <div className="retro-card">
        <h3 className="text-lg font-retro text-retro-cyan mb-4">SAMPLE QUERIES</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sampleQueries.map((sample, index) => (
            <div
              key={index}
              className="p-3 bg-dark-card border border-dark-border hover:border-retro-cyan/30 cursor-pointer transition-all"
              onClick={() => setQuery(sample.query)}
            >
              <h4 className="text-sm font-mono text-retro-yellow mb-1">{sample.name}</h4>
              <p className="text-xs font-mono text-retro-cyan/70 truncate">
                {sample.query}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="retro-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-retro text-retro-cyan">
              QUERY RESULTS ({results.length} rows)
            </h3>
            <span className="text-sm font-mono text-retro-cyan/70">
              Execution time: {executionTime}ms
            </span>
          </div>
          
          <div className="overflow-x-auto">
            <table className="retro-table">
              <thead>
                <tr>
                  {Object.keys(results[0]).map((header) => (
                    <th key={header}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.slice(0, 100).map((row, index) => (
                  <tr key={index}>
                    {Object.values(row).map((value, cellIndex) => (
                      <td key={cellIndex} className="max-w-xs truncate">
                        {value === null ? (
                          <span className="text-retro-cyan/50 italic">NULL</span>
                        ) : typeof value === 'boolean' ? (
                          <span className={value ? 'text-retro-green' : 'text-retro-magenta'}>
                            {value.toString()}
                          </span>
                        ) : typeof value === 'number' ? (
                          <span className="text-retro-cyan">{value}</span>
                        ) : (
                          String(value)
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            
            {results.length > 100 && (
              <div className="mt-4 text-center text-sm text-retro-yellow font-mono">
                Showing first 100 rows of {results.length} total rows
              </div>
            )}
          </div>
        </div>
      )}

      {/* Database Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="retro-card">
          <h3 className="text-lg font-retro text-retro-cyan mb-4">QUICK STATS</h3>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between">
              <span>Connection:</span>
              <span className="text-retro-green">ACTIVE</span>
            </div>
            <div className="flex justify-between">
              <span>Query Mode:</span>
              <span className="text-retro-yellow">READ-ONLY</span>
            </div>
            <div className="flex justify-between">
              <span>Last Query:</span>
              <span className="text-retro-cyan">
                {executionTime ? `${executionTime}ms ago` : 'None'}
              </span>
            </div>
          </div>
        </div>
        
        <div className="retro-card">
          <h3 className="text-lg font-retro text-retro-cyan mb-4">COMMON TABLES</h3>
          <div className="space-y-1 font-mono text-sm">
            <div className="text-retro-yellow">• inventory_items</div>
            <div className="text-retro-yellow">• transactions</div>
            <div className="text-retro-yellow">• products</div>
            <div className="text-retro-yellow">• brands</div>
            <div className="text-retro-yellow">• import_batches</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Database;