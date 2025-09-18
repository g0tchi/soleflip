import { useState } from 'react';
import {
  TrendingUp,
  ExternalLink,
  Package,
  CheckCircle,
  AlertCircle,
  Clock,
  Tag
} from 'lucide-react';
import { Button, Card, Text } from '../ui';

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

interface QuickFlipOpportunityCardProps {
  opportunity: QuickFlipOpportunity;
  onMarkActed: (productId: string, source: string) => void;
  isActed?: boolean;
}

export const QuickFlipOpportunityCard = ({
  opportunity,
  onMarkActed,
  isActed = false
}: QuickFlipOpportunityCardProps) => {
  const [isMarking, setIsMarking] = useState(false);

  const handleMarkActed = async () => {
    setIsMarking(true);
    try {
      await onMarkActed(opportunity.product_id, opportunity.buy_source);
    } finally {
      setIsMarking(false);
    }
  };

  const getProfitColor = (margin: number) => {
    if (margin >= 50) return 'text-green-400';
    if (margin >= 25) return 'text-green-300';
    if (margin >= 15) return 'text-yellow-300';
    return 'text-gray-300';
  };

  const getProfitBadgeColor = (margin: number) => {
    if (margin >= 50) return 'bg-green-500/20 text-green-300 border-green-500/30';
    if (margin >= 25) return 'bg-green-500/20 text-green-300 border-green-500/30';
    if (margin >= 15) return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
    return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
  };

  return (
    <Card
      variant={isActed ? "default" : "elevated"}
      className={`relative transition-all duration-200 hover:scale-[1.02] ${
        isActed ? 'opacity-60 border-green-500/30' : ''
      }`}
    >
      {isActed && (
        <div className="absolute top-3 right-3">
          <CheckCircle className="w-5 h-5 text-green-400" />
        </div>
      )}

      <div className="p-4 space-y-4">
        {/* Product Header */}
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <Text variant="body" className="font-semibold truncate">
              {opportunity.product_name}
            </Text>
            <div className="flex items-center gap-2 mt-1">
              <Text variant="caption">{opportunity.brand_name}</Text>
              <span className="text-gray-500">•</span>
              <Text variant="caption">{opportunity.product_sku}</Text>
            </div>
          </div>

          {/* Profit Badge */}
          <div className={`px-2 py-1 rounded border text-xs font-medium ${getProfitBadgeColor(opportunity.profit_margin)}`}>
            +{opportunity.profit_margin.toFixed(1)}%
          </div>
        </div>

        {/* Price Comparison */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <Text variant="caption" className="flex items-center gap-1">
              <Tag className="w-3 h-3" />
              Buy Price
            </Text>
            <Text variant="body" className="font-semibold">
              €{opportunity.buy_price.toFixed(2)}
            </Text>
            <Text variant="caption">{opportunity.buy_supplier}</Text>
          </div>

          <div className="space-y-1">
            <Text variant="caption" className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              Sell Price
            </Text>
            <Text variant="body" className="font-semibold">
              €{opportunity.sell_price.toFixed(2)}
            </Text>
            <Text variant="caption">StockX Avg</Text>
          </div>
        </div>

        {/* Profit Metrics */}
        <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
          <div className="text-center">
            <Text variant="caption">Gross Profit</Text>
            <Text variant="body" className={`font-semibold ${getProfitColor(opportunity.profit_margin)}`}>
              €{opportunity.gross_profit.toFixed(2)}
            </Text>
          </div>
          <div className="text-center">
            <Text variant="caption">ROI</Text>
            <Text variant="body" className={`font-semibold ${getProfitColor(opportunity.profit_margin)}`}>
              {opportunity.roi.toFixed(1)}%
            </Text>
          </div>
        </div>

        {/* Source & Stock Info */}
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded">
              {opportunity.buy_source.toUpperCase()}
            </span>
            {opportunity.buy_stock_qty && (
              <span className="flex items-center gap-1 text-gray-400">
                <Package className="w-3 h-3" />
                {opportunity.buy_stock_qty}
              </span>
            )}
          </div>

          {opportunity.buy_url && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => window.open(opportunity.buy_url, '_blank')}
              className="p-1"
            >
              <ExternalLink className="w-3 h-3" />
            </Button>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          {!isActed ? (
            <>
              <Button
                variant="primary"
                size="sm"
                fullWidth
                onClick={handleMarkActed}
                isLoading={isMarking}
                className="flex-1"
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                Mark as Purchased
              </Button>
              {opportunity.buy_url && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(opportunity.buy_url, '_blank')}
                >
                  <ExternalLink className="w-4 h-4" />
                </Button>
              )}
            </>
          ) : (
            <Button variant="ghost" size="sm" fullWidth disabled>
              <CheckCircle className="w-4 h-4 mr-2" />
              Acted Upon
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
};