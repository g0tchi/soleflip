# Emergency Restore Instructions

If you need to restore the database:

1. **Connect to PostgreSQL:**
   ```
   psql -h 192.168.2.45 -p 2665 -U metabaseuser -d soleflip
   ```

2. **Clean existing data:**
   ```sql
   TRUNCATE sales.transactions CASCADE;
   TRUNCATE products.inventory CASCADE;  
   TRUNCATE products.products CASCADE;
   TRUNCATE core.brands CASCADE;
   TRUNCATE core.categories CASCADE;
   TRUNCATE core.sizes CASCADE;
   TRUNCATE core.suppliers CASCADE;
   TRUNCATE core.platforms CASCADE;
   ```

3. **Restore from backup:**
   ```
   \i C:\Users\mg\soleflip\soleflip_backup_before_improvements_20250806_073936.sql
   ```

Backup created: 2025-08-06 07:39:43.118290
