# Brand & Supplier History Tracking

## Overview

The system now includes comprehensive timeline/history tracking for brands and suppliers to document important milestones, collaborations, closures, and other significant events.

## Tables

### 1. `catalog.brand_history`

Tracks brand-related events including founding, acquisitions, closures, rebranding, and collaborations.

**Schema:**
```sql
CREATE TABLE catalog.brand_history (
    id UUID PRIMARY KEY,
    brand_id UUID NOT NULL REFERENCES catalog.brand(id),
    event_type catalog.brand_event_type NOT NULL,
    event_date DATE,                          -- Full date (if known)
    event_year INTEGER,                       -- Year only (for year-only precision)
    title VARCHAR(200) NOT NULL,
    description TEXT,
    related_brand_id UUID,                    -- For collaborations
    collaboration_start_date DATE,
    collaboration_end_date DATE,
    metadata JSONB,                           -- Flexible additional data
    source VARCHAR(100),                      -- Information source
    created_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(100)
);
```

**Event Types:**
- `founded` - Brand founding/establishment
- `milestone` - General milestone events
- `acquisition` - Brand acquired by another company
- `closure` - Brand closed/discontinued
- `rebranding` - Brand name/identity change
- `collaboration` - Collaboration with another brand
- `expansion` - Market/product line expansion
- `contraction` - Market/product line reduction
- `other` - Other significant events

### 2. `supplier.supplier_history`

Tracks supplier relationship events including partnerships, quality issues, and status changes.

**Schema:**
```sql
CREATE TABLE supplier.supplier_history (
    id UUID PRIMARY KEY,
    supplier_id UUID NOT NULL REFERENCES supplier.profile(id),
    event_type supplier.supplier_event_type NOT NULL,
    event_date DATE,
    event_year INTEGER,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    severity VARCHAR(20),                     -- For issues: low, medium, high, critical
    resolved BOOLEAN DEFAULT FALSE,           -- Issue resolution status
    resolved_date DATE,
    metadata JSONB,
    source VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(100)
);
```

**Event Types:**
- `partnership_started` - Partnership established
- `partnership_ended` - Partnership terminated
- `status_change` - Supplier status changed
- `milestone` - General milestone events
- `quality_issue` - Quality problems detected
- `closure` - Supplier closed business
- `warning` - Warning issued to supplier
- `preferred_status_gained` - Became preferred supplier
- `preferred_status_lost` - Lost preferred status
- `contract_signed` - New contract signed
- `contract_renewed` - Contract renewal
- `contract_terminated` - Contract ended
- `other` - Other significant events

## Usage Examples

### Brand History Examples

#### 1. Record Brand Founding
```sql
INSERT INTO catalog.brand_history (
    brand_id,
    event_type,
    event_year,
    title,
    description,
    source
) VALUES (
    (SELECT id FROM catalog.brand WHERE name = 'Nike'),
    'founded',
    1964,
    'Nike founded in Oregon',
    'Originally founded as Blue Ribbon Sports by Bill Bowerman and Phil Knight',
    'Official Nike history'
);
```

#### 2. Record Brand Collaboration (Collab)
```sql
-- Example: Nike x Off-White collaboration
INSERT INTO catalog.brand_history (
    brand_id,
    event_type,
    event_date,
    collaboration_start_date,
    collaboration_end_date,
    title,
    description,
    related_brand_id,
    metadata
) VALUES (
    (SELECT id FROM catalog.brand WHERE name = 'Nike'),
    'collaboration',
    '2017-09-09',
    '2017-09-09',
    '2022-11-28',  -- Virgil Abloh passed away
    'Nike x Off-White "The Ten" Collection',
    'Virgil Abloh reimagines 10 iconic Nike silhouettes in groundbreaking collaboration',
    (SELECT id FROM catalog.brand WHERE name = 'Off-White'),
    '{"collection": "The Ten", "designer": "Virgil Abloh", "pieces": 10}'::jsonb
);
```

#### 3. Record Brand Acquisition
```sql
INSERT INTO catalog.brand_history (
    brand_id,
    event_type,
    event_date,
    title,
    description,
    metadata
) VALUES (
    (SELECT id FROM catalog.brand WHERE name = 'Converse'),
    'acquisition',
    '2003-07-09',
    'Acquired by Nike',
    'Nike acquires Converse for $305 million',
    '{"acquiring_company": "Nike", "acquisition_price_usd": 305000000}'::jsonb
);
```

#### 4. Record Brand Closure
```sql
INSERT INTO catalog.brand_history (
    brand_id,
    event_type,
    event_date,
    title,
    description
) VALUES (
    (SELECT id FROM catalog.brand WHERE name = 'Reebok'),
    'closure',
    '2021-08-01',
    'Sold by Adidas to Authentic Brands Group',
    'Adidas sells Reebok after 15 years of ownership'
);
```

### Supplier History Examples

#### 1. Record Partnership Start
```sql
INSERT INTO supplier.supplier_history (
    supplier_id,
    event_type,
    event_date,
    title,
    description,
    created_by
) VALUES (
    (SELECT id FROM supplier.profile WHERE name = 'SneakerSource GmbH'),
    'partnership_started',
    '2020-05-15',
    'Partnership established',
    'Initial partnership agreement signed with standard terms',
    'admin_user'
);
```

#### 2. Record Quality Issue
```sql
INSERT INTO supplier.supplier_history (
    supplier_id,
    event_type,
    event_date,
    title,
    description,
    severity,
    resolved,
    metadata
) VALUES (
    (SELECT id FROM supplier.profile WHERE name = 'FastKicks Ltd'),
    'quality_issue',
    '2023-08-20',
    'Quality issues detected with batch #4521',
    'Multiple counterfeit items detected in shipment',
    'high',
    false,
    '{"batch_id": "4521", "affected_items": 15, "action": "shipment_returned"}'::jsonb
);
```

#### 3. Resolve Quality Issue
```sql
-- Update the quality issue to mark it as resolved
UPDATE supplier.supplier_history
SET
    resolved = true,
    resolved_date = CURRENT_DATE,
    description = description || '. RESOLVED: Supplier implemented new authentication procedures.'
WHERE
    supplier_id = (SELECT id FROM supplier.profile WHERE name = 'FastKicks Ltd')
    AND event_type = 'quality_issue'
    AND resolved = false;
```

#### 4. Record Preferred Status Change
```sql
INSERT INTO supplier.supplier_history (
    supplier_id,
    event_type,
    event_date,
    title,
    description
) VALUES (
    (SELECT id FROM supplier.profile WHERE name = 'Premium Sneakers Inc'),
    'preferred_status_gained',
    '2023-10-01',
    'Elevated to preferred supplier',
    'Achieved 98% quality rating and 99.5% on-time delivery over 12 months'
);
```

## Query Examples

### Get Brand Timeline
```sql
-- Get full timeline for a brand
SELECT
    bh.event_type,
    COALESCE(bh.event_date::text, bh.event_year::text) as when,
    bh.title,
    bh.description,
    rb.name as related_brand,
    bh.source
FROM catalog.brand_history bh
LEFT JOIN catalog.brand rb ON bh.related_brand_id = rb.id
WHERE bh.brand_id = (SELECT id FROM catalog.brand WHERE name = 'Nike')
ORDER BY
    COALESCE(bh.event_date, make_date(bh.event_year, 1, 1)) ASC;
```

### Get All Brand Collaborations
```sql
-- Get all collaborations involving a brand
SELECT
    b1.name as brand,
    b2.name as collaborated_with,
    bh.title,
    bh.collaboration_start_date,
    bh.collaboration_end_date,
    bh.description
FROM catalog.brand_history bh
JOIN catalog.brand b1 ON bh.brand_id = b1.id
JOIN catalog.brand b2 ON bh.related_brand_id = b2.id
WHERE bh.event_type = 'collaboration'
ORDER BY bh.collaboration_start_date DESC;
```

### Get Supplier Unresolved Issues
```sql
-- Get all unresolved quality issues and warnings for suppliers
SELECT
    sp.name as supplier,
    sh.event_type,
    sh.event_date,
    sh.title,
    sh.severity,
    sh.description,
    CURRENT_DATE - sh.event_date as days_open
FROM supplier.supplier_history sh
JOIN supplier.profile sp ON sh.supplier_id = sp.id
WHERE sh.event_type IN ('quality_issue', 'warning')
  AND sh.resolved = false
ORDER BY sh.severity DESC, sh.event_date ASC;
```

### Get Supplier Performance Timeline
```sql
-- Get supplier relationship timeline
SELECT
    sh.event_date,
    sh.event_type,
    sh.title,
    sh.severity,
    sh.resolved
FROM supplier.supplier_history sh
WHERE sh.supplier_id = (SELECT id FROM supplier.profile WHERE name = 'SneakerSource GmbH')
ORDER BY sh.event_date DESC;
```

## Performance Indexes

The following indexes are automatically created for optimal query performance:

### Brand History Indexes
- `idx_brand_history_brand_id` - Fast brand timeline queries
- `idx_brand_history_event_type` - Filter by event type
- `idx_brand_history_event_date` - Chronological sorting
- `idx_brand_history_event_year` - Year-based filtering
- `idx_brand_history_collaboration` - Collaboration lookups (partial index)

### Supplier History Indexes
- `idx_supplier_history_supplier_id` - Fast supplier timeline queries
- `idx_supplier_history_event_type` - Filter by event type
- `idx_supplier_history_event_date` - Chronological sorting
- `idx_supplier_history_event_year` - Year-based filtering
- `idx_supplier_history_unresolved_issues` - Fast unresolved issue queries (partial index)

## Data Integrity

### Immutable Events
History events are **immutable** - they should not be deleted or modified after creation. This ensures audit trail integrity.

- To correct an error, add a new corrective event
- Use the `metadata` JSONB field for additional context
- Events cascade delete when parent brand/supplier is deleted

### Date Precision
Events support two date precision levels:
- **Full date** (`event_date`): When exact date is known
- **Year only** (`event_year`): When only the year is known

Use `COALESCE(event_date, make_date(event_year, 1, 1))` for sorting mixed precision.

## Best Practices

1. **Always provide context**: Use `description` field for detailed information
2. **Track sources**: Record where information came from (`source` field)
3. **Use metadata**: Store structured data in the `metadata` JSONB field
4. **Track user**: Set `created_by` to track who added the event
5. **Mark resolutions**: For issues, always update `resolved` and `resolved_date`
6. **Be specific**: Use the most specific `event_type` available
7. **Link collaborations**: Always set `related_brand_id` for collaboration events

## API Integration Examples

### FastAPI Pydantic Models

```python
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from enum import Enum

class BrandEventType(str, Enum):
    FOUNDED = "founded"
    MILESTONE = "milestone"
    ACQUISITION = "acquisition"
    CLOSURE = "closure"
    REBRANDING = "rebranding"
    COLLABORATION = "collaboration"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    OTHER = "other"

class BrandHistoryCreate(BaseModel):
    brand_id: UUID
    event_type: BrandEventType
    event_date: Optional[date] = None
    event_year: Optional[int] = None
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    related_brand_id: Optional[UUID] = None
    collaboration_start_date: Optional[date] = None
    collaboration_end_date: Optional[date] = None
    metadata: Optional[dict] = None
    source: Optional[str] = Field(None, max_length=100)
    created_by: Optional[str] = Field(None, max_length=100)

class BrandHistoryResponse(BrandHistoryCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
```

## Migration Information

- **Migration file**: `2025_10_25_1900_add_brand_supplier_history.py`
- **Applied**: 2025-10-25
- **Rollback support**: Yes (downgrade available)
- **Dependencies**: Requires `catalog.brand` and `supplier.profile` tables

## Future Enhancements

Potential future additions:
- Event attachments (images, documents)
- Event notifications/webhooks
- Timeline visualization API endpoints
- Event approval workflow
- Multi-language support for descriptions
- Event categories/tags system
