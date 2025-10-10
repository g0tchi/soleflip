-- Fix Stuck Batch from 2025-08-06
-- Batch ID: 1eb6c582-68e9-4987-a92f-13da7327ef23
-- Issue: Stuck in 'processing' status for over 2 months

-- 1. First, inspect the current status
SELECT
    id,
    status,
    source_type,
    source_file,
    created_at,
    started_at,
    completed_at,
    total_records,
    processed_records,
    error_records,
    error_message
FROM integration.import_batches
WHERE id = '1eb6c582-68e9-4987-a92f-13da7327ef23';

-- 2. Mark as failed (recommended after 2 months stuck)
UPDATE integration.import_batches
SET
    status = 'failed',
    error_message = 'Batch manually marked as failed after being stuck in processing for over 2 months (since 2025-08-06). Likely crashed during import.',
    completed_at = NOW()
WHERE id = '1eb6c582-68e9-4987-a92f-13da7327ef23'
AND status = 'processing';  -- Safety check

-- 3. Verify the fix
SELECT
    id,
    status,
    source_type,
    source_file,
    created_at,
    started_at,
    completed_at,
    total_records,
    processed_records,
    error_records,
    error_message
FROM integration.import_batches
WHERE id = '1eb6c582-68e9-4987-a92f-13da7327ef23';

-- 4. Check for other potentially stuck batches
SELECT
    id,
    status,
    source_type,
    source_file,
    created_at,
    started_at,
    EXTRACT(EPOCH FROM (NOW() - started_at)) / 3600 as hours_processing
FROM integration.import_batches
WHERE status = 'processing'
AND started_at < NOW() - INTERVAL '4 hours'
ORDER BY started_at;
