#!/bin/bash
# Test-Skript für Product Enrichment mit Rate Limiting
# Nach StockX API Cooling Period (10-15 Minuten)

echo "=================================="
echo "Product Enrichment Test"
echo "=================================="
echo ""

echo "📊 Checking API Status..."
docker stats --no-stream soleflip-api
echo ""

echo "🧪 Starting Enrichment Test..."
curl -X POST "http://localhost:8000/api/v1/products/enrich" \
  -H "Content-Type: application/json" \
  2>/dev/null | python3 -m json.tool

echo ""
echo "⏳ Waiting 5 seconds for background task to start..."
sleep 5

echo ""
echo "📋 Checking Logs (last 30 seconds)..."
echo "Looking for: Rate limit hits, Retries, Enriched products, Checkpoints"
echo ""
docker logs soleflip-api --since 30s | grep -E "Rate limit hit|Retry|enriched_count|checkpoint|Product enrichment completed" | head -20

echo ""
echo "💾 Memory Status:"
docker stats --no-stream soleflip-api

echo ""
echo "=================================="
echo "Test Complete!"
echo "=================================="
echo ""
echo "✅ If you see 'Rate limit hit... Retry' logs → Rate limiting is working!"
echo "✅ If you see 'enriched_count' → Products are being enriched successfully!"
echo "❌ If still getting 429 errors → Wait another 5-10 minutes"
