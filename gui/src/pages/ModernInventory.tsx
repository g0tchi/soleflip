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
  Download,
  ExternalLink,
  Clock,
  Calendar
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/tauri';

interface InventoryItem {
  id: string;
  product_name: string;
  brand_name?: string;
  brand?: string;  // Legacy support
  size_value?: string;
  size?: string;  // Legacy support
  condition: string;
  purchase_price?: number;
  current_price?: number;
  ask_price?: number;  // StockX listing price
  status: 'in_stock' | 'presale' | 'dropship' | 'listed_stockx' | 'listed_alias' | 'sold' | 'reserved' | 'error';
  sourcing_type: 'physical' | 'presale' | 'dropship';  // Where item comes from
  listing_status?: 'active' | 'inactive' | 'pending' | 'sold';  // Platform listing status
  stockx_listing_id?: string;
  alias_listing_id?: string;
  created_at: string;
  updated_at?: string;
  stockx_id?: string;
  external_ids?: Record<string, string>;
}

const ModernInventory = () => {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [stockxListings, setStockxListings] = useState<any[]>([]);
  const [aliasListings, setAliasListings] = useState<any[]>([]);
  const [listingsLoading, setListingsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'inventory' | 'stockx' | 'alias'>('inventory');
  const [syncLoading, setSyncLoading] = useState(false);

  const fetchInventory = async () => {
    try {
      setIsLoading(true);
      const response = await invoke<any>('get_inventory_items');
      // Handle both paginated response format and direct items array
      const items = response.data?.items || response.items || [];
      console.log('Inventory items loaded:', items);
      console.log('Items by status:', items.reduce((acc: Record<string, number>, item: InventoryItem) => {
        acc[item.status] = (acc[item.status] || 0) + 1;
        return acc;
      }, {}));
      console.log('Items that can show StockX button:', items.filter((item: InventoryItem) => 
        item.status === 'in_stock' || item.status === 'presale' || item.status === 'preorder'
      ));
      setInventory(items);
    } catch (error) {
      console.error('Failed to fetch inventory:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStockXListings = async () => {
    try {
      setListingsLoading(true);
      const listings = await invoke<any[]>('get_stockx_listings', { 
        status: null, 
        limit: 100 
      });
      console.log('StockX listings loaded:', listings);
      setStockxListings(listings || []);
    } catch (error) {
      console.error('Failed to fetch StockX listings:', error);
      setStockxListings([]);
    } finally {
      setListingsLoading(false);
    }
  };

  const fetchAliasListings = async () => {
    try {
      setListingsLoading(true);
      const listings = await invoke<any[]>('get_alias_listings', { 
        status: null, 
        limit: 100 
      });
      console.log('Alias listings loaded:', listings);
      setAliasListings(listings || []);
    } catch (error) {
      console.error('Failed to fetch Alias listings:', error);
      setAliasListings([]);
    } finally {
      setListingsLoading(false);
    }
  };

  const syncInventoryFromStockX = async () => {
    try {
      setSyncLoading(true);
      const response = await invoke<any>('sync_inventory_from_stockx');
      console.log('StockX sync response:', response);
      
      const data = response.data || {};
      const message = `Sync completed successfully!
        
• ${data.synced_count || 0} inventory items synced
• ${data.products_created || 0} new products created with market data
• ${data.market_data_imported || 0} products with market data imported
• Processed ${data.total_listings || 0} StockX listings`;
      
      alert(message);
      
      // Refresh inventory after sync
      await fetchInventory();
    } catch (error) {
      console.error('Failed to sync from StockX:', error);
      alert('Failed to sync from StockX. Check console for details.');
    } finally {
      setSyncLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, []);

  const filteredInventory = inventory.filter(item => {
    const brandName = item.brand_name || item.brand || '';
    const sizeName = item.size_value || item.size || '';
    
    const matchesSearch = 
      item.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      brandName.toLowerCase().includes(searchTerm.toLowerCase());
    
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
      title: 'Physical Stock',
      value: inventory.filter(item => item.sourcing_type === 'physical' && item.status === 'in_stock').length,
      icon: Tag,
      color: 'green'
    },
    {
      title: 'Active Listings',
      value: inventory.filter(item => item.status === 'listed_stockx' || item.status === 'listed_alias').length,
      icon: TrendingUp,
      color: 'purple'
    },
    {
      title: 'Presale Items',
      value: inventory.filter(item => item.sourcing_type === 'presale' || item.sourcing_type === 'dropship').length,
      icon: Calendar,
      color: 'orange'
    }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'in_stock':
        return 'bg-green-500/20 text-green-400';
      case 'listed_stockx':
        return 'bg-blue-500/20 text-blue-400';
      case 'listed_alias':
        return 'bg-cyan-500/20 text-cyan-400';
      case 'sold':
        return 'bg-gray-500/20 text-gray-400';
      case 'presale':
        return 'bg-orange-500/20 text-orange-400';
      case 'dropship':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'reserved':
        return 'bg-amber-500/20 text-amber-400';
      case 'error':
        return 'bg-red-500/20 text-red-400';
      default:
        return 'bg-purple-500/20 text-purple-400';
    }
  };

  const getSourcingTypeColor = (sourcingType: string) => {
    switch (sourcingType) {
      case 'physical':
        return 'bg-green-500/10 text-green-300 border border-green-500/20';
      case 'presale':
        return 'bg-orange-500/10 text-orange-300 border border-orange-500/20';
      case 'dropship':
        return 'bg-yellow-500/10 text-yellow-300 border border-yellow-500/20';
      default:
        return 'bg-gray-500/10 text-gray-300 border border-gray-500/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'in_stock':
        return <Package className="w-4 h-4" />;
      case 'listed':
        return <ExternalLink className="w-4 h-4" />;
      case 'sold':
        return <Tag className="w-4 h-4" />;
      case 'presale':
        return <Calendar className="w-4 h-4" />;
      case 'preorder':
        return <Clock className="w-4 h-4" />;
      default:
        return <Package className="w-4 h-4" />;
    }
  };

  const canListOnStockX = (item: InventoryItem) => {
    return item.status === 'in_stock' || item.status === 'presale' || item.status === 'preorder';
  };

  const handleStockXListing = async (item: InventoryItem) => {
    try {
      const response = await invoke('create_stockx_listing', {
        itemId: item.id,
        listingType: item.status === 'in_stock' ? 'immediate' : 'presale'
      });
      console.log('StockX listing created:', response);
      fetchInventory(); // Refresh to update status
    } catch (error) {
      console.error('Failed to create StockX listing:', error);
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
          {activeTab === 'inventory' && (
            <button className="modern-button flex items-center space-x-2">
              <Plus className="w-4 h-4" />
              <span>Add Item</span>
            </button>
          )}
          {activeTab === 'stockx' && (
            <button 
              onClick={fetchStockXListings}
              disabled={listingsLoading}
              className="modern-button-outline flex items-center space-x-2"
            >
              <RefreshCw className={`w-4 h-4 ${listingsLoading ? 'animate-spin' : ''}`} />
              <span>Refresh StockX Listings</span>
            </button>
          )}
          {activeTab === 'alias' && (
            <button 
              onClick={fetchAliasListings}
              disabled={listingsLoading}
              className="modern-button-outline flex items-center space-x-2"
            >
              <RefreshCw className={`w-4 h-4 ${listingsLoading ? 'animate-spin' : ''}`} />
              <span>Refresh Alias Listings</span>
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.title} className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className={`p-2 rounded-xl bg-${stat.color}-500/10`}>
                  <Icon className={`w-5 h-5 text-${stat.color}-400`} />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    {stat.value}
                  </div>
                  <div className="text-xs modern-subheading">
                    {stat.title}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 bg-gray-800/50 rounded-lg p-1">
        <button
          onClick={() => setActiveTab('inventory')}
          className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all ${
            activeTab === 'inventory'
              ? 'bg-purple-500/20 text-purple-400 shadow-lg'
              : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
          }`}
        >
          <div className="flex items-center justify-center space-x-2">
            <Package className="w-5 h-5" />
            <span>Inventory</span>
            <span className="px-2 py-1 text-xs bg-gray-600/50 rounded-full">
              {inventory.length}
            </span>
          </div>
        </button>
        
        <button
          onClick={() => {
            setActiveTab('stockx');
            if (stockxListings.length === 0) {
              fetchStockXListings();
            }
          }}
          className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all ${
            activeTab === 'stockx'
              ? 'bg-green-500/20 text-green-400 shadow-lg'
              : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
          }`}
        >
          <div className="flex items-center justify-center space-x-2">
            <ExternalLink className="w-5 h-5" />
            <span>StockX Listings</span>
            <span className="px-2 py-1 text-xs bg-gray-600/50 rounded-full">
              {stockxListings.length}
            </span>
          </div>
        </button>
        
        <button
          onClick={() => {
            setActiveTab('alias');
            if (aliasListings.length === 0) {
              fetchAliasListings();
            }
          }}
          className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all ${
            activeTab === 'alias'
              ? 'bg-blue-500/20 text-blue-400 shadow-lg'
              : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
          }`}
        >
          <div className="flex items-center justify-center space-x-2">
            <Tag className="w-5 h-5" />
            <span>Alias Listings</span>
            <span className="px-2 py-1 text-xs bg-gray-600/50 rounded-full">
              {aliasListings.length}
            </span>
          </div>
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'inventory' && (
        <>
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
              <option value="presale">Presale</option>
              <option value="preorder">Preorder</option>
              <option value="sold">Sold</option>
            </select>
            
          </div>
        </div>

        {/* Inventory Table */}
        {isLoading ? (
          <div className="flex justify-center items-center py-20">
            <div className="text-center">
              <RefreshCw className="w-12 h-12 animate-spin text-purple-400 mx-auto mb-4" />
              <p className="modern-heading text-lg">Loading Inventory...</p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto max-h-96 overflow-y-auto border border-gray-800/50 rounded-lg">
            <table className="modern-table">
              <thead className="sticky top-0 bg-gray-900/95 backdrop-blur-sm z-10">
                <tr>
                  <th>Product</th>
                  <th>Brand</th>
                  <th>Size</th>
                  <th>Sourcing</th>
                  <th>Cost</th>
                  <th>Ask Price</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredInventory.map((item) => {
                  const isNonPhysical = item.sourcing_type === 'presale' || item.sourcing_type === 'dropship';
                  const isListed = item.status === 'listed_stockx' || item.status === 'listed_alias';
                  return (
                    <tr key={item.id} className={isNonPhysical ? 'bg-orange-500/5 border-l-4 border-orange-400' : isListed ? 'bg-blue-500/5 border-l-4 border-blue-400' : ''}>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="font-medium modern-heading text-sm">
                          {item.product_name}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="modern-subheading">
                        {item.brand_name || item.brand || 'Unknown Brand'}
                      </span>
                    </td>
                    <td>
                      <span className="px-2 py-1 rounded-lg bg-gray-800/50 text-xs font-medium">
                        {item.size_value || item.size || 'N/A'}
                      </span>
                    </td>
                    <td>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getSourcingTypeColor(item.sourcing_type || 'physical')}`}>
                        {item.sourcing_type || 'physical'}
                      </span>
                    </td>
                    <td>
                      <span className="font-medium text-sm">
                        {item.purchase_price ? `€${item.purchase_price.toFixed(2)}` : (item.sourcing_type === 'presale' || item.sourcing_type === 'dropship') ? 'On-demand' : '€0.00'}
                      </span>
                    </td>
                    <td>
                      <span className="font-medium text-green-400">
                        €{item.ask_price?.toFixed(2) || item.current_price?.toFixed(2) || '0.00'}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(item.status)}
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                          {item.status.replace('_', ' ')}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="flex space-x-1">
                        {canListOnStockX(item) && item.status !== 'listed' && (
                          <button 
                            onClick={() => handleStockXListing(item)}
                            className="px-2 py-1 bg-green-600 hover:bg-green-700 rounded text-white text-xs font-medium"
                            title="List on StockX"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </button>
                        )}
                        <button className="p-1.5 hover:bg-gray-800/50 rounded transition-colors" title="View Details">
                          <Eye className="w-3.5 h-3.5 text-blue-400" />
                        </button>
                        <button className="p-1.5 hover:bg-gray-800/50 rounded transition-colors" title="Edit">
                          <Edit3 className="w-3.5 h-3.5 text-purple-400" />
                        </button>
                      </div>
                    </td>
                    </tr>
                  );
                })}
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
        </>
      )}

      {/* StockX Management Tab */}
      {activeTab === 'stockx' && (
        <div className="modern-card">
          <div className="mb-6">
            <h2 className="text-2xl font-bold modern-heading">StockX Listing Management</h2>
            <p className="modern-subheading">Monitor performance, adjust prices, and optimize your StockX presence</p>
          </div>

          {listingsLoading ? (
            <div className="flex justify-center items-center py-20">
              <div className="text-center">
                <RefreshCw className="w-12 h-12 animate-spin text-purple-400 mx-auto mb-4" />
                <p className="modern-heading text-lg">Loading StockX listings...</p>
              </div>
            </div>
          ) : stockxListings.length === 0 ? (
            <div className="text-center py-12">
              <ExternalLink className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium modern-heading mb-2">No StockX listings found</h3>
              <p className="modern-subheading">
                You don't have any active listings on StockX, or the API is currently unavailable.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto max-h-96 overflow-y-auto border border-gray-800/50 rounded-lg">
              <table className="modern-table">
                <thead className="sticky top-0 bg-gray-900/95 backdrop-blur-sm z-10">
                  <tr>
                    <th>Product</th>
                    <th>Size</th>
                    <th>Current Ask</th>
                    <th>Market Price</th>
                    <th>Status</th>
                    <th>Performance</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {stockxListings.map((listing, index) => (
                    <tr key={listing.listingId || index}>
                      <td>
                        <div className="font-medium modern-heading text-sm">
                          {listing.product?.productName || listing.product?.name || listing.productName || listing.variant?.product?.name || 'Unknown Product'}
                        </div>
                      </td>
                      <td>
                        <span className="px-2 py-1 rounded-lg bg-gray-800/50 text-xs font-medium">
                          {listing.size || listing.variant?.size || listing.variant?.variantValue || 'N/A'}
                        </span>
                      </td>
                      <td>
                        <span className="font-medium text-green-400 text-lg">
                          €{listing.askPrice || listing.amount || 'N/A'}
                        </span>
                      </td>
                      <td>
                        <div className="text-sm">
                          <div className="text-white">€{(parseFloat(listing.askPrice || '0') * 0.95).toFixed(0)}</div>
                          <div className="text-xs text-gray-400">Market avg</div>
                        </div>
                      </td>
                      <td>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          listing.status === 'ACTIVE' ? 'bg-green-500/20 text-green-400' :
                          listing.status === 'PENDING' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {listing.status || 'UNKNOWN'}
                        </span>
                      </td>
                      <td>
                        <div className="text-sm">
                          <div className="flex items-center gap-1">
                            <TrendingUp className="w-3 h-3 text-green-400" />
                            <span className="text-green-400">+5%</span>
                          </div>
                          <div className="text-xs text-gray-400">vs market</div>
                        </div>
                      </td>
                      <td>
                        <div className="flex space-x-1">
                          <button className="px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white text-xs" title="Adjust Price">
                            €
                          </button>
                          <button className="p-1.5 hover:bg-gray-800/50 rounded transition-colors" title="Analytics">
                            <TrendingUp className="w-3.5 h-3.5 text-purple-400" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Alias Listings Tab */}
      {activeTab === 'alias' && (
        <div className="modern-card">
          <div className="mb-6">
            <h2 className="text-2xl font-bold modern-heading">Current Alias Listings</h2>
            <p className="modern-subheading">View and manage your active Alias listings</p>
          </div>

          {listingsLoading ? (
            <div className="flex justify-center items-center py-20">
              <div className="text-center">
                <RefreshCw className="w-12 h-12 animate-spin text-purple-400 mx-auto mb-4" />
                <p className="modern-heading text-lg">Loading Alias listings...</p>
              </div>
            </div>
          ) : aliasListings.length === 0 ? (
            <div className="text-center py-12">
              <Tag className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium modern-heading mb-2">No Alias listings found</h3>
              <p className="modern-subheading">
                You don't have any active listings on Alias, or the API is currently unavailable.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto max-h-96 overflow-y-auto border border-gray-800/50 rounded-lg">
              <table className="modern-table">
                <thead className="sticky top-0 bg-gray-900/95 backdrop-blur-sm z-10">
                  <tr>
                    <th>Listing ID</th>
                    <th>Product</th>
                    <th>Size</th>
                    <th>Ask Price</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {aliasListings.map((listing, index) => (
                    <tr key={listing.listingId || index}>
                      <td>
                        <span className="font-mono text-xs bg-gray-800/50 px-2 py-1 rounded">
                          {listing.listingId?.slice(-8) || 'N/A'}
                        </span>
                      </td>
                      <td>
                        <div className="font-medium modern-heading text-sm">
                          {listing.product?.name || listing.productName || 'Unknown Product'}
                        </div>
                      </td>
                      <td>
                        <span className="px-2 py-1 rounded-lg bg-gray-800/50 text-xs font-medium">
                          {listing.size || 'N/A'}
                        </span>
                      </td>
                      <td>
                        <span className="font-medium text-blue-400">
                          €{listing.askPrice || listing.amount || 'N/A'}
                        </span>
                      </td>
                      <td>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          listing.status === 'ACTIVE' ? 'bg-green-500/20 text-green-400' :
                          listing.status === 'PENDING' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {listing.status || 'UNKNOWN'}
                        </span>
                      </td>
                      <td>
                        <span className="text-sm modern-subheading">
                          {listing.createdAt ? new Date(listing.createdAt).toLocaleDateString() : 'N/A'}
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
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModernInventory;