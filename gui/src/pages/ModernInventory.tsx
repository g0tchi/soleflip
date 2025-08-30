import { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  Plus, 
  Package,
  Tag,
  TrendingUp,
  Eye,
  Edit3,
  Trash2,
  RefreshCw,
  Download
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/tauri';

interface InventoryItem {
  id: string;
  product_name: string;
  brand: string;
  size: string;
  condition: string;
  purchase_price: number;
  current_price: number;
  status: string;
  created_at: string;
}

const ModernInventory = () => {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const fetchInventory = async () => {
    try {
      setIsLoading(true);
      const response = await invoke<any>('get_inventory_items');
      setInventory(response.items || []);
    } catch (error) {
      console.error('Failed to fetch inventory:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, []);

  const filteredInventory = inventory.filter(item => {
    const matchesSearch = 
      item.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.brand.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const stats = [
    {
      title: 'Total Items',
      value: inventory.length,
      icon: Package,
      color: 'blue'
    },
    {
      title: 'In Stock',
      value: inventory.filter(item => item.status === 'in_stock').length,
      icon: Tag,
      color: 'green'
    },
    {
      title: 'Listed',
      value: inventory.filter(item => item.status === 'listed').length,
      icon: TrendingUp,
      color: 'purple'
    },
    {
      title: 'Total Value',
      value: `$${inventory.reduce((sum, item) => sum + item.current_price, 0).toLocaleString()}`,
      icon: TrendingUp,
      color: 'orange'
    }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'in_stock':
        return 'bg-green-500/20 text-green-400';
      case 'listed':
        return 'bg-blue-500/20 text-blue-400';
      case 'sold':
        return 'bg-gray-500/20 text-gray-400';
      default:
        return 'bg-purple-500/20 text-purple-400';
    }
  };

  const getConditionColor = (condition: string) => {
    switch (condition) {
      case 'new':
        return 'bg-green-500/20 text-green-400';
      case 'used':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'damaged':
        return 'bg-red-500/20 text-red-400';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  return (
    <div className="min-h-screen p-8 space-y-8">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-4xl font-bold modern-heading mb-2">
            Inventory
          </h1>
          <p className="text-xl modern-subheading">
            Manage your product inventory and track performance
          </p>
        </div>
        <div className="flex space-x-4">
          <button
            onClick={fetchInventory}
            disabled={isLoading}
            className="modern-button-outline flex items-center space-x-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button className="modern-button flex items-center space-x-2">
            <Plus className="w-4 h-4" />
            <span>Add Item</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.title} className="modern-card">
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-xl bg-${stat.color}-500/10`}>
                  <Icon className={`w-6 h-6 text-${stat.color}-400`} />
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold modern-heading mb-1">
                  {stat.value}
                </div>
                <div className="text-sm modern-subheading">
                  {stat.title}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Filters and Search */}
      <div className="modern-card">
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by product name or brand..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="modern-input pl-10 w-full"
            />
          </div>
          
          <div className="flex gap-4">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="modern-input"
            >
              <option value="all">All Status</option>
              <option value="in_stock">In Stock</option>
              <option value="listed">Listed</option>
              <option value="sold">Sold</option>
            </select>
            
            <button className="modern-button-outline flex items-center space-x-2">
              <Filter className="w-4 h-4" />
              <span>More Filters</span>
            </button>
            
            <button className="modern-button-outline flex items-center space-x-2">
              <Download className="w-4 h-4" />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Inventory Table */}
        {isLoading ? (
          <div className="flex justify-center items-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin text-purple-400" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="modern-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Brand</th>
                  <th>Size</th>
                  <th>Condition</th>
                  <th>Purchase Price</th>
                  <th>Current Price</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredInventory.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="font-medium modern-heading text-sm">
                        {item.product_name}
                      </div>
                    </td>
                    <td>
                      <span className="modern-subheading">
                        {item.brand}
                      </span>
                    </td>
                    <td>
                      <span className="px-2 py-1 rounded-lg bg-gray-800/50 text-xs font-medium">
                        {item.size}
                      </span>
                    </td>
                    <td>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getConditionColor(item.condition)}`}>
                        {item.condition}
                      </span>
                    </td>
                    <td>
                      <span className="font-medium">
                        ${item.purchase_price.toFixed(2)}
                      </span>
                    </td>
                    <td>
                      <span className="font-medium">
                        ${item.current_price.toFixed(2)}
                      </span>
                    </td>
                    <td>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                        {item.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      <div className="flex space-x-2">
                        <button className="p-2 hover:bg-gray-800/50 rounded-lg transition-colors">
                          <Eye className="w-4 h-4 text-blue-400" />
                        </button>
                        <button className="p-2 hover:bg-gray-800/50 rounded-lg transition-colors">
                          <Edit3 className="w-4 h-4 text-purple-400" />
                        </button>
                        <button className="p-2 hover:bg-gray-800/50 rounded-lg transition-colors">
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredInventory.length === 0 && !isLoading && (
              <div className="text-center py-12">
                <Package className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium modern-heading mb-2">No inventory items found</h3>
                <p className="modern-subheading">
                  {searchTerm || statusFilter !== 'all' 
                    ? 'Try adjusting your search or filters' 
                    : 'Start by adding your first inventory item'}
                </p>
                <button className="modern-button mt-4 flex items-center space-x-2 mx-auto">
                  <Plus className="w-4 h-4" />
                  <span>Add First Item</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ModernInventory;