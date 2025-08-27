import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { 
  Package, 
  Search, 
  Filter, 
  RefreshCw, 
  Download,
  Eye,
  Edit,
  Trash2 
} from 'lucide-react';

interface InventoryItem {
  id: string;
  sku: string;
  name: string;
  brand: string;
  size: string;
  condition: string;
  purchase_price: number;
  current_value: number;
  status: string;
}

const Inventory = () => {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('all');

  const fetchInventory = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await invoke<InventoryItem[]>('get_inventory_items', { limit: 100 });
      setItems(data);
    } catch (err) {
      setError(err as string);
      console.error('Failed to fetch inventory:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, []);

  const filteredItems = items.filter(item => {
    const matchesSearch = 
      item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.brand.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.sku.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = selectedStatus === 'all' || item.status === selectedStatus;
    
    return matchesSearch && matchesStatus;
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR'
    }).format(value);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'available':
        return 'text-retro-green';
      case 'sold':
        return 'text-retro-cyan';
      case 'pending':
        return 'text-retro-yellow';
      case 'reserved':
        return 'text-retro-magenta';
      default:
        return 'text-retro-cyan/70';
    }
  };

  const exportToCSV = async () => {
    try {
      const csvData = await invoke<string>('export_data_csv', { 
        table: 'inventory_items',
        filters: selectedStatus !== 'all' ? { status: selectedStatus } : null
      });
      
      // Create and download CSV file
      const blob = new Blob([csvData], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `inventory_export_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Package className="w-16 h-16 text-retro-cyan animate-pulse mx-auto mb-4" />
          <p className="text-retro-cyan font-mono">LOADING INVENTORY...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-retro font-bold text-retro-cyan animate-glow">
            INVENTORY
          </h1>
          <p className="text-retro-cyan/70 font-mono mt-1">
            {filteredItems.length} items ({items.length} total)
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <button 
            onClick={exportToCSV}
            className="retro-button-success flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>EXPORT</span>
          </button>
          <button 
            onClick={fetchInventory}
            className="retro-button flex items-center space-x-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>REFRESH</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="retro-card">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center space-x-2">
            <Search className="w-4 h-4 text-retro-cyan" />
            <input
              type="text"
              placeholder="Search inventory..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="retro-input w-64"
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-retro-cyan" />
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="retro-input"
            >
              <option value="all">All Status</option>
              <option value="available">Available</option>
              <option value="sold">Sold</option>
              <option value="pending">Pending</option>
              <option value="reserved">Reserved</option>
            </select>
          </div>
        </div>
      </div>

      {/* Inventory Table */}
      {error ? (
        <div className="retro-card text-center">
          <p className="text-retro-magenta font-mono">{error}</p>
          <button 
            onClick={fetchInventory}
            className="retro-button mt-4"
          >
            RETRY
          </button>
        </div>
      ) : (
        <div className="retro-card overflow-x-auto">
          <table className="retro-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product</th>
                <th>Brand</th>
                <th>Size</th>
                <th>Condition</th>
                <th>Purchase</th>
                <th>Current Value</th>
                <th>Profit</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item) => {
                const profit = item.current_value - item.purchase_price;
                const profitMargin = item.purchase_price > 0 
                  ? ((profit / item.purchase_price) * 100)
                  : 0;

                return (
                  <tr key={item.id}>
                    <td className="font-mono text-retro-cyan">{item.sku}</td>
                    <td className="max-w-xs truncate">{item.name}</td>
                    <td className="text-retro-yellow">{item.brand}</td>
                    <td>{item.size}</td>
                    <td>{item.condition}</td>
                    <td className="text-retro-cyan">{formatCurrency(item.purchase_price)}</td>
                    <td className="text-retro-green">{formatCurrency(item.current_value)}</td>
                    <td className={profit >= 0 ? 'text-retro-green' : 'text-retro-magenta'}>
                      {formatCurrency(profit)}
                      <br />
                      <span className="text-xs opacity-70">
                        ({profitMargin.toFixed(1)}%)
                      </span>
                    </td>
                    <td>
                      <span className={`font-mono text-xs uppercase ${getStatusColor(item.status)}`}>
                        {item.status}
                      </span>
                    </td>
                    <td>
                      <div className="flex space-x-2">
                        <button 
                          className="text-retro-cyan hover:text-retro-cyan/70 transition-colors"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button 
                          className="text-retro-yellow hover:text-retro-yellow/70 transition-colors"
                          title="Edit Item"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button 
                          className="text-retro-magenta hover:text-retro-magenta/70 transition-colors"
                          title="Delete Item"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          
          {filteredItems.length === 0 && !isLoading && (
            <div className="text-center py-12">
              <Package className="w-16 h-16 text-retro-cyan/30 mx-auto mb-4" />
              <p className="text-retro-cyan/50 font-mono">
                {searchTerm || selectedStatus !== 'all' 
                  ? 'No items match your filters'
                  : 'No inventory items found'
                }
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Inventory;