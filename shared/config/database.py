# Database Configuration for SoleFlip Backend

DATABASE_CONFIG = {
    "pool_size": 25,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}

# PostgreSQL Settings
POSTGRES_MAX_CONNECTIONS = 150

# PgBouncer Settings (if used)
PGBOUNCER_CONFIG = {
    "pool_mode": "transaction",
    "max_client_conn": 100,
    "default_pool_size": 25,
    "reserve_pool": 5,
}
