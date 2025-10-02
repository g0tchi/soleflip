# Architecture Documentation

This folder contains architectural analysis, design decisions, and system structure documentation.

## 📋 Index

### Database Architecture

- **[database-analysis.md](database-analysis.md)** - Database Structure Analysis
  - Schema organization (core, products, transactions, analytics, finance)
  - Table relationships
  - Data integrity constraints
  - Performance considerations

- **[schema-consolidation-analysis.md](schema-consolidation-analysis.md)** - Schema Consolidation
  - Multi-schema strategy
  - Data separation principles
  - Migration planning
  - Best practices

- **[transactions-schema-analysis.md](transactions-schema-analysis.md)** - Transactions Schema
  - Order tracking architecture
  - Multi-platform support
  - Financial calculations
  - Audit trails

---

### Data Architecture

- **[marketplace-data-architecture.md](marketplace-data-architecture.md)** - Marketplace Data (v2.2.0)
  - Real-time pricing data
  - Multi-platform availability tracking
  - Automated repricing logic
  - Historical price tracking

- **[platform-vs-direct-sales-analysis.md](platform-vs-direct-sales-analysis.md)** - Sales Channel Analysis
  - Platform fees comparison
  - Direct sales optimization
  - Revenue analysis
  - Channel strategy

---

### Business Logic

- **[roi-calculation-b2b-implementation.md](roi-calculation-b2b-implementation.md)** - ROI Calculations
  - B2B profit margin calculations
  - VAT handling
  - Platform fee deductions
  - Net profit formulas

- **[product-review-workflow.md](product-review-workflow.md)** - Product Review System
  - Review workflow states
  - Quality assurance process
  - Approval pipeline
  - Automation opportunities

---

### Performance & Testing

- **[inventory-refresh-test-report.md](inventory-refresh-test-report.md)** - Inventory Refresh Testing
  - Performance benchmarks
  - Concurrency testing
  - Edge case handling
  - Optimization results

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    SOLEFLIP PLATFORM                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         DOMAIN-DRIVEN DESIGN STRUCTURE         │    │
│  ├────────────────────────────────────────────────┤    │
│  │                                                 │    │
│  │  domains/                                       │    │
│  │  ├── integration/   (External APIs)            │    │
│  │  ├── inventory/     (Stock Management)         │    │
│  │  ├── pricing/       (Smart Pricing)            │    │
│  │  ├── products/      (Catalog)                  │    │
│  │  ├── analytics/     (Forecasting)              │    │
│  │  ├── orders/        (Order Management)         │    │
│  │  ├── dashboard/     (Aggregation)              │    │
│  │  ├── auth/          (Authentication)           │    │
│  │  └── suppliers/     (Supplier Management)      │    │
│  │                                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │          DATABASE SCHEMA ORGANIZATION          │    │
│  ├────────────────────────────────────────────────┤    │
│  │                                                 │    │
│  │  PostgreSQL Schemas:                           │    │
│  │  ├── core          (Users, Platforms, Brands)  │    │
│  │  ├── products      (Catalog, Inventory)        │    │
│  │  ├── transactions  (Orders, Payments)          │    │
│  │  ├── analytics     (Views, Aggregations)       │    │
│  │  └── finance       (Expenses, Accounting)      │    │
│  │                                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## 🎯 Architecture Principles

### 1. Domain-Driven Design (DDD)
- Clear bounded contexts
- Rich domain models
- Separation of concerns
- Business logic in domain layer

### 2. Multi-Schema Database
- **core**: Shared entities (users, platforms, brands, suppliers)
- **products**: Product catalog and inventory
- **transactions**: Orders, sales, payments
- **analytics**: Materialized views, aggregations
- **finance**: Expenses, accounting

### 3. Repository Pattern
- Data access abstraction
- Testable business logic
- Clean architecture
- Dependency injection

### 4. Event-Driven Updates
- Real-time synchronization
- Loose coupling
- Scalable architecture
- Audit trails

## 📊 Data Flow

```
1. ORDER CREATION FLOW
   User creates order
   ├──> transactions.orders (INSERT)
   ├──> Event: order_created
   ├──> Update inventory status
   ├──> Trigger analytics refresh
   └──> Send notifications

2. INVENTORY UPDATE FLOW
   Inventory item added/updated
   ├──> products.inventory (INSERT/UPDATE)
   ├──> Event: inventory_changed
   ├──> Update marketplace_data
   ├──> Trigger repricing
   └──> Refresh analytics views

3. ANALYTICS REFRESH FLOW
   Scheduled/Event-driven
   ├──> REFRESH MATERIALIZED VIEW
   ├──> Update aggregations
   ├──> Metabase auto-updates
   └──> Dashboards show new data
```

## 🔐 Security Architecture

- **Authentication**: JWT tokens with refresh mechanism
- **Authorization**: Role-based access control (RBAC)
- **Data Encryption**: Fernet encryption for sensitive fields
- **API Security**: Rate limiting, CORS, request validation

## 📈 Performance Strategy

- **Database Indexes**: Strategic indexing on frequently queried fields
- **Materialized Views**: Pre-aggregated data for fast dashboard queries
- **Connection Pooling**: Optimized async SQLAlchemy engine
- **Caching**: Redis-based multi-tier caching
- **Streaming**: Large dataset streaming responses

## 📚 Related Documentation

- **Migrations:** `../migrations/` - Schema evolution
- **Integrations:** `../integrations/` - External platform integrations
- **Refactoring:** `../refactoring/` - Code quality improvements

---

**Last Updated:** 2025-10-01
