import { useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { 
  Upload, 
  Calendar, 
  Clock, 
  CheckCircle, 
  AlertTriangle,
  RefreshCw,
  Download 
} from 'lucide-react';

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

const Import = () => {
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<ImportStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleStockXImport = async () => {
    if (!fromDate || !toDate) {
      setError('Please select both from and to dates');
      return;
    }

    setIsImporting(true);
    setError(null);
    
    try {
      const response = await invoke<ImportResponse>('import_stockx_data', {
        fromDate,
        toDate
      });
      
      // Start polling for status
      pollImportStatus(response.batch_id);
      
    } catch (err) {
      setError(err as string);
      console.error('Import failed:', err);
    } finally {
      setIsImporting(false);
    }
  };

  const pollImportStatus = async (batchId: string) => {
    try {
      const status = await invoke<ImportStatus>('get_import_status', {
        batchId
      });
      
      setImportStatus(status);
      
      // Continue polling if still processing
      if (status.status === 'processing' || status.status === 'pending') {
        setTimeout(() => pollImportStatus(batchId), 2000);
      }
    } catch (err) {
      console.error('Failed to fetch import status:', err);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-retro-green" />;
      case 'processing':
        return <RefreshCw className="w-5 h-5 text-retro-cyan animate-spin" />;
      case 'failed':
        return <AlertTriangle className="w-5 h-5 text-retro-magenta" />;
      default:
        return <Clock className="w-5 h-5 text-retro-yellow" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-retro-green';
      case 'processing':
        return 'text-retro-cyan';
      case 'failed':
        return 'text-retro-magenta';
      default:
        return 'text-retro-yellow';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-retro font-bold text-retro-cyan animate-glow">
          DATA IMPORT
        </h1>
        <p className="text-retro-cyan/70 font-mono mt-1">
          Import data from external sources
        </p>
      </div>

      {/* StockX Import */}
      <div className="retro-card">
        <div className="flex items-center space-x-3 mb-6">
          <Upload className="w-8 h-8 text-retro-cyan" />
          <h2 className="text-xl font-retro text-retro-cyan">STOCKX IMPORT</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-mono text-retro-cyan/70 mb-2">
              FROM DATE
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-retro-cyan/50" />
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="retro-input pl-10 w-full"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-mono text-retro-cyan/70 mb-2">
              TO DATE
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-retro-cyan/50" />
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="retro-input pl-10 w-full"
              />
            </div>
          </div>
        </div>
        
        {error && (
          <div className="mt-4 p-3 border border-retro-magenta bg-retro-magenta/10 text-retro-magenta font-mono text-sm">
            {error}
          </div>
        )}
        
        <div className="mt-6">
          <button
            onClick={handleStockXImport}
            disabled={isImporting || !fromDate || !toDate}
            className="retro-button-success flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isImporting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            <span>{isImporting ? 'IMPORTING...' : 'START IMPORT'}</span>
          </button>
        </div>
      </div>

      {/* Import Status */}
      {importStatus && (
        <div className="retro-card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-retro text-retro-cyan">IMPORT STATUS</h3>
            <div className="flex items-center space-x-2">
              {getStatusIcon(importStatus.status)}
              <span className={`font-mono uppercase ${getStatusColor(importStatus.status)}`}>
                {importStatus.status}
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="flex justify-between font-mono text-sm">
                <span>Batch ID:</span>
                <span className="text-retro-cyan">{importStatus.id}</span>
              </div>
              <div className="flex justify-between font-mono text-sm">
                <span>Source:</span>
                <span className="text-retro-yellow uppercase">{importStatus.source_type}</span>
              </div>
              <div className="flex justify-between font-mono text-sm">
                <span>Started:</span>
                <span className="text-retro-cyan">
                  {new Date(importStatus.created_at).toLocaleString()}
                </span>
              </div>
              {importStatus.completed_at && (
                <div className="flex justify-between font-mono text-sm">
                  <span>Completed:</span>
                  <span className="text-retro-green">
                    {new Date(importStatus.completed_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
            
            <div className="space-y-4">
              <div className="flex justify-between font-mono text-sm">
                <span>Records Processed:</span>
                <span className="text-retro-green">{importStatus.records_processed}</span>
              </div>
              <div className="flex justify-between font-mono text-sm">
                <span>Records Failed:</span>
                <span className="text-retro-magenta">{importStatus.records_failed}</span>
              </div>
              <div className="flex justify-between font-mono text-sm">
                <span>Success Rate:</span>
                <span className="text-retro-cyan">
                  {importStatus.records_processed > 0
                    ? (((importStatus.records_processed - importStatus.records_failed) / importStatus.records_processed) * 100).toFixed(1)
                    : 0
                  }%
                </span>
              </div>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="mt-6">
            <div className="flex justify-between text-sm font-mono mb-2">
              <span>Progress</span>
              <span>{importStatus.progress.toFixed(1)}%</span>
            </div>
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${importStatus.progress}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Import History */}
      <div className="retro-card">
        <h3 className="text-lg font-retro text-retro-cyan mb-4">RECENT IMPORTS</h3>
        <div className="text-center py-8 text-retro-cyan/50">
          <Clock className="w-12 h-12 mx-auto mb-2" />
          <p className="font-mono">No recent imports</p>
          <p className="font-mono text-xs mt-1">Import history will appear here</p>
        </div>
      </div>

      {/* Import Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="retro-card">
          <h3 className="text-lg font-retro text-retro-cyan mb-4">CSV IMPORT</h3>
          <p className="text-sm text-retro-cyan/70 mb-4 font-mono">
            Import inventory from CSV files
          </p>
          <button className="retro-button flex items-center space-x-2">
            <Upload className="w-4 h-4" />
            <span>SELECT FILE</span>
          </button>
        </div>
        
        <div className="retro-card">
          <h3 className="text-lg font-retro text-retro-cyan mb-4">SHOPIFY SYNC</h3>
          <p className="text-sm text-retro-cyan/70 mb-4 font-mono">
            Synchronize with Shopify store
          </p>
          <button className="retro-button-warning flex items-center space-x-2">
            <RefreshCw className="w-4 h-4" />
            <span>SYNC NOW</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Import;