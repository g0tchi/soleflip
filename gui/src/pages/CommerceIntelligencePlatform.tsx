import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { 
  Database as DatabaseIcon, 
  Upload, 
  Terminal, 
  Play, 
  Download,
  AlertTriangle,
  CheckCircle,
  Calendar,
  Clock,
  RefreshCw,
  FileText,
  Server,
  Activity,
  Zap,
  Package,
  Trash2,
  FileUp,
  HardDrive,
  BarChart3
} from 'lucide-react';

interface QueryResult {
  [key: string]: any;
}

interface ImportResponse {
  status: string;
  message: string;
  batch_id: string;
}

interface ImportStatus {
  id: string;
  source_type: string;
  status: string;
  progress: number;
  records_processed: number;
  records_failed: number;
  created_at: string;
  completed_at?: string;
}

interface RetailerUploadResponse {
  success: boolean;
  batch_id: string;
  message: string;
}

interface RetailerUploadStatus {
  batch_id: string;
  status: string;
  progress: number;
  processed_records: number;
  failed_records: number;
  total_records?: number;
  memory_usage: number;
  current_stage: string;
  error_message?: string;
}

const CommerceIntelligencePlatform = () => {
  
  // Database Query State
  const [query, setQuery] = useState('SELECT * FROM inventory_items LIMIT 10;');
  const [results, setResults] = useState<QueryResult[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  
  // Import State
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<ImportStatus | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  
  // Active Tab
  const [activeTab, setActiveTab] = useState<'database' | 'import' | 'retailer'>('database');

  // Retailer Upload State
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [selectedRetailer, setSelectedRetailer] = useState('');
  const [uploadProgress, setUploadProgress] = useState<{[key: string]: number}>({});
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadStatuses, setUploadStatuses] = useState<{[key: string]: RetailerUploadStatus}>({});
  const [supportedRetailers, setSupportedRetailers] = useState<string[]>([]);

  const executeQuery = async () => {
    if (!query.trim()) {
      setQueryError('Please enter a query');
      return;
    }

    setIsExecuting(true);
    setQueryError(null);
    setResults([]);
    const startTime = Date.now();
    
    try {
      const data = await invoke<QueryResult[]>('run_database_query', {
        query: query.trim()
      });
      
      setResults(data);
      setExecutionTime(Date.now() - startTime);
    } catch (err) {
      setQueryError(err as string);
      console.error('Query failed:', err);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleStockXImport = async () => {
    if (!fromDate || !toDate) {
      setImportError('Please select both from and to dates');
      return;
    }

    setIsImporting(true);
    setImportError(null);
    
    try {
      const response = await invoke<ImportResponse>('import_stockx_data', {
        fromDate,
        toDate
      });
      
      console.log('Import started:', response);
      
      // Poll for status updates
      const pollStatus = async () => {
        try {
          const status = await invoke<ImportStatus>('get_import_status', {
            batchId: response.batch_id
          });
          setImportStatus(status);
          
          if (status.status === 'completed' || status.status === 'failed') {
            setIsImporting(false);
          } else {
            setTimeout(pollStatus, 2000);
          }
        } catch (err) {
          console.error('Status check failed:', err);
          setIsImporting(false);
        }
      };
      
      setTimeout(pollStatus, 1000);
    } catch (err) {
      setImportError(err as string);
      setIsImporting(false);
      console.error('Import failed:', err);
    }
  };

  // Retailer Upload Functions
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(prev => [...prev, ...files]);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setDragActive(false);
    const files = Array.from(event.dataTransfer.files);
    const validFiles = files.filter(file => 
      file.type === 'text/csv' || 
      file.type === 'application/json' || 
      file.name.endsWith('.csv') || 
      file.name.endsWith('.json') || 
      file.name.endsWith('.jsonl')
    );
    setSelectedFiles(prev => [...prev, ...validFiles]);
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    setDragActive(false);
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleRetailerUpload = async () => {
    if (selectedFiles.length === 0 || !selectedRetailer) {
      setUploadError('Please select files and retailer');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadProgress({});

    try {
      // Convert File objects to file paths (in real implementation, files would be saved first)
      const filePaths = selectedFiles.map(file => file.name);
      
      const responses = await invoke<RetailerUploadResponse[]>('upload_retailer_files', {
        retailerName: selectedRetailer,
        filePaths: filePaths,
        importName: `${selectedRetailer} Upload - ${new Date().toISOString().split('T')[0]}`
      });
      
      console.log('Upload responses:', responses);
      
      // Start polling for status of each upload
      for (const response of responses) {
        if (response.success) {
          pollUploadStatus(response.batch_id);
        }
      }
      
    } catch (err) {
      setUploadError(err as string);
      console.error('Upload failed:', err);
    } finally {
      setIsUploading(false);
    }
  };

  const pollUploadStatus = async (batchId: string) => {
    try {
      const status = await invoke<RetailerUploadStatus>('get_retailer_upload_status', {
        batchId
      });
      
      setUploadStatuses(prev => ({
        ...prev,
        [batchId]: status
      }));
      
      // Update progress for corresponding file
      const fileName = selectedFiles.find(f => 
        Object.values(uploadStatuses).some(s => s.batch_id === batchId)
      )?.name || batchId;
      
      setUploadProgress(prev => ({
        ...prev,
        [fileName]: status.progress
      }));
      
      // Continue polling if still processing
      if (status.status === 'processing' || status.status === 'queued') {
        setTimeout(() => pollUploadStatus(batchId), 2000);
      }
    } catch (err) {
      console.error('Failed to fetch upload status:', err);
    }
  };

  const exportResults = () => {
    if (results.length === 0) return;
    
    const csv = [
      Object.keys(results[0]).join(','),
      ...results.map(row => 
        Object.values(row).map(val => 
          typeof val === 'string' ? `"${val}"` : val
        ).join(',')
      )
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'query_results.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  // Load supported retailers on component mount
  useEffect(() => {
    const loadSupportedRetailers = async () => {
      try {
        const retailers = await invoke<string[]>('get_supported_retailers');
        setSupportedRetailers(retailers);
      } catch (err) {
        console.error('Failed to load supported retailers:', err);
      }
    };

    if (activeTab === 'retailer') {
      loadSupportedRetailers();
    }
  }, [activeTab]);

  const predefinedQueries = [
    'SELECT * FROM inventory_items LIMIT 10;',
    'SELECT COUNT(*) as total_items FROM inventory_items;',
    'SELECT brand, COUNT(*) as count FROM products GROUP BY brand ORDER BY count DESC LIMIT 5;',
    'SELECT status, COUNT(*) as count FROM inventory_items GROUP BY status;'
  ];

  return (
    <div className="min-h-screen p-8 space-y-8">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-4xl font-bold modern-heading mb-2">
            Commerce Intelligence Platform
          </h1>
          <p className="text-xl modern-subheading">
            Enterprise data processing and commerce analytics
          </p>
        </div>
        <div className="flex space-x-4">
          {activeTab === 'database' && (
            <button className="modern-button-outline flex items-center space-x-2">
              <FileText className="w-4 h-4" />
              <span>Save Query</span>
            </button>
          )}
          {activeTab === 'import' && (
            <button className="modern-button flex items-center space-x-2">
              <Upload className="w-4 h-4" />
              <span>New Import</span>
            </button>
          )}
          {activeTab === 'retailer' && (
            <button className="modern-button flex items-center space-x-2">
              <Package className="w-4 h-4" />
              <span>Upload Files</span>
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="modern-card px-6 py-3">
          <div className="flex items-center space-x-4">
            <div className="p-2 rounded-xl bg-blue-500/10">
              <DatabaseIcon className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="text-xl font-bold modern-heading">
                {results.length}
              </div>
              <div className="text-xs modern-subheading">
                Query Results
              </div>
            </div>
          </div>
        </div>
        <div className="modern-card px-6 py-3">
          <div className="flex items-center space-x-4">
            <div className="p-2 rounded-xl bg-purple-500/10">
              <Server className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <div className="text-xl font-bold modern-heading">
                {executionTime ? `${executionTime}ms` : '--'}
              </div>
              <div className="text-xs modern-subheading">
                Execution Time
              </div>
            </div>
          </div>
        </div>
        <div className="modern-card px-6 py-3">
          <div className="flex items-center space-x-4">
            <div className="p-2 rounded-xl bg-green-500/10">
              <Activity className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <div className="text-xl font-bold modern-heading">
                {importStatus?.records_processed || 0}
              </div>
              <div className="text-xs modern-subheading">
                Records Imported
              </div>
            </div>
          </div>
        </div>
        <div className="modern-card px-6 py-3">
          <div className="flex items-center space-x-4">
            <div className="p-2 rounded-xl bg-orange-500/10">
              <Zap className="w-5 h-5 text-orange-400" />
            </div>
            <div>
              <div className="text-xl font-bold modern-heading">
                {importStatus?.status || 'Ready'}
              </div>
              <div className="text-xs modern-subheading">
                Import Status
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 bg-gray-800/50 rounded-lg p-1">
        <button
          onClick={() => setActiveTab('database')}
          className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all ${
            activeTab === 'database'
              ? 'bg-purple-500/20 text-purple-400 shadow-lg'
              : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
          }`}
        >
          <div className="flex items-center justify-center space-x-2">
            <DatabaseIcon className="w-5 h-5" />
            <span>Analytics Query</span>
          </div>
        </button>
        <button
          onClick={() => setActiveTab('import')}
          className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all ${
            activeTab === 'import'
              ? 'bg-purple-500/20 text-purple-400 shadow-lg'
              : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
          }`}
        >
          <div className="flex items-center justify-center space-x-2">
            <Upload className="w-5 h-5" />
            <span>Commerce Import</span>
          </div>
        </button>
        <button
          onClick={() => setActiveTab('retailer')}
          className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all ${
            activeTab === 'retailer'
              ? 'bg-purple-500/20 text-purple-400 shadow-lg'
              : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
          }`}
        >
          <div className="flex items-center justify-center space-x-2">
            <Package className="w-5 h-5" />
            <span>Data Sources</span>
          </div>
        </button>
      </div>

      {activeTab === 'database' ? (
        <div className="space-y-6">
          {/* Database Query Section */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Query Input - Left */}
            <div className="lg:col-span-8 space-y-4">
              <div className="modern-card">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="modern-heading text-xl flex items-center space-x-2">
                    <Terminal className="w-5 h-5" />
                    SQL Query
                  </h2>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={executeQuery}
                      disabled={isExecuting}
                      className={`modern-button flex items-center space-x-2 ${isExecuting ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {isExecuting ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Play className="w-4 h-4" />
                      )}
                      {isExecuting ? 'Executing...' : 'Execute'}
                    </button>
                    {results.length > 0 && (
                      <button
                        onClick={exportResults}
                        className="modern-button-outline flex items-center space-x-2"
                      >
                        <Download className="w-4 h-4" />
                        Export CSV
                      </button>
                    )}
                  </div>
                </div>
                
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={6}
                  className="modern-input w-full font-mono text-sm"
                  placeholder="Enter your SQL query here..."
                />
                
                {queryError && (
                  <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-red-400 text-sm font-medium">Query Error</p>
                      <p className="text-red-300 text-sm mt-1">{queryError}</p>
                    </div>
                  </div>
                )}
                
                {executionTime !== null && (
                  <div className="mt-4 p-3 bg-green-900/20 border border-green-500/30 rounded-lg flex items-center space-x-2">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    <p className="text-green-400 text-sm">
                      Query executed successfully in {executionTime}ms
                      {results.length > 0 && ` • ${results.length} rows returned`}
                    </p>
                  </div>
                )}
              </div>

              {/* Results Table */}
              {results.length > 0 && (
                <div className="modern-card">
                  <h3 className="modern-heading text-lg mb-4 flex items-center space-x-2">
                    <FileText className="w-5 h-5" />
                    Query Results ({results.length} rows)
                  </h3>
                  <div className="overflow-x-auto max-h-[calc(100vh-32rem)] overflow-y-auto border border-gray-800/50 rounded-lg">
                    <table className="modern-table">
                      <thead className="sticky top-0 bg-gray-900/95 backdrop-blur-sm z-10">
                        <tr>
                          {Object.keys(results[0]).map((key) => (
                            <th key={key} className="text-left px-3 py-2 text-sm font-medium">
                              {key}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {results.slice(0, 100).map((row, index) => (
                          <tr key={index}>
                            {Object.values(row).map((value, cellIndex) => (
                              <td key={cellIndex} className="px-3 py-2 text-sm">
                                {value === null ? (
                                  <span className="text-gray-500 italic">null</span>
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
                      <div className="mt-4 text-center text-gray-400 text-sm">
                        Showing first 100 rows of {results.length} total results
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Quick Queries - Right */}
            <div className="lg:col-span-4">
              <div className="modern-card">
                <h3 className="modern-heading text-lg mb-4 flex items-center space-x-2">
                  <Zap className="w-5 h-5" />
                  Quick Queries
                </h3>
                <div className="space-y-2">
                  {predefinedQueries.map((predefinedQuery, index) => (
                    <button
                      key={index}
                      onClick={() => setQuery(predefinedQuery)}
                      className="w-full text-left p-3 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
                    >
                      <code className="text-blue-300">{predefinedQuery}</code>
                    </button>
                  ))}
                </div>
              </div>

              <div className="modern-card mt-6">
                <h3 className="modern-heading text-lg mb-4 flex items-center space-x-2">
                  <Server className="w-5 h-5" />
                  Database Info
                </h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Status:</span>
                    <span className="flex items-center gap-1 text-green-400">
                      <Activity className="w-3 h-3" />
                      Connected
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Type:</span>
                    <span>PostgreSQL</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Mode:</span>
                    <span className="text-yellow-400">Read-Only</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : activeTab === 'import' ? (
        <div className="space-y-6">
          {/* Data Import Section */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Import Controls - Left */}
            <div className="lg:col-span-8">
              <div className="modern-card">
                <div className="flex items-center space-x-2 mb-6">
                  <Upload className="w-6 h-6 text-blue-400" />
                  <h2 className="modern-heading text-xl">StockX Data Import</h2>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      From Date
                    </label>
                    <div className="relative">
                      <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="date"
                        value={fromDate}
                        onChange={(e) => setFromDate(e.target.value)}
                        className="modern-input pl-10"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      To Date
                    </label>
                    <div className="relative">
                      <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="date"
                        value={toDate}
                        onChange={(e) => setToDate(e.target.value)}
                        className="modern-input pl-10"
                      />
                    </div>
                  </div>
                </div>
                
                <button
                  onClick={handleStockXImport}
                  disabled={isImporting || !fromDate || !toDate}
                  className={`modern-button w-full flex items-center justify-center space-x-2 py-3 ${
                    (isImporting || !fromDate || !toDate) ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                >
                  {isImporting ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <Upload className="w-5 h-5" />
                  )}
                  {isImporting ? 'Importing Data...' : 'Start Import'}
                </button>
                
                {importError && (
                  <div className="mt-4 p-4 bg-red-900/20 border border-red-500/30 rounded-lg flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-red-400 font-medium">Import Error</p>
                      <p className="text-red-300 text-sm mt-1">{importError}</p>
                    </div>
                  </div>
                )}
                
                {importStatus && (
                  <div className="mt-4 p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        <Clock className="w-4 h-4 text-blue-400" />
                        <span className="text-blue-400 font-medium">Import Status</span>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        importStatus.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                        importStatus.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>
                        {importStatus.status.toUpperCase()}
                      </span>
                    </div>
                    
                    {importStatus.status === 'processing' && (
                      <div className="mb-3">
                        <div className="flex justify-between text-sm mb-1">
                          <span>Progress</span>
                          <span>{importStatus.progress}%</span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${importStatus.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-400">Processed:</span>
                        <span className="ml-2 text-green-400">{importStatus.records_processed}</span>
                      </div>
                      <div>
                        <span className="text-gray-400">Failed:</span>
                        <span className="ml-2 text-red-400">{importStatus.records_failed}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Import Info - Right */}
            <div className="lg:col-span-4">
              <div className="modern-card">
                <h3 className="modern-heading text-lg mb-4">Import Information</h3>
                <div className="space-y-4 text-sm">
                  <div className="p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                    <h4 className="text-blue-400 font-medium mb-2">What gets imported:</h4>
                    <ul className="text-gray-300 space-y-1 text-xs">
                      <li>• Product information</li>
                      <li>• Market pricing data</li>
                      <li>• Sales history</li>
                      <li>• Brand and category data</li>
                    </ul>
                  </div>
                  
                  <div className="p-3 bg-yellow-900/20 border border-yellow-500/30 rounded-lg">
                    <h4 className="text-yellow-400 font-medium mb-2">Important:</h4>
                    <ul className="text-gray-300 space-y-1 text-xs">
                      <li>• Large date ranges take longer</li>
                      <li>• Import runs in background</li>
                      <li>• Duplicate data is handled automatically</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Retailer Upload Section */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Upload Area - Left */}
            <div className="lg:col-span-8">
              <div className="modern-card">
                <div className="flex items-center space-x-2 mb-6">
                  <Package className="w-6 h-6 text-green-400" />
                  <h2 className="modern-heading text-xl">Enterprise Data Sources</h2>
                </div>

                {/* Retailer Selection */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Select Commerce Source
                  </label>
                  <select
                    value={selectedRetailer}
                    onChange={(e) => setSelectedRetailer(e.target.value)}
                    className="modern-input w-full"
                  >
                    <option value="">Choose a data source...</option>
                    <option value="awin">Awin Affiliate Network</option>
                    {supportedRetailers.map((retailer) => (
                      <option key={retailer} value={retailer}>
                        {retailer.charAt(0).toUpperCase() + retailer.slice(1)} Retailer
                      </option>
                    ))}
                  </select>
                </div>

                {/* File Upload Area */}
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
                    dragActive 
                      ? 'border-blue-400 bg-blue-400/10' 
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                >
                  <FileUp className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-lg font-medium text-gray-300 mb-2">
                    Drop commerce data files here or click to browse
                  </h3>
                  <p className="text-sm text-gray-400 mb-4">
                    Enterprise-grade processing: CSV, JSON, JSONL files up to 1GB each
                  </p>
                  <input
                    type="file"
                    multiple
                    accept=".csv,.json,.jsonl"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload"
                  />
                  <label
                    htmlFor="file-upload"
                    className="modern-button inline-flex items-center space-x-2 cursor-pointer"
                  >
                    <Upload className="w-4 h-4" />
                    <span>Select Files</span>
                  </label>
                </div>

                {/* Selected Files */}
                {selectedFiles.length > 0 && (
                  <div className="mt-6 space-y-3">
                    <h4 className="font-medium text-gray-300">Selected Files ({selectedFiles.length})</h4>
                    {selectedFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <FileText className="w-5 h-5 text-blue-400" />
                          <div>
                            <p className="font-medium text-gray-200">{file.name}</p>
                            <p className="text-xs text-gray-400">
                              {(file.size / (1024 * 1024)).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          {uploadProgress[file.name] && (
                            <div className="flex items-center space-x-2">
                              <div className="w-32 bg-gray-700 rounded-full h-2">
                                <div 
                                  className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                                  style={{ width: `${uploadProgress[file.name]}%` }}
                                />
                              </div>
                              <span className="text-xs text-gray-400">{uploadProgress[file.name]}%</span>
                            </div>
                          )}
                          <button
                            onClick={() => removeFile(index)}
                            className="text-red-400 hover:text-red-300 p-1"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Upload Button */}
                <div className="mt-6">
                  <button
                    onClick={handleRetailerUpload}
                    disabled={isUploading || selectedFiles.length === 0 || !selectedRetailer}
                    className={`modern-button w-full flex items-center justify-center space-x-2 py-3 ${
                      (isUploading || selectedFiles.length === 0 || !selectedRetailer) ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  >
                    {isUploading ? (
                      <RefreshCw className="w-5 h-5 animate-spin" />
                    ) : (
                      <Upload className="w-5 h-5" />
                    )}
                    <span>
                      {isUploading 
                        ? `Processing ${selectedFiles.length} commerce files...` 
                        : `Process ${selectedFiles.length} files`
                      }
                    </span>
                  </button>
                </div>

                {/* Upload Error */}
                {uploadError && (
                  <div className="mt-4 p-4 bg-red-900/20 border border-red-500/30 rounded-lg flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-red-400 font-medium">Upload Error</p>
                      <p className="text-red-300 text-sm mt-1">{uploadError}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Upload Info - Right */}
            <div className="lg:col-span-4 space-y-6">
              <div className="modern-card">
                <h3 className="modern-heading text-lg mb-4 flex items-center space-x-2">
                  <BarChart3 className="w-5 h-5" />
                  Processing Performance
                </h3>
                <div className="space-y-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Memory Usage:</span>
                    <span className="text-blue-400">
                      {Object.values(uploadStatuses)[0]?.memory_usage 
                        ? `${Object.values(uploadStatuses)[0].memory_usage}MB / 2GB`
                        : '0MB / 2GB'
                      }
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Chunk Size:</span>
                    <span className="text-green-400">5,000 records</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Processing:</span>
                    <span className="text-yellow-400">
                      {Object.values(uploadStatuses)[0]?.current_stage || 'Ready'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Status:</span>
                    <span className={`flex items-center gap-1 ${
                      isUploading ? 'text-blue-400' : 
                      Object.values(uploadStatuses).some(s => s.status === 'completed') ? 'text-green-400' :
                      Object.values(uploadStatuses).some(s => s.status === 'failed') ? 'text-red-400' :
                      'text-green-400'
                    }`}>
                      <Activity className="w-3 h-3" />
                      {isUploading ? 'Processing' : 
                       Object.values(uploadStatuses).length > 0 ? 
                       Object.values(uploadStatuses)[0].status : 'Ready'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="modern-card">
                <h3 className="modern-heading text-lg mb-4 flex items-center space-x-2">
                  <HardDrive className="w-5 h-5" />
                  Commerce Sources
                </h3>
                <div className="space-y-3 text-sm">
                  <div className="p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
                    <h4 className="text-green-400 font-medium mb-2">Data Sources:</h4>
                    <ul className="text-gray-300 space-y-1 text-xs">
                      <li>• Awin Affiliate Network</li>
                      <li>• Retailer CSV exports</li>
                      <li>• JSON product catalogs</li>
                      <li>• Multi-source processing</li>
                    </ul>
                  </div>
                  
                  <div className="p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                    <h4 className="text-blue-400 font-medium mb-2">Enterprise Features:</h4>
                    <ul className="text-gray-300 space-y-1 text-xs">
                      <li>• Scalable streaming pipeline</li>
                      <li>• Real-time analytics</li>
                      <li>• Automated error recovery</li>
                      <li>• Intelligence-driven processing</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CommerceIntelligencePlatform;