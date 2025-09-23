import { useState, useEffect } from 'react';
import { Zap, Target, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card, Heading, Text, Button } from '../ui';

interface QuickFlipSummary {
  total_opportunities: number;
  avg_profit_margin: number;
  avg_gross_profit: number;
  best_opportunity?: {
    product_name: string;
    profit_margin: number;
    gross_profit: number;
  };
}

export const QuickFlipWidget = () => {
  const [summary, setSummary] = useState<QuickFlipSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchSummary = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/quickflip/opportunities/summary');
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Failed to fetch QuickFlip summary:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Zap className="w-6 h-6 text-yellow-400" />
          <Heading size="md">QuickFlip Opportunities</Heading>
        </div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-700 rounded animate-pulse"></div>
          <div className="h-4 bg-gray-700 rounded animate-pulse w-3/4"></div>
          <div className="h-8 bg-gray-700 rounded animate-pulse w-1/2"></div>
        </div>
      </Card>
    );
  }

  if (!summary || summary.total_opportunities === 0) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Zap className="w-6 h-6 text-gray-500" />
          <Heading variant="title" className="text-gray-400">QuickFlip Opportunities</Heading>
        </div>
        <div className="text-center py-4">
          <Target className="w-8 h-8 text-gray-600 mx-auto mb-2" />
          <Text variant="body">No opportunities found</Text>
          <Text variant="caption">Import market data to discover arbitrage opportunities</Text>
        </div>
        <Link to="/quickflip">
          <Button variant="outline" size="sm" fullWidth className="mt-4">
            <Zap className="w-4 h-4 mr-2" />
            Go to QuickFlip
          </Button>
        </Link>
      </Card>
    );
  }

  return (
    <Card className="p-6 hover:scale-[1.02] transition-transform duration-200">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-yellow-500/20 rounded-lg">
            <Zap className="w-6 h-6 text-yellow-400" />
          </div>
          <div>
            <Heading variant="title">QuickFlip Opportunities</Heading>
            <Text variant="caption">Arbitrage opportunities</Text>
          </div>
        </div>
        <Link to="/quickflip">
          <Button variant="ghost" size="sm">
            <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>

      <div className="space-y-4">
        {/* Key Metrics */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <Text variant="caption">Opportunities</Text>
            <Heading variant="title" className="text-yellow-400">
              {summary.total_opportunities}
            </Heading>
          </div>

          <div className="text-center">
            <Text variant="caption">Avg Margin</Text>
            <Heading variant="title" className="text-green-400">
              {summary.avg_profit_margin.toFixed(1)}%
            </Heading>
          </div>

          <div className="text-center">
            <Text variant="caption">Avg Profit</Text>
            <Heading variant="title" className="text-green-400">
              €{summary.avg_gross_profit.toFixed(0)}
            </Heading>
          </div>
        </div>

        {/* Best Opportunity */}
        {summary.best_opportunity && (
          <div className="p-3 bg-gray-800/50 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <Text variant="body" className="font-medium truncate">
                  {summary.best_opportunity.product_name}
                </Text>
                <Text variant="caption">Best opportunity</Text>
              </div>
              <div className="text-right">
                <Text variant="body" className="text-green-400 font-medium">
                  +{summary.best_opportunity.profit_margin.toFixed(1)}%
                </Text>
                <Text variant="caption">
                  €{summary.best_opportunity.gross_profit.toFixed(0)} profit
                </Text>
              </div>
            </div>
          </div>
        )}

        {/* Action Button */}
        <Link to="/quickflip">
          <Button variant="primary" size="sm" fullWidth className="group">
            <Zap className="w-4 h-4 mr-2 group-hover:animate-pulse" />
            View All Opportunities
          </Button>
        </Link>
      </div>
    </Card>
  );
};