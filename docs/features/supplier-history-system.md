# Supplier History System

**Version:** 2.2.8
**Date:** October 11, 2025
**Status:** Production Ready ✅

## Overview

The Supplier History System provides comprehensive timeline tracking and historical documentation for all suppliers in the SoleFlipper platform. Similar to the Brand History system, it enables detailed tracking of supplier milestones, expansions, closures, and major events.

## Features

### 1. Database Schema Enhancements

#### New Supplier Fields
Extended `core.suppliers` table with 10 new fields:

| Field | Type | Description |
|-------|------|-------------|
| `founded_year` | INTEGER | Year the supplier was founded |
| `founder_name` | VARCHAR(200) | Name(s) of founder(s) |
| `instagram_handle` | VARCHAR(100) | Instagram username (e.g., @afew_store) |
| `instagram_url` | VARCHAR(300) | Full Instagram profile URL |
| `facebook_url` | VARCHAR(300) | Facebook profile URL |
| `twitter_handle` | VARCHAR(100) | Twitter/X username |
| `logo_url` | VARCHAR(500) | URL to supplier logo image |
| `supplier_story` | TEXT | Detailed history and story |
| `closure_date` | DATE | Date of closure (if applicable) |
| `closure_reason` | TEXT | Reason for closure |

#### New Table: `supplier_history`

```sql
CREATE TABLE core.supplier_history (
    id UUID PRIMARY KEY,
    supplier_id UUID REFERENCES core.suppliers(id),
    event_date DATE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_title VARCHAR(200) NOT NULL,
    event_description TEXT,
    impact_level VARCHAR(20) DEFAULT 'medium',
    source_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Event Types:**
- `founded` - Company/store founding
- `opened_store` - New retail location opened
- `closed_store` - Retail location closed
- `expansion` - Business expansion
- `rebranding` - Brand name/identity change
- `milestone` - Significant achievement
- `controversy` - Notable controversy/issue
- `closure` - Complete business closure

**Impact Levels:**
- `critical` - Major founding/closure events
- `high` - Store openings, major milestones
- `medium` - Expansions, rebrandings
- `low` - Minor events

### 2. Metabase Analytics Views

Six optimized views created in `analytics` schema for Metabase visualization:

#### `supplier_timeline_view`
Complete timeline of all events with color coding and metadata.
- **Best for:** Line charts, event timelines
- **Key fields:** event_date, supplier_name, event_title, impact_color, status_indicator

#### `supplier_summary_stats`
Statistical summary per supplier with event counts and metrics.
- **Best for:** Number cards, KPI dashboards
- **Key metrics:** total_events, store_openings, milestones, operational_years

#### `supplier_event_matrix`
Event breakdown by year, type, and supplier.
- **Best for:** Pivot tables, stacked bar charts
- **Key fields:** event_year, event_type, event_count, supplier_name

#### `supplier_geographic_overview`
Geographic distribution with coordinates for German cities.
- **Best for:** Pin maps
- **Includes:** Latitude/longitude for Berlin, Munich, Hamburg, Düsseldorf, Darmstadt

#### `supplier_status_breakdown`
Status distribution (active vs. closed).
- **Best for:** Donut/pie charts
- **Key metrics:** supplier_count, total_events, avg_age_years

#### `supplier_detailed_table`
Comprehensive table with all supplier details and statistics.
- **Best for:** Tables with conditional formatting
- **Features:** Status indicators, event counts, timeline spans

## Documented Suppliers

### 1. **Overkill** (Berlin)
- **Founded:** September 2003
- **Founders:** Thomas Peiser and Marc Leuschner
- **Status:** Active
- **Timeline:** 3 events (2003-2010)
- **Story:** Founded as a 60 sqm store for graffiti, sneakers and streetwear in Kreuzberg. Started as a magazine around graffiti culture.

**Key Events:**
- 2003: Founded in Berlin Kreuzberg
- 2006: Marc Leuschner joins team
- 2010: First sneaker collaborations launched

### 2. **afew** (Düsseldorf)
- **Founded:** 2008
- **Founders:** Andy and Marco (Brothers)
- **Status:** Active
- **Timeline:** 4 events (2008-2017)
- **Story:** Started selling shoes from their father's garage. Originally called "Schuh-You" before rebranding to AFEW.

**Key Events:**
- 2008: Founded, selling from father's garage
- 2008: Physical store opens at Oststraße 36
- 2010: Rebranding to AFEW STORE
- 2017: Complete store redesign

### 3. **asphaltgold** (Darmstadt)
- **Founded:** 2008
- **Founders:** Daniel Benz
- **Status:** Active
- **Timeline:** 6 events (2008-2025)
- **Story:** Started as one-man operation, now 120+ employees and 80+ brands. Top 15 sneaker retailer in Europe with 1M+ social media followers.

**Key Events:**
- 2008: Founded on Friedensplatz in Darmstadt
- 2009: Online shop launched (Asphaltgold.com)
- 2015: Second store (AGC Store) opens
- 2020: Store consolidation at Ludwigsplatz
- 2020: Recognized as Top 15 European sneaker retailer
- 2025: Frankfurt store opens

### 4. **CTBI Trading / Allike** (Hamburg) ❌ CLOSED
- **Founded:** 2009
- **Founder:** Fiete Bluhm
- **Status:** Closed (October 10, 2025)
- **Timeline:** 5 events (2009-2025)
- **Story:** 16 years of sneaker culture in Hamburg. Expanded with a.plus (fashion) and Willi's (food) during Covid. Closed due to difficult market conditions for smaller businesses.

**Key Events:**
- 2009: Allike Store founded
- 2014: Physical store opens in Hamburg-Altona
- 2020: Expansion with a.plus and Willi's
- 2020: Second store opens downtown Hamburg
- 2025: Store closure announced (136,000 Instagram followers)

**Closure Details:**
- **Date:** October 10, 2025
- **Reason:** Industry changes, difficult market conditions for smaller businesses
- **Instagram:** https://www.instagram.com/p/DPo3_FjiEV-/

### 5. **BSTN** (Munich)
- **Founded:** September 2013 (Beastin brand started 2008)
- **Founders:** Christian "Fu" Boszczyk and Dusan "Duki" Cvetkovic
- **Status:** Active
- **Timeline:** 4 events (2008-2020)
- **Story:** Started with own label "BEASTIN" in 2008. Created BSTN store in 2013 when they couldn't find perfect retail environment for their brand. Now international with stores in Munich, Hamburg, and London.

**Key Events:**
- 2008: Beastin brand founded
- 2013: BSTN store opens in Munich Maxvorstadt
- 2017: Hamburg store opens in Schanzenviertel
- 2020: International expansion to Brixton, London

## Statistics

- **Total Suppliers Documented:** 5
- **Total Timeline Events:** 22
- **Timeline Span:** 2003-2025 (22 years)
- **Active Suppliers:** 4
- **Closed Suppliers:** 1
- **Event Breakdown:**
  - Store Openings: 7
  - Foundings: 6
  - Milestones: 6
  - Closures: 1
  - Expansions: 1
  - Rebrandings: 1

## Metabase Visualization Guide

### Recommended Dashboards

#### 1. Supplier Timeline Dashboard
**Chart Type:** Line Chart with Events
**View:** `analytics.supplier_timeline_view`
**Setup:**
```sql
SELECT event_date, supplier_name, event_title,
       impact_level, impact_color, event_sequence
FROM analytics.supplier_timeline_view
ORDER BY event_date
```
**Configuration:**
- X-axis: event_date
- Y-axis: event_sequence
- Series: supplier_name
- Color: impact_color (#DC2626 for critical, #EA580C for high, #CA8A04 for medium)

**Shows:** Chronological progression of all supplier events with visual impact indicators.

#### 2. Event Impact Analysis
**Chart Type:** Stacked Bar Chart
**View:** `analytics.supplier_event_matrix`
**Setup:**
```sql
SELECT event_year, event_type, SUM(event_count) as total_events
FROM analytics.supplier_event_matrix
GROUP BY event_year, event_type
ORDER BY event_year
```
**Configuration:**
- X-axis: event_year
- Y-axis: total_events
- Series: event_type
- Stacking: enabled

**Shows:** Event frequency and types over time, revealing industry patterns.

#### 3. Supplier KPI Cards
**Chart Type:** Number Cards / Gauges
**View:** `analytics.supplier_summary_stats`
**Metrics:**
- Total Events
- Store Openings
- Operational Years
- Major Events (critical + high impact)

**Example Query:**
```sql
SELECT name, total_events, store_openings,
       operational_years, critical_events + high_impact_events as major_events
FROM analytics.supplier_summary_stats
WHERE status = 'active'
```

#### 4. Geographic Distribution
**Chart Type:** Pin Map
**View:** `analytics.supplier_geographic_overview`
**Setup:**
```sql
SELECT name, city, latitude, longitude,
       total_events, status
FROM analytics.supplier_geographic_overview
WHERE latitude IS NOT NULL
```
**Configuration:**
- Latitude: latitude
- Longitude: longitude
- Pin size: total_events
- Pin color: status (green for active, red for closed)

**Shows:** Where German sneaker suppliers are located with event density.

#### 5. Status Overview
**Chart Type:** Donut Chart
**View:** `analytics.supplier_status_breakdown`
**Setup:**
```sql
SELECT status, supplier_count
FROM analytics.supplier_status_breakdown
```
**Shows:** Active vs. closed supplier distribution.

#### 6. Detailed Supplier Table
**Chart Type:** Table with Conditional Formatting
**View:** `analytics.supplier_detailed_table`
**Conditional Formatting:**
- `status_emoji`: Red background for [X] (closed)
- `major_events`: Bold text if > 3
- `active_years`: Color gradient (green for 20+, yellow for 10-20, red for <10)

#### 7. Event Type Breakdown
**Chart Type:** Row Chart
**View:** `analytics.supplier_event_matrix`
**Setup:**
```sql
SELECT event_type, supplier_name, SUM(event_count) as events
FROM analytics.supplier_event_matrix
GROUP BY event_type, supplier_name
ORDER BY events DESC
```

## Implementation Details

### Database Migration
**File:** `migrations/versions/2025_10_11_0835_3ef19f94d0a5_add_supplier_history_table.py`

**Changes:**
1. Added 10 new columns to `core.suppliers`
2. Created `core.supplier_history` table
3. Created 4 indexes for performance:
   - `idx_supplier_history_supplier_date` (supplier_id, event_date)
   - `idx_supplier_history_event_type` (event_type)
   - `idx_suppliers_instagram` (instagram_handle)
   - `idx_suppliers_founded_year` (founded_year)

### Scripts

#### Data Population Scripts
- `populate_allike_history.py` - Allike/CTBI history and closure
- `populate_afew_asphaltgold_history.py` - afew and asphaltgold histories
- `create_asphaltgold_supplier.py` - Create new asphaltgold supplier entry
- `populate_bstn_overkill_history.py` - BSTN and Overkill histories

#### Utility Scripts
- `update_allike_closure.py` - Document Allike closure
- `show_all_supplier_histories.py` - Display complete overview
- `verify_allike_history.py` - Verify data integrity
- `cleanup_duplicate_history.py` - Remove duplicate entries
- `create_metabase_supplier_views.py` - Create analytics views

### Research Sources

All timeline events are documented with source URLs:
- Official supplier websites
- Instagram announcements
- Sneaker Freaker articles
- Nike SNKRS features
- Industry publications

## API Integration

While no direct API endpoints were created in this phase, the views can be queried directly:

```python
from sqlalchemy import text
from shared.database.connection import db_manager

async def get_supplier_timeline(supplier_slug: str):
    async with db_manager.get_session() as session:
        result = await session.execute(
            text("""
                SELECT * FROM analytics.supplier_timeline_view
                WHERE supplier_slug = :slug
                ORDER BY event_date
            """),
            {"slug": supplier_slug}
        )
        return result.fetchall()
```

## Future Enhancements

### Planned Features
1. **Automated Social Media Monitoring** - Track supplier Instagram/Twitter for announcements
2. **Event Webhooks** - Notify when suppliers post major updates
3. **Competitive Intelligence** - Cross-reference with sales data to identify trends
4. **Supplier Health Score** - Calculate viability score based on event patterns
5. **Industry Trend Analysis** - Aggregate data to identify market patterns
6. **API Endpoints** - RESTful API for supplier history queries

### Additional Suppliers to Document
- Solebox (Berlin/Munich)
- Snipes (multiple locations)
- Footlocker Germany
- 43einhalb (Frankfurt)
- Caliroots (Sweden/International)
- END Clothing (UK)
- Sneakersnstuff (Sweden/International)

## Maintenance

### Adding New Suppliers

1. **Create supplier record:**
```python
await session.execute(
    text("""
        INSERT INTO core.suppliers (
            name, slug, founded_year, founder_name,
            instagram_handle, instagram_url, website,
            city, country, supplier_story
        ) VALUES (
            :name, :slug, :founded_year, :founder_name,
            :instagram_handle, :instagram_url, :website,
            :city, :country, :supplier_story
        )
    """),
    supplier_data
)
```

2. **Add timeline events:**
```python
events = [
    {
        "supplier_id": supplier_id,
        "event_date": date(2020, 1, 1),
        "event_type": "founded",
        "event_title": "Store Founded",
        "event_description": "Full description...",
        "impact_level": "critical",
        "source_url": "https://..."
    }
]

for event in events:
    await session.execute(
        text("""
            INSERT INTO core.supplier_history
            (supplier_id, event_date, event_type, event_title,
             event_description, impact_level, source_url)
            VALUES
            (:supplier_id, :event_date, :event_type, :event_title,
             :event_description, :impact_level, :source_url)
        """),
        event
    )
```

### Updating Existing Suppliers

Use provided scripts:
```bash
# Verify data
python -m scripts.show_all_supplier_histories

# Check specific supplier
python -m scripts.verify_allike_history
```

## Testing

All views tested with real data:
- ✅ Timeline view: 22 events displayed correctly
- ✅ Summary stats: All calculations accurate
- ✅ Geographic view: Coordinates verified for all cities
- ✅ Event matrix: Proper grouping and aggregation
- ✅ Status breakdown: Correct active/closed counts
- ✅ Detailed table: All fields populated correctly

## Performance

- **Query Performance:** Sub-second queries on all views
- **Indexes:** Strategic indexes on date, type, and foreign keys
- **View Optimization:** Pre-aggregated data for fast dashboard loading
- **Data Size:** Currently 5 suppliers, 22 events (~10KB)
- **Scalability:** Designed to handle 100+ suppliers, 1000+ events

## Security & Privacy

- No sensitive supplier financial data stored
- Public information only (websites, social media, press releases)
- Closure reasons documented from public announcements
- Source URLs provided for transparency and verification

## Related Documentation

- [Brand History System](./brand-intelligence.md)
- [StockX Product Enrichment](./stockx-product-enrichment.md)
- [Metabase Analytics Views](../guides/metabase-setup.md)
- [Database Schema Documentation](../architecture/database-schema.md)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.2.8 | 2025-10-11 | Initial supplier history system implementation |

## Contributors

- Research: Claude Code with web search and documentation review
- Implementation: Database migrations, data population scripts, Metabase views
- Documentation: Comprehensive feature documentation and visualization guide

---

**Last Updated:** October 11, 2025
**Status:** ✅ Production Ready
**Metabase Views:** 6 analytics views available in `analytics` schema
