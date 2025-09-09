import { useEffect, useState } from 'react';
import { Package, Search, Filter, RefreshCw, TrendingUp, CheckCircle, Star, ExternalLink, Edit, X, Save } from 'lucide-react';

interface InventoryItem {
  id: string;
  product_id: string;
  product_name: string;
  brand_name: string | null;
  category_name: string;
  size: string;
  quantity: number;
  purchase_price: number | null;
  status: string;
  created_at: string;
  external_ids?: { stockx_listing_id?: string; alias_listing_id?: string };
}

interface InventoryStats {
  total: number;
  in_stock: number;
  listed_stockx: number;
  listed_alias: number;
}

type TabType = 'all' | 'stockx' | 'alias';

const Inventory = () => {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('all');
  const [stats, setStats] = useState<InventoryStats>({ total: 0, in_stock: 0, listed_stockx: 0, listed_alias: 0 });
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [actionLoading, setActionLoading] = useState<{[key: string]: boolean}>({});
  const [editItem, setEditItem] = useState<InventoryItem | null>(null);
  const [editForm, setEditForm] = useState<Partial<InventoryItem>>({});

  // Tab definitions
  const tabs = [
    { 
      id: 'all' as const, 
      label: 'All Products', 
      icon: Package,
      description: 'All inventory items'
    },
    { 
      id: 'stockx' as const, 
      label: 'StockX Listings', 
      icon: ExternalLink,
      description: 'Active StockX listings'
    },
    { 
      id: 'alias' as const, 
      label: 'Alias Listings', 
      icon: TrendingUp,
      description: 'Active Alias listings'
    }
  ];

  const fetchInventory = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      let endpoint = '';
      
      let items: InventoryItem[] = [];
      let allInventoryItems: InventoryItem[] = [];
      
      // Always fetch all inventory items for stats calculation
      let skip = 0;
      const limit = 1000;
      let hasMore = true;
      
      while (hasMore) {
        const inventoryResponse = await fetch(`http://localhost:8000/api/v1/inventory/items?limit=${limit}&skip=${skip}`);
        if (inventoryResponse.ok) {
          const inventoryData = await inventoryResponse.json();
          const pageItems = inventoryData.items || [];
          allInventoryItems.push(...pageItems);
          
          hasMore = inventoryData.pagination?.has_more || false;
          skip += limit;
          
          // Safety break to avoid infinite loop
          if (skip > 10000) break;
        } else {
          break;
        }
      }
      
      if (activeTab === 'all') {
        // For 'All' tab: use all inventory items and add StockX listings
        items = [...allInventoryItems];
        
        // Then get StockX listings and add those that are physically in stock
        try {
          const stockxResponse = await fetch('http://localhost:8000/api/v1/inventory/stockx-listings?limit=1000');
          if (stockxResponse.ok) {
            const stockxData = await stockxResponse.json();
            const stockxListings = stockxData.data?.listings || [];
            
            // Transform and add StockX items that are physically in stock
            const stockxItems = stockxListings.map((listing: any) => ({
              id: `stockx-${listing.listingId || listing.id || Math.random()}`,
              product_id: listing.productId || '',
              product_name: listing.productName || listing.product?.name || 'Unknown Product',
              brand_name: listing.brand || 'Unknown Brand',
              category_name: 'StockX (In Stock)',
              size: listing.size || listing.variant?.variantValue || 'N/A',
              quantity: 1,
              purchase_price: parseFloat(listing.askPrice || listing.amount || '0'),
              status: 'stockx_listed', // Special status for StockX items in all view
              created_at: listing.createdAt || listing.stockx_created_at || new Date().toISOString(),
              external_ids: {
                stockx_listing_id: listing.listingId
              }
            }));
            
            // Add StockX items to the combined list
            items = [...items, ...stockxItems];
          }
        } catch (stockxError) {
          console.warn('Failed to load StockX listings for All view:', stockxError);
          // Continue with just local inventory if StockX fails
        }
        
      } else if (activeTab === 'stockx') {
        endpoint = 'http://localhost:8000/api/v1/inventory/stockx-listings?limit=1000';
      } else if (activeTab === 'alias') {
        endpoint = 'http://localhost:8000/api/v1/inventory/alias-listings?limit=1000';
      } else {
        endpoint = 'http://localhost:8000/api/v1/inventory/items?limit=1000';
      }
      
      // Only fetch if we haven't already loaded items (for 'all' tab)
      if (activeTab !== 'all') {

        const response = await fetch(endpoint);
        if (!response.ok) {
          throw new Error(`Failed to fetch inventory: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Handle different response formats for different endpoints
        if (activeTab === 'stockx' || activeTab === 'alias') {
          // StockX and Alias endpoints return data.data.listings
          items = data.data?.listings || [];
          
          // Transform StockX/Alias listings to match InventoryItem interface
          items = items.map((listing: any) => ({
            id: listing.listingId || listing.id,
            product_id: listing.productId || '',
            product_name: listing.productName || listing.product?.name || 'Unknown Product',
            brand_name: listing.brand || 'Unknown Brand',
            category_name: 'StockX/Alias',
            size: listing.size || listing.variant?.variantValue || 'N/A',
            quantity: 1,
            purchase_price: parseFloat(listing.askPrice || listing.amount || '0'),
            status: activeTab === 'stockx' ? 'listed' : 'listed_alias',
            created_at: listing.createdAt || listing.stockx_created_at || new Date().toISOString(),
            external_ids: {
              stockx_listing_id: activeTab === 'stockx' ? listing.listingId : undefined
            }
          }));
        } else {
          // Inventory items endpoint returns data.items
          items = data.items || [];
        }
      }
      
      // Set items for all tabs
      setItems(items);
      
      // Calculate stats based on all inventory items
      await calculateStats(allInventoryItems);
      
    } catch (err) {
      console.error('Error fetching inventory:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch inventory');
    } finally {
      setIsLoading(false);
    }
  };

  const calculateStats = async (allInventoryItems: InventoryItem[]) => {
    // Get StockX listings count
    let stockxListingsCount = 0;
    try {
      const stockxResponse = await fetch('http://localhost:8000/api/v1/inventory/stockx-listings?limit=1000');
      if (stockxResponse.ok) {
        const stockxData = await stockxResponse.json();
        stockxListingsCount = stockxData.data?.listings?.length || 0;
      }
    } catch (error) {
      console.warn('Failed to load StockX listings for stats:', error);
    }
    
    const newStats = {
      total: allInventoryItems.length,
      in_stock: allInventoryItems.filter(item => item.status === 'in_stock').length,
      listed_stockx: stockxListingsCount,
      listed_alias: allInventoryItems.filter(item => item.status === 'listed_alias').length,
    };
    setStats(newStats);
  };

  const filteredItems = items.filter(item => {
    // Search filter
    const matchesSearch = item.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.brand_name && item.brand_name.toLowerCase().includes(searchTerm.toLowerCase()));
    
    // Status filter
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
    
    // Tab-based filter
    let matchesTab = true;
    if (activeTab === 'stockx') {
      // Show only items with StockX listing IDs
      matchesTab = item.external_ids?.stockx_listing_id != null;
    } else if (activeTab === 'alias') {
      // Show only items with Alias listing IDs (mock for now)
      matchesTab = item.status === 'listed_alias' || item.external_ids?.alias_listing_id != null;
    }
    // For 'all' tab, show everything (matchesTab stays true)
    
    return matchesSearch && matchesStatus && matchesTab;
  });

  const getActiveTabCount = () => {
    switch (activeTab) {
      case 'stockx': return stats.listed_stockx;
      case 'alias': return stats.listed_alias;
      case 'all':
      default: return stats.total;
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      'in_stock': { label: 'In Stock', color: 'bg-green-600' },
      'listed': { label: 'StockX', color: 'bg-blue-600' },
      'stockx_listed': { label: 'StockX (In Stock)', color: 'bg-blue-500' },
      'listed_alias': { label: 'Alias', color: 'bg-purple-600' },
      'sold': { label: 'Sold', color: 'bg-gray-600' },
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || 
                  { label: status, color: 'bg-gray-500' };
    
    return (
      <span className={`px-2 py-1 text-xs font-mono text-white rounded ${config.color}`}>
        {config.label}
      </span>
    );
  };

  const formatPrice = (price: number | null) => {
    if (!price) return 'N/A';
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR'
    }).format(price);
  };

  const handleStatusChange = async (itemId: string, newStatus: string) => {
    setActionLoading(prev => ({ ...prev, [itemId]: true }));
    try {
      const response = await fetch(`http://localhost:8000/api/v1/inventory/items/${itemId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Status update failed: ${errorText}`);
      }

      // Refresh inventory after status change
      await fetchInventory();
      
    } catch (error) {
      console.error(`Status update failed:`, error);
      setError(`Status update failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [itemId]: false }));
    }
  };

  const openEditModal = (item: InventoryItem) => {
    setEditItem(item);
    setEditForm({
      product_name: item.product_name,
      brand_name: item.brand_name,
      size: item.size,
      quantity: item.quantity,
      purchase_price: item.purchase_price,
      status: item.status
    });
  };

  const closeEditModal = () => {
    setEditItem(null);
    setEditForm({});
  };

  const handleEditFormChange = (field: keyof InventoryItem, value: any) => {
    setEditForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const saveEditChanges = async () => {
    if (!editItem) return;

    try {
      const response = await fetch(`http://localhost:8000/api/v1/inventory/items/${editItem.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editForm),
      });

      if (!response.ok) {
        throw new Error(`Update failed: ${response.statusText}`);
      }

      // Refresh inventory after update
      await fetchInventory();
      closeEditModal();
      
    } catch (error) {
      console.error('Edit failed:', error);
      setError(`Edit failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, [activeTab]);

  useEffect(() => {
    fetchInventory();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Package className="w-16 h-16 text-blue-400 animate-pulse mx-auto mb-4" />
          <p className="modern-heading text-lg">Loading Inventory...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8 space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="modern-heading text-3xl mb-2">
            Inventory Management
          </h1>
          <p className="modern-subheading">
            {tabs.find(t => t.id === activeTab)?.description}
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={fetchInventory}
            className="modern-button-outline flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="modern-card px-6 py-3">
          <div className="flex items-center space-x-4">
            <div className="p-2 rounded-xl bg-gray-500/10">
              <Package className="w-5 h-5 text-gray-400" />
            </div>
            <div>
              <div className="text-xl font-bold modern-heading">
                {stats.total}
              </div>
              <div className="text-xs modern-subheading">
                Total Items
              </div>
            </div>
          </div>
        </div>
        <div className="modern-card px-6 py-3">
          <div className="flex items-center space-x-4">
            <div className="p-2 rounded-xl bg-green-500/10">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <div className="text-xl font-bold modern-heading">
                {stats.in_stock}
              </div>
              <div className="text-xs modern-subheading">
                In Stock
              </div>
            </div>
          </div>
        </div>
        <div className="modern-card px-6 py-3">
          <div className="flex items-center space-x-4">
            <div className="p-2 rounded-xl bg-blue-500/10">
              <TrendingUp className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="text-xl font-bold modern-heading">
                {stats.listed_stockx}
              </div>
              <div className="text-xs modern-subheading">
                StockX Listings
              </div>
            </div>
          </div>
        </div>
        <div className="modern-card px-6 py-3">
          <div className="flex items-center space-x-4">
            <div className="p-2 rounded-xl bg-purple-500/10">
              <Star className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <div className="text-xl font-bold modern-heading">
                {stats.listed_alias}
              </div>
              <div className="text-xs modern-subheading">
                Alias Listings
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 bg-gray-800/50 rounded-lg p-1 mb-6">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;
          const count = getActiveTabCount();
          
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all ${
                isActive
                  ? 'bg-purple-500/20 text-purple-400 shadow-lg'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
              }`}
            >
              <div className="flex items-center justify-center space-x-2">
                <Icon className="w-5 h-5" />
                <span>{tab.label}</span>
                {isActive && (
                  <span className="bg-purple-400 text-purple-900 px-2 py-1 rounded-full text-xs font-bold">
                    {count}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Search & Filter */}
      <div className="flex justify-between items-center mb-6">
        <div></div>
        <div className="flex items-center space-x-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search products..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="modern-input pl-10 w-64"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="modern-input w-48"
          >
            <option value="all">All Status</option>
            <option value="in_stock">In Stock</option>
            <option value="sold">Sold</option>
            <option value="listed">Listed</option>
            <option value="presale">Presale</option>
            <option value="preorder">Preorder</option>
            <option value="canceled">Canceled</option>
          </select>
          <div className="flex items-center space-x-2 text-sm text-gray-400">
            <Filter className="w-4 h-4" />
            <span>{filteredItems.length} of {items.length}</span>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-900/20 border border-red-500 rounded-lg">
          <div className="p-4">
            <div className="text-red-400 text-sm">ERROR: {error}</div>
          </div>
        </div>
      )}

      {/* Items Table */}
      <div className="modern-card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 px-4 text-gray-300 text-sm font-medium">PRODUCT</th>
                <th className="text-left py-3 px-4 text-gray-300 text-sm font-medium">BRAND</th>
                <th className="text-left py-3 px-4 text-gray-300 text-sm font-medium">SIZE</th>
                <th className="text-left py-3 px-4 text-gray-300 text-sm font-medium">PRICE</th>
                <th className="text-left py-3 px-4 text-gray-300 text-sm font-medium">STATUS</th>
                <th className="text-left py-3 px-4 text-gray-300 text-sm font-medium">QUANTITY</th>
                <th className="text-left py-3 px-4 text-gray-300 text-sm font-medium">CHANGE STATUS</th>
                <th className="text-left py-3 px-4 text-gray-300 text-sm font-medium">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8">
                    <div className="text-gray-400">
                      {searchTerm ? 'No items found for search term' : 'No items found'}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredItems.slice(0, 50).map((item) => (
                  <tr key={item.id} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-medium text-gray-100 text-sm">
                        {item.product_name}
                      </div>
                      {item.external_ids?.stockx_listing_id && (
                        <div className="text-xs text-gray-400 mt-1">
                          StockX: {item.external_ids.stockx_listing_id.slice(0, 8)}...
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-blue-400 font-medium text-sm">
                        {item.brand_name || 'Unknown'}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-gray-300 text-sm">
                        {item.size || 'N/A'}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-gray-100 text-sm">
                        {formatPrice(item.purchase_price)}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(item.status)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-gray-100 text-sm">
                        {item.quantity}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <select
                        value={item.status}
                        onChange={(e) => handleStatusChange(item.id, e.target.value)}
                        disabled={actionLoading[item.id]}
                        className="modern-input text-sm w-32 disabled:opacity-50"
                      >
                        <option value="in_stock">In Stock</option>
                        <option value="sold">Sold</option>
                        <option value="listed">Listed</option>
                        <option value="presale">Presale</option>
                        <option value="preorder">Preorder</option>
                        <option value="canceled">Canceled</option>
                      </select>
                      {actionLoading[item.id] && (
                        <RefreshCw className="w-4 h-4 text-blue-400 animate-spin ml-2 inline" />
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => openEditModal(item)}
                        className="flex items-center space-x-1 px-2 py-1 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-md transition-colors"
                      >
                        <Edit className="w-3 h-3" />
                        <span>Edit</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {filteredItems.length > 50 && (
          <div className="border-t border-gray-700 p-4">
            <div className="text-center text-gray-400 text-sm">
              Showing first 50 of {filteredItems.length} items
            </div>
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {editItem && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4 border border-gray-600">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Edit Item</h2>
              <button
                onClick={closeEditModal}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Product Name
                </label>
                <input
                  type="text"
                  value={editForm.product_name || ''}
                  onChange={(e) => handleEditFormChange('product_name', e.target.value)}
                  className="modern-input w-full"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Brand
                </label>
                <input
                  type="text"
                  value={editForm.brand_name || ''}
                  onChange={(e) => handleEditFormChange('brand_name', e.target.value)}
                  className="modern-input w-full"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Size
                  </label>
                  <input
                    type="text"
                    value={editForm.size || ''}
                    onChange={(e) => handleEditFormChange('size', e.target.value)}
                    className="modern-input w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Quantity
                  </label>
                  <input
                    type="number"
                    value={editForm.quantity || ''}
                    onChange={(e) => handleEditFormChange('quantity', parseInt(e.target.value))}
                    className="modern-input w-full"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Purchase Price (EUR)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={editForm.purchase_price || ''}
                  onChange={(e) => handleEditFormChange('purchase_price', parseFloat(e.target.value))}
                  className="modern-input w-full"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Status
                </label>
                <select
                  value={editForm.status || ''}
                  onChange={(e) => handleEditFormChange('status', e.target.value)}
                  className="modern-input w-full"
                >
                  <option value="in_stock">In Stock</option>
                  <option value="sold">Sold</option>
                  <option value="listed">Listed</option>
                  <option value="presale">Presale</option>
                  <option value="preorder">Preorder</option>
                  <option value="canceled">Canceled</option>
                </select>
              </div>
            </div>
            
            <div className="flex space-x-3 mt-6">
              <button
                onClick={closeEditModal}
                className="flex-1 px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveEditChanges}
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 rounded-md transition-colors flex items-center justify-center space-x-1"
              >
                <Save className="w-4 h-4" />
                <span>Save Changes</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Inventory;