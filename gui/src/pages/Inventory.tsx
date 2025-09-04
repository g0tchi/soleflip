import { useEffect, useState } from 'react';
import { Package, Search, Filter, RefreshCw, ExternalLink, TrendingUp, MoreVertical, PlusCircle, MinusCircle, Zap, AlertTriangle, CheckCircle, Star } from 'lucide-react';

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
  external_ids?: { stockx_listing_id?: string };
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
  const [actionLoading, setActionLoading] = useState<{[key: string]: boolean}>({});
  const [actionMenuOpen, setActionMenuOpen] = useState<string | null>(null);

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
      
      // Use different endpoints for different tabs
      if (activeTab === 'stockx') {
        // Use StockX listings endpoint for StockX tab
        endpoint = 'http://localhost:8000/api/v1/inventory/stockx-listings?limit=100';
      } else if (activeTab === 'alias') {
        // Use Alias listings endpoint for Alias tab
        endpoint = 'http://localhost:8000/api/v1/inventory/alias-listings?limit=100';
      } else {
        // Use inventory items endpoint for "All Products" tab
        endpoint = 'http://localhost:8000/api/v1/inventory/items?limit=100';
      }

      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error(`Failed to fetch inventory: ${response.statusText}`);
      }
      
      const data = await response.json();
      let items = [];
      
      // Handle different response formats for different endpoints
      if (activeTab === 'stockx' || activeTab === 'alias') {
        // StockX and Alias endpoints return data.data.listings
        items = data.data?.listings || [];
        
        // Transform StockX/Alias listings to match InventoryItem interface
        items = items.map(listing => ({
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
      
      setItems(items);
      
      // Calculate stats
      calculateStats(items);
      
    } catch (err) {
      console.error('Error fetching inventory:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch inventory');
    } finally {
      setIsLoading(false);
    }
  };

  const calculateStats = (inventoryItems: InventoryItem[]) => {
    const newStats = {
      total: inventoryItems.length,
      in_stock: inventoryItems.filter(item => item.status === 'in_stock').length,
      listed_stockx: inventoryItems.filter(item => item.status === 'listed').length,
      listed_alias: inventoryItems.filter(item => item.status === 'listed_alias').length,
    };
    setStats(newStats);
  };

  const filteredItems = items.filter(item => 
    item.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (item.brand_name && item.brand_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

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

  const handleStockXAction = async (itemId: string, action: 'create' | 'mark-presale' | 'unmark-presale' | 'sync', listingId?: string) => {
    setActionLoading(prev => ({ ...prev, [itemId]: true }));
    try {
      let endpoint = '';
      let method = 'POST';
      
      switch (action) {
        case 'create':
          endpoint = `http://localhost:8000/api/v1/inventory/items/${itemId}/stockx-listing`;
          break;
        case 'mark-presale':
          endpoint = `http://localhost:8000/api/v1/inventory/stockx-listings/${listingId}/mark-presale`;
          break;
        case 'unmark-presale':
          endpoint = `http://localhost:8000/api/v1/inventory/stockx-listings/${listingId}/unmark-presale`;
          method = 'DELETE';
          break;
        case 'sync':
          endpoint = `http://localhost:8000/api/v1/inventory/items/${itemId}/sync-from-stockx`;
          break;
      }

      const response = await fetch(endpoint, { method });
      if (!response.ok) {
        throw new Error(`${action} failed: ${response.statusText}`);
      }

      // Refresh inventory after action
      await fetchInventory();
      setActionMenuOpen(null);
      
    } catch (err) {
      console.error(`StockX ${action} failed:`, err);
      setError(err instanceof Error ? err.message : `${action} failed`);
    } finally {
      setActionLoading(prev => ({ ...prev, [itemId]: false }));
    }
  };

  const getStockXActions = (item: InventoryItem) => {
    const stockxListingId = item.external_ids?.stockx_listing_id;
    const isListed = item.status === 'listed';
    const canList = ['in_stock', 'presale'].includes(item.status);
    
    const actions = [];
    
    if (!isListed && canList) {
      actions.push({
        label: 'List on StockX',
        icon: PlusCircle,
        action: () => handleStockXAction(item.id, 'create'),
        color: 'text-green-400'
      });
    }
    
    if (isListed && stockxListingId) {
      actions.push(
        {
          label: 'Mark as Presale',
          icon: AlertTriangle,
          action: () => handleStockXAction(item.id, 'mark-presale', stockxListingId),
          color: 'text-orange-400'
        },
        {
          label: 'Remove Presale',
          icon: MinusCircle,
          action: () => handleStockXAction(item.id, 'unmark-presale', stockxListingId),
          color: 'text-red-400'
        }
      );
    }
    
    actions.push({
      label: 'Sync from StockX',
      icon: RefreshCw,
      action: () => handleStockXAction(item.id, 'sync'),
      color: 'text-blue-400'
    });
    
    return actions;
  };

  useEffect(() => {
    fetchInventory();
  }, [activeTab]);

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

      {/* Tab Navigation & Search */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div className="flex space-x-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const count = getActiveTabCount();
            
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 text-sm ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="font-medium">{tab.label}</span>
                {isActive && (
                  <span className="bg-white text-blue-600 px-2 py-1 rounded-full text-xs font-bold">
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
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
                <th className="text-left py-3 px-4 text-gray-300 text-sm font-medium">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8">
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
                    <td className="py-3 px-4 relative">
                      <button
                        onClick={() => setActionMenuOpen(actionMenuOpen === item.id ? null : item.id)}
                        disabled={actionLoading[item.id]}
                        className="p-2 hover:bg-gray-600 rounded transition-colors disabled:opacity-50"
                      >
                        {actionLoading[item.id] ? (
                          <RefreshCw className="w-4 h-4 text-gray-300 animate-spin" />
                        ) : (
                          <MoreVertical className="w-4 h-4 text-gray-300" />
                        )}
                      </button>
                      
                      {actionMenuOpen === item.id && (
                        <div className="absolute right-0 top-full mt-1 bg-gray-700 border border-gray-600 rounded-md shadow-lg z-10 min-w-48">
                          {getStockXActions(item).map((action, index) => {
                            const Icon = action.icon;
                            return (
                              <button
                                key={index}
                                onClick={action.action}
                                className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-600 transition-colors flex items-center space-x-2 ${action.color}`}
                              >
                                <Icon className="w-4 h-4" />
                                <span>{action.label}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
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
    </div>
  );
};

export default Inventory;