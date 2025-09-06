import { useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { 
  Upload, 
  Calendar, 
  Clock, 
  CheckCircle, 
  AlertTriangle,
  RefreshCw
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
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'processing':
        return <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />;
      case 'failed':
        return <AlertTriangle className="w-5 h-5 text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-yellow-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-400';
      case 'processing':
        return 'text-blue-400';
      case 'failed':
        return 'text-red-400';
      default:
        return 'text-yellow-400';
    }
  };

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold modern-heading">
          Data Import
        </h1>
        <p className="modern-subheading mt-1">
          Import data from external sources
        </p>
      </div>

      {/* StockX Import */}
      <div className="modern-card">
        <div className="flex items-center space-x-3 mb-6">
          <Upload className="w-8 h-8 text-purple-400" />
          <h2 className="text-xl modern-heading">StockX Import</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium modern-subheading mb-2">
              From Date
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="modern-input pl-10 w-full"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium modern-subheading mb-2">
              To Date
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="modern-input pl-10 w-full"
              />
            </div>
          </div>
        </div>
        
        {error && (
          <div className="mt-4 p-3 border border-red-400 bg-red-400/10 text-red-400 text-sm">
            {error}
          </div>
        )}
        
        <div className="mt-6">
          <button
            onClick={handleStockXImport}
            disabled={isImporting || !fromDate || !toDate}
            className="modern-button flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isImporting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            <span>{isImporting ? 'Importing...' : 'Start Import'}</span>
          </button>
        </div>
      </div>

      {/* Import Status */}
      {importStatus && (
        <div className="modern-card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg modern-heading">Import Status</h3>
            <div className="flex items-center space-x-2">
              {getStatusIcon(importStatus.status)}
              <span className={`font-medium uppercase ${getStatusColor(importStatus.status)}`}>
                {importStatus.status}
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="flex justify-between font-medium text-sm">
                <span>Batch ID:</span>
                <span className="modern-heading">{importStatus.id}</span>
              </div>
              <div className="flex justify-between font-medium text-sm">
                <span>Source:</span>
                <span className="text-yellow-400 uppercase">{importStatus.source_type}</span>
              </div>
              <div className="flex justify-between font-medium text-sm">
                <span>Started:</span>
                <span className="text-blue-400">
                  {new Date(importStatus.created_at).toLocaleString()}
                </span>
              </div>
              {importStatus.completed_at && (
                <div className="flex justify-between font-medium text-sm">
                  <span>Completed:</span>
                  <span className="text-green-400">
                    {new Date(importStatus.completed_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
            
            <div className="space-y-4">
              <div className="flex justify-between font-medium text-sm">
                <span>Records Processed:</span>
                <span className="text-green-400">{importStatus.records_processed}</span>
              </div>
              <div className="flex justify-between font-medium text-sm">
                <span>Records Failed:</span>
                <span className="text-red-400">{importStatus.records_failed}</span>
              </div>
              <div className="flex justify-between font-medium text-sm">
                <span>Success Rate:</span>
                <span className="text-blue-400">
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
            <div className="flex justify-between text-sm font-medium mb-2">
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
      <div className="modern-card">
        <h3 className="text-lg modern-heading mb-4">Recent Imports</h3>
        <div className="text-center py-8 text-gray-500">
          <Clock className="w-12 h-12 mx-auto mb-2" />
          <p className="font-medium">No recent imports</p>
          <p className="modern-subheading text-xs mt-1">Import history will appear here</p>
        </div>
      </div>

      {/* Import Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="modern-card">
          <h3 className="text-lg modern-heading mb-4">CSV Import</h3>
          <p className="text-sm modern-subheading mb-4">
            Import inventory from CSV files
          </p>
          <button className="modern-button flex items-center space-x-2">
            <Upload className="w-4 h-4" />
            <span>Select File</span>
          </button>
        </div>
        
        <div className="modern-card">
          <h3 className="text-lg modern-heading mb-4">Shopify Sync</h3>
          <p className="text-sm modern-subheading mb-4">
            Synchronize with Shopify store
          </p>
          <button className="modern-button-secondary flex items-center space-x-2">
            <RefreshCw className="w-4 h-4" />
            <span>Sync Now</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Import;