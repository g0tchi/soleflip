import { useState, useEffect } from 'react';
import {
  TrendingUp,
  Filter,
  RefreshCw,
  Download,
  Search,
  SlidersHorizontal,
  Zap,
  Target,
  DollarSign
} from 'lucide-react';
import { Button, Card, Heading, Text, Grid } from '../ui';
import { QuickFlipOpportunityCard } from './QuickFlipOpportunityCard';

interface QuickFlipOpportunity {
  product_id: string;
  product_name: string;
  product_sku: string;
  brand_name: string;
  buy_price: number;
  buy_source: string;
  buy_supplier: string;
  buy_url?: string;
  buy_stock_qty?: number;
  sell_price: number;
  gross_profit: number;
  profit_margin: number;
  roi: number;
}

interface QuickFlipSummary {
  total_opportunities: number;
  avg_profit_margin: number;
  avg_gross_profit: number;
  best_opportunity?: QuickFlipOpportunity;
  sources_breakdown: Record<string, {
    count: number;
    avg_profit_margin: number;
    best_margin: number;
  }>;
}

interface Filters {
  min_profit_margin: number;
  min_gross_profit: number;
  max_buy_price?: number;
  sources: string[];
  search: string;
}

export const QuickFlipDashboard = () => {
  const [opportunities, setOpportunities] = useState<QuickFlipOpportunity[]>([]);
  const [summary, setSummary] = useState<QuickFlipSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [actedOpportunities, setActedOpportunities] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    min_profit_margin: 15,
    min_gross_profit: 25,
    max_buy_price: undefined,
    sources: [],
    search: ''
  });

  const fetchOpportunities = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        min_profit_margin: filters.min_profit_margin.toString(),
        min_gross_profit: filters.min_gross_profit.toString(),
        limit: '50'
      });

      if (filters.max_buy_price) {
        params.append('max_buy_price', filters.max_buy_price.toString());
      }

      if (filters.sources.length > 0) {
        params.append('sources', filters.sources.join(','));
      }

      const response = await fetch(`http://127.0.0.1:8000/api/v1/quickflip/opportunities?${params}`);
      const data = await response.json();

      // Apply local search filter
      let filteredData = data;
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        filteredData = data.filter((opp: QuickFlipOpportunity) =>
          opp.product_name.toLowerCase().includes(searchLower) ||
          opp.brand_name.toLowerCase().includes(searchLower) ||
          opp.product_sku.toLowerCase().includes(searchLower)
        );
      }

      setOpportunities(filteredData);
    } catch (error) {
      console.error('Failed to fetch opportunities:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/quickflip/opportunities/summary');
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  };

  const handleMarkActed = async (productId: string, source: string) => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/quickflip/opportunities/mark-acted', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: productId,
          source: source,
          action: 'purchased'
        })
      });

      if (response.ok) {
        const key = `${productId}-${source}`;
        setActedOpportunities(prev => new Set([...prev, key]));
      }
    } catch (error) {
      console.error('Failed to mark opportunity as acted:', error);
    }
  };

  const availableSources = summary ? Object.keys(summary.sources_breakdown) : [];

  useEffect(() => {
    fetchOpportunities();
    fetchSummary();
  }, []);

  useEffect(() => {
    fetchOpportunities();
  }, [filters]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Heading variant="display" className="flex items-center gap-3">
            <Zap className="w-8 h-8 text-yellow-400" />
            QuickFlip Opportunities
          </Heading>
          <Text variant="body" className="mt-1 text-gray-400">
            Discover profitable arbitrage opportunities in real-time
          </Text>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            icon={SlidersHorizontal}
          >
            Filters
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              fetchOpportunities();
              fetchSummary();
            }}
            isLoading={loading}
            icon={RefreshCw}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <Grid className="grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <Text variant="caption">Total Opportunities</Text>
                <Heading variant="title" className="text-yellow-400">
                  {summary.total_opportunities}
                </Heading>
              </div>
              <Target className="w-8 h-8 text-yellow-400 opacity-60" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <Text variant="caption">Avg Profit Margin</Text>
                <Heading variant="title" className="text-green-400">
                  {summary.avg_profit_margin.toFixed(1)}%
                </Heading>
              </div>
              <TrendingUp className="w-8 h-8 text-green-400 opacity-60" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <Text variant="caption">Avg Gross Profit</Text>
                <Heading variant="title" className="text-green-400">
                  €{summary.avg_gross_profit.toFixed(0)}
                </Heading>
              </div>
              <DollarSign className="w-8 h-8 text-green-400 opacity-60" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <Text variant="caption">Data Sources</Text>
                <Heading variant="title" className="text-purple-400">
                  {Object.keys(summary.sources_breakdown).length}
                </Heading>
              </div>
              <Download className="w-8 h-8 text-purple-400 opacity-60" />
            </div>
          </Card>
        </Grid>
      )}

      {/* Filters Panel */}
      {showFilters && (
        <Card className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Min Profit Margin (%)
              </label>
              <input
                type="number"
                value={filters.min_profit_margin}
                onChange={(e) => setFilters(prev => ({ ...prev, min_profit_margin: Number(e.target.value) }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                min="0"
                max="100"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Min Gross Profit (€)
              </label>
              <input
                type="number"
                value={filters.min_gross_profit}
                onChange={(e) => setFilters(prev => ({ ...prev, min_gross_profit: Number(e.target.value) }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                min="0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max Buy Price (€)
              </label>
              <input
                type="number"
                value={filters.max_buy_price || ''}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  max_buy_price: e.target.value ? Number(e.target.value) : undefined
                }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                placeholder="No limit"
                min="0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Sources
              </label>
              <select
                multiple
                value={filters.sources}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  sources: Array.from(e.target.selectedOptions, option => option.value)
                }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
              >
                {availableSources.map(source => (
                  <option key={source} value={source}>
                    {source.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Search Products
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                placeholder="Search by product name, brand, or SKU..."
                className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
              />
            </div>
          </div>
        </Card>
      )}

      {/* Opportunities Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <Text variant="body" className="font-semibold">
            {opportunities.length} Opportunities Found
          </Text>
          {loading && (
            <div className="flex items-center gap-2 text-yellow-400">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <Text variant="body">Loading...</Text>
            </div>
          )}
        </div>

        {opportunities.length > 0 ? (
          <Grid className="grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {opportunities.map((opportunity) => {
              const key = `${opportunity.product_id}-${opportunity.buy_source}`;
              return (
                <QuickFlipOpportunityCard
                  key={key}
                  opportunity={opportunity}
                  onMarkActed={handleMarkActed}
                  isActed={actedOpportunities.has(key)}
                />
              );
            })}
          </Grid>
        ) : (
          <Card className="p-8 text-center">
            <Target className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <Heading variant="title" className="text-gray-400 mb-2">
              No Opportunities Found
            </Heading>
            <Text variant="body" className="text-gray-400">
              Try adjusting your filters or check back later for new opportunities.
            </Text>
          </Card>
        )}
      </div>
    </div>
  );
};