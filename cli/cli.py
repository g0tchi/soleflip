#!/usr/bin/env python3
"""
Retro Keygen Admin CLI
A nostalgic CLI tool for database and API management
"""

import random
import sys
import time

from db import DatabaseManager
from shopify import ShopifyManager
from utils import (
    clear_screen,
    colored_text,
    format_status_line,
    keygen_animation,
    progress_bar,
    section_header,
    show_banner,
    status_icon,
    wait_for_key,
)

from config import get_config

try:
    from stockx_real import RealStockXManager as StockXManager

    print(colored_text("Using real StockX integration", "green"))
except ImportError:
    from stockx import StockXManager

    print(colored_text("Using demo StockX integration", "yellow"))
from awin import AwinManager
from security import SecurityManager, display_security_status


class RetroAdminCLI:
    def __init__(self):
        self.config = get_config()
        self.security = SecurityManager(self.config)
        self.db = DatabaseManager(self.config)
        self.shopify = ShopifyManager(self.config)
        self.stockx = StockXManager(self.config)
        self.awin = AwinManager(self.config)
        self.username = ""
        self.session_id = None

    def startup_sequence(self):
        """Retro keygen style startup"""
        show_banner()
        time.sleep(1)

        print(colored_text("=" * 60, "violet"))
        print(colored_text("  INITIALIZING ADMIN INTERFACE...", "info"))
        print(colored_text("=" * 60, "violet"))

        # Fake loading sequence
        progress_bar("Loading modules", 100, 0.02)
        progress_bar("Connecting to databases", 100, 0.01)
        progress_bar("Authenticating APIs", 100, 0.015)

        print(colored_text("\n[OK] SYSTEM READY", "success"))

        # Show loaded modules in Claude Code style
        print(section_header("SYSTEM MODULES LOADED", "info"))
        modules = [
            ("Database Engine", "PostgreSQL + SQLAlchemy"),
            ("Security System", "Session Management + Logging"),
            ("API Integrations", "Shopify + StockX + Awin"),
            ("Modern Interface", "Claude Code Inspired Design"),
        ]
        for module, desc in modules:
            print(format_status_line(module, "ok", desc))

        print(colored_text("\n  Ready to manage! <3", "purple"))

    def get_user_credentials(self):
        """Interactive user input with retro styling"""
        print(section_header("ADMIN AUTHENTICATION REQUIRED", "warning"))
        print(colored_text("=" * 40, "violet"))

        while not self.username:
            user_input = input(colored_text("\nEnter your codename: ", "info")).strip()
            if user_input:
                self.username = user_input
                break
            print(colored_text("Invalid input! Try again.", "error"))

        # Start security session
        self.session_id = self.security.start_session(self.username)

        # Fake key generation
        keygen_animation(f"Generating access key for {self.username}")

        fake_key = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=16))
        formatted_key = "-".join([fake_key[i : i + 4] for i in range(0, 16, 4)])

        print(format_status_line("ACCESS GRANTED", "success", f"Welcome {self.username}"))
        print(colored_text(f"  Session Key: {formatted_key}", "accent"))
        print(colored_text(f"  Session ID: {self.session_id}", "muted"))

    def show_main_menu(self):
        """Display main menu with Claude Code styling"""
        print(section_header("SOLEFLIPPER ADMIN PANEL", "purple"))
        print(colored_text("=" * 50, "violet"))

        # Get system status for icons
        db_status = "ok" if self.db.check_connection() else "error"
        shopify_status = "ok" if self.shopify and self.shopify.check_connection() else "missing"
        stockx_status = "ok" if self.stockx.check_connection() else "error"

        menu_options = [
            ("1", "Database Operations", db_status, "Manage database, run queries, export data"),
            ("2", "Shopify Management", shopify_status, "Product sync, inventory management"),
            ("3", "StockX Integration", stockx_status, "Portfolio tracking, API operations"),
            ("4", "Data Import", "info", "Awin CSV processing and validation"),
            ("5", "System Status", "info", "Health checks and configuration"),
            ("6", "Logs & Analytics", "info", "Access logs, audit trails, metrics"),
            ("Q", "Exit", "muted", "Close the application"),
        ]

        print(colored_text("\nAvailable Operations:", "info"))

        for key, desc, status, details in menu_options:
            icon = status_icon(status)
            key_text = colored_text(f"[{key}]", "accent")
            desc_text = colored_text(desc, "purple")
            detail_text = colored_text(f" - {details}", "muted")
            print(f"  {key_text} {icon} {desc_text}{detail_text}")

    def handle_database_menu(self):
        """Database operations submenu"""
        print(colored_text("\n[DB] DATABASE OPERATIONS", "green"))
        print(colored_text("-" * 30, "green"))

        db_options = [
            ("1", "View Tables", self.db.list_tables),
            ("2", "Run Query", self.db.interactive_query),
            ("3", "Export Data", self.db.export_data),
            ("4", "Import Data", self.db.import_data),
            ("B", "Back to Main Menu", None),
        ]

        for key, desc, _ in db_options:
            print(colored_text(f"  [{key}] {desc}", "white"))

        choice = input(colored_text("\nSelect option: ", "green")).upper()

        if choice == "B":
            return
        elif choice in ["1", "2", "3", "4"]:
            option = next((opt for opt in db_options if opt[0] == choice), None)
            if option and option[2]:
                self.security.update_session_activity("database_operation", {"action": option[1]})
                option[2]()
        else:
            print(colored_text("Invalid option!", "red"))

    def handle_shopify_menu(self):
        """Shopify management submenu"""
        print(colored_text("\n[SHOP] SHOPIFY MANAGEMENT", "blue"))
        print(colored_text("-" * 30, "blue"))

        shopify_options = [
            ("1", "List Products", self.shopify.list_products),
            ("2", "Update Product", self.shopify.update_product),
            ("3", "Sync Inventory", self.shopify.sync_inventory),
            ("4", "Export Catalog", self.shopify.export_catalog),
            ("B", "Back to Main Menu", None),
        ]

        for key, desc, _ in shopify_options:
            print(colored_text(f"  [{key}] {desc}", "white"))

        choice = input(colored_text("\nSelect option: ", "blue")).upper()

        if choice == "B":
            return
        elif choice in ["1", "2", "3", "4"]:
            option = next((opt for opt in shopify_options if opt[0] == choice), None)
            if option and option[2]:
                self.security.update_session_activity("shopify_operation", {"action": option[1]})
                option[2]()
        else:
            print(colored_text("Invalid option!", "red"))

    def handle_awin_menu(self):
        """Awin data import submenu"""
        print(colored_text("\n[AWIN] DATA IMPORT", "magenta"))
        print(colored_text("-" * 30, "magenta"))

        awin_options = [
            ("1", "Import CSV", self.awin.import_csv),
            ("2", "Sync API Data", self.awin.sync_api),
            ("3", "View Import History", self.awin.import_history),
            ("4", "Data Validation", self.awin.validate_data),
            ("B", "Back to Main Menu", None),
        ]

        for key, desc, _ in awin_options:
            print(colored_text(f"  [{key}] {desc}", "white"))

        choice = input(colored_text("\nSelect option: ", "magenta")).upper()

        if choice == "B":
            return
        elif choice in ["1", "2", "3", "4"]:
            option = next((opt for opt in awin_options if opt[0] == choice), None)
            if option and option[2]:
                self.security.update_session_activity("awin_operation", {"action": option[1]})
                option[2]()
        else:
            print(colored_text("Invalid option!", "red"))

    def handle_stockx_menu(self):
        """StockX portfolio management submenu"""
        print(colored_text("\n[STOCKX] PORTFOLIO MANAGEMENT", "purple"))
        print(colored_text("-" * 35, "purple"))

        stockx_options = [
            ("1", "View Portfolio (Database)", self.stockx.list_portfolio_items),
            ("2", "Search Products (API)", self.stockx.search_products),
            ("3", "Sync Portfolio (API)", self.stockx.sync_portfolio),
            ("4", "Export Sales Data", self.stockx.export_sales_data),
            ("5", "API Status & Control", self.stockx.show_api_status),
            ("6", "Enrich Product Data", self.product_enrichment_menu),
            ("B", "Back to Main Menu", None),
        ]

        for key, desc, _ in stockx_options:
            print(colored_text(f"  [{key}] {desc}", "white"))

        choice = input(colored_text("\nSelect option: ", "purple")).upper()

        if choice == "B":
            return
        elif choice in ["1", "2", "3", "4", "5", "6"]:
            option = next((opt for opt in stockx_options if opt[0] == choice), None)
            if option and option[2]:
                self.security.update_session_activity("stockx_operation", {"action": option[1]})
                option[2]()
        else:
            print(colored_text("Invalid option!", "red"))

    def show_system_status(self):
        """Display comprehensive system status with security"""
        clear_screen()
        print(colored_text("[SYS] SYSTEM & SECURITY STATUS", "yellow"))
        print(colored_text("=" * 40, "yellow"))

        self.security.update_session_activity("system_status_check")

        # Security Status
        display_security_status(self.security)

        print(section_header("SERVICE STATUS", "info"))

        # Check service connections with new styling
        db_status = self.db.check_connection()
        shopify_status = self.shopify.check_connection()
        stockx_status = self.stockx.check_connection()
        awin_status = self.awin.check_status()

        print(
            format_status_line(
                "Database",
                "ok" if db_status else "error",
                "PostgreSQL connection active" if db_status else "Connection failed",
            )
        )
        print(
            format_status_line(
                "Shopify API",
                "ok" if shopify_status else "missing",
                "REST API connected" if shopify_status else "Check credentials",
            )
        )
        print(
            format_status_line(
                "StockX Integration",
                "ok" if stockx_status else "error",
                "Service available" if stockx_status else "Service unavailable",
            )
        )
        print(
            format_status_line(
                "Awin Import",
                "ok" if awin_status else "missing",
                "CSV processing ready" if awin_status else "Not configured",
            )
        )

        # Environment info
        print(colored_text("\n[ENV] ENVIRONMENT INFO", "cyan"))
        print(colored_text(f"Mode: {self.config.system.environment.upper()}", "white"))
        print(colored_text(f"Test Mode: {'YES' if self.config.system.is_test else 'NO'}", "white"))
        print(colored_text(f"Debug: {'YES' if self.config.system.debug else 'NO'}", "white"))

        # Show retro-style feature list
        print(colored_text("\n[FEATURES] SYSTEM CAPABILITIES:", "bright_cyan"))
        features = [
            ("Retro Interface", "ASCII Art + Keygen Animations"),
            ("Database Engine", "PostgreSQL + SQLAlchemy"),
            ("Security System", "Session Management + Logging"),
            ("API Integrations", "Shopify + StockX + Awin"),
            ("Data Management", "CSV Import/Export + Validation"),
        ]
        for feature, desc in features:
            print(colored_text(f"  - {feature}: {desc}", "cyan"))

        print(colored_text("\n  Ready to hack! <3", "bright_magenta"))

        wait_for_key()

    def show_logs(self):
        """Display comprehensive logs menu"""
        clear_screen()
        print(colored_text("[LOG] LOGS & ANALYTICS", "cyan"))
        print(colored_text("=" * 30, "cyan"))

        self.security.update_session_activity("logs_access")

        log_options = [
            ("1", "Access Logs", self.show_access_logs),
            ("2", "Error Logs", self.show_error_logs),
            ("3", "Audit Trail", self.show_audit_logs),
            ("4", "Session History", self.show_session_history),
            ("B", "Back to Main Menu", None),
        ]

        for key, desc, _ in log_options:
            print(colored_text(f"  [{key}] {desc}", "white"))

        choice = input(colored_text("\nSelect log type: ", "cyan")).upper()

        if choice == "B":
            return
        elif choice in ["1", "2", "3", "4"]:
            option = next((opt for opt in log_options if opt[0] == choice), None)
            if option and option[2]:
                option[2]()
        else:
            print(colored_text("Invalid option!", "red"))

    def show_access_logs(self):
        """Show access logs"""
        clear_screen()
        print(colored_text("[ACCESS] ACCESS LOGS", "bright_cyan"))
        print(colored_text("-" * 20, "cyan"))

        logs = self.security.get_recent_logs("access", 15)
        if not logs:
            print(colored_text("No access logs found", "yellow"))
        else:
            for log in logs:
                print(colored_text(log, "white"))

        wait_for_key()

    def show_error_logs(self):
        """Show error logs"""
        clear_screen()
        print(colored_text("[ERROR] ERROR LOGS", "bright_red"))
        print(colored_text("-" * 20, "red"))

        logs = self.security.get_recent_logs("error", 15)
        if not logs:
            print(colored_text("No error logs found", "green"))
        else:
            for log in logs:
                print(colored_text(log, "red"))

        wait_for_key()

    def show_audit_logs(self):
        """Show audit trail"""
        clear_screen()
        print(colored_text("[AUDIT] AUDIT TRAIL", "bright_yellow"))
        print(colored_text("-" * 20, "yellow"))

        logs = self.security.get_recent_logs("audit", 15)
        if not logs:
            print(colored_text("No audit logs found", "yellow"))
        else:
            for log in logs:
                print(colored_text(log, "yellow"))

        wait_for_key()

    def show_session_history(self):
        """Show session statistics"""
        clear_screen()
        print(colored_text("[SESSION] SESSION HISTORY", "bright_magenta"))
        print(colored_text("-" * 25, "magenta"))

        stats = self.security.get_session_stats()

        for key, value in stats.items():
            print(colored_text(f"{key.replace('_', ' ').title()}: {value}", "white"))

        wait_for_key()

    def run(self):
        """Main application loop"""
        try:
            self.startup_sequence()
            self.get_user_credentials()

            while True:
                self.show_main_menu()
                choice = input(colored_text(f"\n{self.username}@retro-admin> ", "cyan")).upper()

                if choice == "Q":
                    print(colored_text("\n[OK] Logging out...", "yellow"))
                    keygen_animation("Securing session")
                    self.security.end_session()
                    print(colored_text("Goodbye, {}!".format(self.username), "green"))
                    break
                elif choice == "1":
                    self.security.update_session_activity("menu_access", {"menu": "database"})
                    self.handle_database_menu()
                elif choice == "2":
                    self.security.update_session_activity("menu_access", {"menu": "shopify"})
                    self.handle_shopify_menu()
                elif choice == "3":
                    self.security.update_session_activity("menu_access", {"menu": "stockx"})
                    self.handle_stockx_menu()
                elif choice == "4":
                    self.security.update_session_activity("menu_access", {"menu": "awin"})
                    self.handle_awin_menu()
                elif choice == "5":
                    self.security.update_session_activity("menu_access", {"menu": "system_status"})
                    self.show_system_status()
                elif choice == "6":
                    self.security.update_session_activity("menu_access", {"menu": "logs"})
                    self.show_logs()
                else:
                    print(colored_text("Invalid command! Try again.", "red"))

        except KeyboardInterrupt:
            print(colored_text("\n\n[!] Emergency logout detected!", "red"))
            self.security.end_session()
            print(colored_text("Session terminated.", "yellow"))
            sys.exit(0)
        except Exception as e:
            print(colored_text(f"\n[FATAL] Critical error: {e}", "red"))
            self.security.log_error("Critical system error", e)
            self.security.end_session()
            sys.exit(1)

    def product_enrichment_menu(self):
        """Product data enrichment submenu"""
        clear_screen()
        print(status_icon("processing") + colored_text(" PRODUCT DATA ENRICHMENT", "purple"))
        print(colored_text("=" * 60, "purple"))

        while True:
            print(colored_text("\n[1] Analyze Current Products", "white"))
            print(colored_text("[2] Search & Match StockX Products", "white"))
            print(colored_text("[3] Enrich Selected Products", "white"))
            print(colored_text("[4] Bulk Enrichment (All Products)", "white"))
            print(colored_text("[5] View Enrichment Stats", "white"))
            print(colored_text("[B] Back to StockX Menu", "cyan"))

            choice = input(colored_text("\nSelect option: ", "purple")).upper()

            if choice == "B":
                break
            elif choice == "1":
                self.analyze_products_for_enrichment()
            elif choice == "2":
                self.search_and_match_stockx()
            elif choice == "3":
                self.enrich_selected_products()
            elif choice == "4":
                self.bulk_product_enrichment()
            elif choice == "5":
                self.show_enrichment_stats()
            else:
                print(colored_text("Invalid option!", "red"))
                time.sleep(1)

    def analyze_products_for_enrichment(self):
        """Analyze current products and identify enrichment opportunities"""
        clear_screen()
        print(
            status_icon("processing") + colored_text(" ANALYZING PRODUCTS FOR ENRICHMENT", "purple")
        )
        print(colored_text("=" * 60, "purple"))

        try:
            import asyncio

            from sqlalchemy import text

            from shared.database.connection import db_manager

            async def analyze():
                await db_manager.initialize()

                async with db_manager.get_session() as session:
                    # Get products missing key data
                    result = await session.execute(
                        text(
                            """
                        SELECT 
                            COUNT(*) as total_products,
                            COUNT(CASE WHEN description IS NULL OR description = '' THEN 1 END) as missing_description,
                            COUNT(CASE WHEN retail_price IS NULL THEN 1 END) as missing_retail_price,
                            COUNT(CASE WHEN release_date IS NULL THEN 1 END) as missing_release_date,
                            COUNT(CASE WHEN avg_resale_price IS NULL THEN 1 END) as missing_resale_price
                        FROM products.products
                    """
                        )
                    )

                    stats = result.fetchone()

                    print(colored_text("\nProduct Analysis Results:", "purple"))
                    print(colored_text("-" * 30, "violet"))
                    print(colored_text(f"Total Products: {stats[0]}", "white"))
                    print(colored_text(f"Missing Description: {stats[1]}", "yellow"))
                    print(colored_text(f"Missing Retail Price: {stats[2]}", "yellow"))
                    print(colored_text(f"Missing Release Date: {stats[3]}", "yellow"))
                    print(colored_text(f"Missing Resale Price: {stats[4]}", "yellow"))

                    # Show sample products that need enrichment
                    result = await session.execute(
                        text(
                            """
                        SELECT products.name, products.sku, brand.name as brand_name,
                               products.description, products.retail_price, products.release_date
                        FROM products.products 
                        LEFT JOIN core.brands brand ON products.brand_id = brand.id
                        WHERE products.description IS NULL OR products.retail_price IS NULL 
                           OR products.release_date IS NULL
                        LIMIT 10
                    """
                        )
                    )

                    products = result.fetchall()

                    if products:
                        print(colored_text("\nSample Products Needing Enrichment:", "purple"))
                        print(colored_text("-" * 40, "violet"))
                        for i, product in enumerate(products, 1):
                            name, sku, brand_name, desc, retail, release = product
                            brand = brand_name if brand_name else "Unknown"

                            missing = []
                            if not desc:
                                missing.append("desc")
                            if not retail:
                                missing.append("price")
                            if not release:
                                missing.append("release")

                            print(colored_text(f"{i}. {brand} - {name} ({sku})", "white"))
                            print(colored_text(f"    Missing: {', '.join(missing)}", "yellow"))
                    else:
                        # If no products found, show some sample products anyway
                        result = await session.execute(
                            text(
                                """
                            SELECT products.name, products.sku, brand.name as brand_name,
                                   products.description, products.retail_price, products.release_date
                            FROM products.products 
                            LEFT JOIN core.brands brand ON products.brand_id = brand.id
                            LIMIT 10
                        """
                            )
                        )

                        sample_products = result.fetchall()
                        print(colored_text("\nSample Products in Database:", "purple"))
                        print(colored_text("-" * 40, "violet"))
                        for i, product in enumerate(sample_products, 1):
                            name, sku, brand_name, desc, retail, release = product
                            brand = brand_name if brand_name else "Unknown"
                            print(colored_text(f"{i}. {brand} - {name[:50]} ({sku})", "white"))

                            status = []
                            if desc:
                                status.append("✓ desc")
                            else:
                                status.append("✗ desc")
                            if retail:
                                status.append("✓ price")
                            else:
                                status.append("✗ price")
                            if release:
                                status.append("✓ release")
                            else:
                                status.append("✗ release")

                            print(colored_text(f"    Data: {' | '.join(status)}", "muted"))

                await db_manager.close()

            asyncio.run(analyze())

        except Exception as e:
            print(colored_text(f"Error analyzing products: {str(e)}", "red"))

        wait_for_key()

    def search_and_match_stockx(self):
        """Search StockX for matching products"""
        clear_screen()
        print(
            status_icon("processing")
            + colored_text(" SEARCH & MATCH STOCKX PRODUCTS", "bright_green")
        )
        print(colored_text("=" * 60, "green"))

        search_term = input(colored_text("\nEnter product search term: ", "cyan"))
        if not search_term:
            print(colored_text("Search cancelled", "yellow"))
            time.sleep(1)
            return

        try:
            import asyncio

            from domains.integration.services.stockx_service import StockXService
            from shared.database.connection import db_manager

            async def search():
                await db_manager.initialize()

                async with db_manager.get_session() as session:
                    stockx_service = StockXService(session)

                    print(colored_text(f"\nSearching StockX for: {search_term}", "white"))

                    results = await stockx_service.search_stockx_catalog(search_term, page_size=20)

                    if results and "results" in results:
                        products = results["results"]
                        print(colored_text(f"\nFound {len(products)} products:", "bright_cyan"))
                        print(colored_text("-" * 40, "cyan"))

                        for i, product in enumerate(products[:10], 1):
                            title = product.get("title", "No Title")
                            brand = product.get("brand", "Unknown Brand")
                            retail_price = product.get("retailPrice", "N/A")
                            release_date = product.get("releaseDate", "N/A")

                            print(colored_text(f"{i}. {brand} - {title}", "white"))
                            print(
                                colored_text(
                                    f"    Retail: ${retail_price} | Release: {release_date}", "dim"
                                )
                            )
                    else:
                        print(colored_text("No products found", "yellow"))

                await db_manager.close()

            asyncio.run(search())

        except Exception as e:
            print(colored_text(f"Error searching StockX: {str(e)}", "red"))

        wait_for_key()

    def enrich_selected_products(self):
        """Enrich selected products with StockX data"""
        clear_screen()
        print(status_icon("processing") + colored_text(" ENRICH SELECTED PRODUCTS", "bright_green"))
        print(colored_text("=" * 60, "green"))

        try:
            import asyncio

            from sqlalchemy import text, update

            from domains.integration.services.stockx_service import StockXService
            from shared.database.connection import db_manager
            from shared.database.models import Product

            async def enrich_products():
                await db_manager.initialize()

                async with db_manager.get_session() as session:
                    # Get products that need enrichment
                    result = await session.execute(
                        text(
                            """
                        SELECT id, name, sku, description, retail_price, release_date
                        FROM products.products 
                        WHERE description IS NULL OR retail_price IS NULL OR release_date IS NULL
                        LIMIT 20
                    """
                        )
                    )

                    products = result.fetchall()

                    if not products:
                        print(colored_text("\nNo products need enrichment!", "green"))
                        return

                    print(
                        colored_text(
                            f"\nFound {len(products)} products needing enrichment:", "bright_cyan"
                        )
                    )
                    print(colored_text("-" * 50, "cyan"))

                    for i, product in enumerate(products, 1):
                        print(colored_text(f"{i}. {product[1]} ({product[2]})", "white"))

                    choice = input(
                        colored_text(
                            f"\nSelect product to enrich (1-{len(products)}) or 'all': ", "cyan"
                        )
                    )

                    if choice.lower() == "all":
                        selected_products = products
                    else:
                        try:
                            idx = int(choice) - 1
                            if 0 <= idx < len(products):
                                selected_products = [products[idx]]
                            else:
                                print(colored_text("Invalid selection!", "red"))
                                return
                        except ValueError:
                            print(colored_text("Invalid input!", "red"))
                            return

                    stockx_service = StockXService(session)
                    enriched_count = 0

                    for product in selected_products:
                        product_id, name, sku, description, retail_price, release_date = product

                        print(colored_text(f"\nEnriching: {name}", "yellow"))

                        # Search StockX for this product
                        search_results = await stockx_service.search_stockx_catalog(
                            name, page_size=5
                        )

                        if (
                            search_results
                            and "results" in search_results
                            and search_results["results"]
                        ):
                            stockx_product = search_results["results"][0]  # Take best match

                            # Extract enrichment data
                            new_description = stockx_product.get(
                                "description"
                            ) or stockx_product.get("title")
                            new_retail_price = stockx_product.get("retailPrice")
                            new_release_date = stockx_product.get("releaseDate")
                            stockx_product_id = stockx_product.get("id")

                            # Update product in database
                            update_data = {}
                            if not description and new_description:
                                update_data["description"] = new_description
                            if not retail_price and new_retail_price:
                                update_data["retail_price"] = float(new_retail_price)
                            if not release_date and new_release_date:
                                try:
                                    from datetime import datetime

                                    update_data["release_date"] = datetime.fromisoformat(
                                        new_release_date.replace("Z", "+00:00")
                                    )
                                except:
                                    pass

                            if update_data:
                                await session.execute(
                                    update(Product)
                                    .where(Product.id == product_id)
                                    .values(**update_data)
                                )

                                # Update inventory items with StockX ID
                                if stockx_product_id:
                                    await session.execute(
                                        text(
                                            """
                                        UPDATE products.inventory 
                                        SET external_ids = COALESCE(external_ids, '{}') || :stockx_data
                                        WHERE product_id = :product_id
                                    """
                                        ),
                                        {
                                            "stockx_data": f'{{"stockx_product_id": "{stockx_product_id}"}}',
                                            "product_id": str(product_id),
                                        },
                                    )

                                enriched_count += 1
                                print(
                                    colored_text(
                                        f"  ✓ Updated: {', '.join(update_data.keys())}", "green"
                                    )
                                )
                            else:
                                print(colored_text("  - No new data found", "dim"))
                        else:
                            print(colored_text("  ✗ No StockX match found", "red"))

                    await session.commit()
                    print(
                        colored_text(
                            f"\nEnrichment complete! Updated {enriched_count} products.",
                            "bright_green",
                        )
                    )

                await db_manager.close()

            asyncio.run(enrich_products())

        except Exception as e:
            print(colored_text(f"Error during enrichment: {str(e)}", "red"))

        wait_for_key()

    def bulk_product_enrichment(self):
        """Bulk enrich all products with available StockX data"""
        clear_screen()
        print(status_icon("warning") + colored_text(" BULK PRODUCT ENRICHMENT", "bright_green"))
        print(colored_text("=" * 60, "green"))

        print(colored_text("\nWARNING: This will attempt to enrich ALL products", "yellow"))
        print(colored_text("This may take a significant amount of time and API calls", "yellow"))

        confirm = input(colored_text("\nProceed? (yes/no): ", "cyan")).lower()
        if confirm != "yes":
            print(colored_text("Bulk enrichment cancelled", "yellow"))
            time.sleep(1)
            return

        try:
            import asyncio

            from sqlalchemy import text, update

            from domains.integration.services.stockx_service import StockXService
            from shared.database.connection import db_manager
            from shared.database.models import Product

            async def bulk_enrich():
                await db_manager.initialize()

                async with db_manager.get_session() as session:
                    # Get all products that need enrichment
                    result = await session.execute(
                        text(
                            """
                        SELECT id, name, sku, description, retail_price, release_date
                        FROM products.products 
                        WHERE description IS NULL OR retail_price IS NULL OR release_date IS NULL
                        ORDER BY created_at DESC
                    """
                        )
                    )

                    products = result.fetchall()
                    total_products = len(products)

                    if total_products == 0:
                        print(colored_text("\nNo products need enrichment!", "green"))
                        return

                    print(
                        colored_text(
                            f"\nStarting bulk enrichment of {total_products} products...",
                            "bright_cyan",
                        )
                    )
                    print(colored_text("This may take several minutes. Please wait...", "yellow"))

                    stockx_service = StockXService(session)
                    enriched_count = 0
                    skipped_count = 0
                    error_count = 0

                    for i, product in enumerate(products, 1):
                        product_id, name, sku, description, retail_price, release_date = product

                        # Progress indicator
                        progress = (i / total_products) * 100
                        print(
                            colored_text(f"\n[{progress:.1f}%] Processing: {name[:50]}...", "cyan")
                        )

                        try:
                            # Search StockX for this product
                            search_results = await stockx_service.search_stockx_catalog(
                                name, page_size=3
                            )

                            if (
                                search_results
                                and "results" in search_results
                                and search_results["results"]
                            ):
                                # Find best match (could be improved with fuzzy matching)
                                best_match = None
                                for result in search_results["results"]:
                                    result_title = result.get("title", "").lower()
                                    if name.lower() in result_title or any(
                                        word in result_title for word in name.lower().split()[:2]
                                    ):
                                        best_match = result
                                        break

                                if not best_match:
                                    best_match = search_results["results"][
                                        0
                                    ]  # Fallback to first result

                                # Extract enrichment data
                                new_description = best_match.get("description") or best_match.get(
                                    "title"
                                )
                                new_retail_price = best_match.get("retailPrice")
                                new_release_date = best_match.get("releaseDate")
                                stockx_product_id = best_match.get("id")

                                # Update product in database
                                update_data = {}
                                if not description and new_description:
                                    update_data["description"] = new_description[
                                        :1000
                                    ]  # Limit length
                                if not retail_price and new_retail_price:
                                    try:
                                        update_data["retail_price"] = float(new_retail_price)
                                    except (ValueError, TypeError):
                                        pass
                                if not release_date and new_release_date:
                                    try:
                                        from datetime import datetime

                                        update_data["release_date"] = datetime.fromisoformat(
                                            new_release_date.replace("Z", "+00:00")
                                        )
                                    except:
                                        pass

                                if update_data:
                                    await session.execute(
                                        update(Product)
                                        .where(Product.id == product_id)
                                        .values(**update_data)
                                    )

                                    # Update inventory items with StockX ID
                                    if stockx_product_id:
                                        await session.execute(
                                            text(
                                                """
                                            UPDATE products.inventory 
                                            SET external_ids = COALESCE(external_ids, '{}') || :stockx_data
                                            WHERE product_id = :product_id
                                        """
                                            ),
                                            {
                                                "stockx_data": f'{{"stockx_product_id": "{stockx_product_id}"}}',
                                                "product_id": str(product_id),
                                            },
                                        )

                                    enriched_count += 1
                                    print(
                                        colored_text(
                                            f"  ✓ Updated: {', '.join(update_data.keys())}", "green"
                                        )
                                    )
                                else:
                                    skipped_count += 1
                                    print(colored_text("  - No new data available", "dim"))
                            else:
                                skipped_count += 1
                                print(colored_text("  ✗ No StockX match found", "red"))

                            # Rate limiting - pause between requests
                            await asyncio.sleep(2)

                        except Exception as e:
                            error_count += 1
                            print(colored_text(f"  ✗ Error: {str(e)[:100]}", "red"))
                            continue

                    # Commit all changes
                    await session.commit()

                    print(colored_text("\n" + "=" * 60, "green"))
                    print(colored_text("BULK ENRICHMENT COMPLETE!", "bright_green"))
                    print(colored_text(f"Total Processed: {total_products}", "white"))
                    print(colored_text(f"Successfully Enriched: {enriched_count}", "green"))
                    print(colored_text(f"Skipped (No Data): {skipped_count}", "yellow"))
                    print(colored_text(f"Errors: {error_count}", "red"))
                    print(colored_text("=" * 60, "green"))

                await db_manager.close()

            asyncio.run(bulk_enrich())

        except Exception as e:
            print(colored_text(f"Critical error during bulk enrichment: {str(e)}", "red"))

        wait_for_key()

    def show_enrichment_stats(self):
        """Show product enrichment statistics"""
        clear_screen()
        print(status_icon("info") + colored_text(" ENRICHMENT STATISTICS", "bright_green"))
        print(colored_text("=" * 60, "green"))

        try:
            import asyncio

            from sqlalchemy import text

            from shared.database.connection import db_manager

            async def show_stats():
                await db_manager.initialize()

                async with db_manager.get_session() as session:
                    # Get enrichment stats
                    result = await session.execute(
                        text(
                            """
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN description IS NOT NULL AND description != '' THEN 1 END) as has_description,
                            COUNT(CASE WHEN retail_price IS NOT NULL THEN 1 END) as has_retail_price,
                            COUNT(CASE WHEN release_date IS NOT NULL THEN 1 END) as has_release_date,
                            COUNT(CASE WHEN avg_resale_price IS NOT NULL THEN 1 END) as has_resale_price
                        FROM products.products
                    """
                        )
                    )

                    stats = result.fetchone()
                    total = stats[0]

                    if total == 0:
                        print(colored_text("\nNo products found in database", "yellow"))
                    else:
                        desc_pct = (stats[1] / total) * 100
                        retail_pct = (stats[2] / total) * 100
                        release_pct = (stats[3] / total) * 100
                        resale_pct = (stats[4] / total) * 100

                        print(colored_text("\nEnrichment Statistics:", "bright_cyan"))
                        print(colored_text("-" * 30, "cyan"))
                        print(colored_text(f"Total Products: {total}", "white"))
                        print(
                            colored_text(f"With Description: {stats[1]} ({desc_pct:.1f}%)", "white")
                        )
                        print(
                            colored_text(
                                f"With Retail Price: {stats[2]} ({retail_pct:.1f}%)", "white"
                            )
                        )
                        print(
                            colored_text(
                                f"With Release Date: {stats[3]} ({release_pct:.1f}%)", "white"
                            )
                        )
                        print(
                            colored_text(
                                f"With Resale Price: {stats[4]} ({resale_pct:.1f}%)", "white"
                            )
                        )

                await db_manager.close()

            asyncio.run(show_stats())

        except Exception as e:
            print(colored_text(f"Error showing stats: {str(e)}", "red"))

        wait_for_key()


if __name__ == "__main__":
    cli = RetroAdminCLI()
    cli.run()
