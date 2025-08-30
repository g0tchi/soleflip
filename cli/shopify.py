#!/usr/bin/env python3
"""
Shopify API Helper for Retro CLI
Handles Shopify REST API operations with security focus
"""

import json
import csv
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config, ShopifyConfig
from utils import colored_text, progress_bar, clear_screen

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShopifyManager:
    """Shopify API operations manager"""

    def __init__(self, config: Config):
        self.config = config
        self.shopify_config: Optional[ShopifyConfig] = config.shopify

        # Setup HTTP session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        if self.shopify_config:
            self.session.headers.update(
                {
                    "X-Shopify-Access-Token": self.shopify_config.access_token,
                    "Content-Type": "application/json",
                }
            )

    def check_connection(self) -> bool:
        """Check if Shopify API is accessible"""
        if not self.shopify_config:
            return False

        try:
            url = f"{self.shopify_config.base_url}/shop.json"
            response = self.session.get(url, timeout=10)
            return response.status_code == 200

        except requests.RequestException:
            return False

    def get_shop_info(self) -> Optional[Dict[str, Any]]:
        """Get shop information"""
        if not self.shopify_config:
            return None

        try:
            url = f"{self.shopify_config.base_url}/shop.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            return response.json().get("shop", {})

        except requests.RequestException as e:
            logger.error(f"Failed to get shop info: {e}")
            return None

    def list_products(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List Shopify products"""
        if not self.check_connection():
            print(colored_text("❌ Shopify not connected!", "red"))
            return []

        try:
            clear_screen()
            print(colored_text("🛍️  SHOPIFY PRODUCTS", "bright_blue"))
            print(colored_text("═" * 50, "blue"))

            url = f"{self.shopify_config.base_url}/products.json"
            params = {"limit": min(limit, 250)}  # Shopify limit

            print(colored_text("Fetching products...", "cyan"))
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            products = response.json().get("products", [])

            if not products:
                print(colored_text("No products found", "yellow"))
                return []

            # Display products
            print(colored_text(f"\nFound {len(products)} products:", "bright_green"))
            print(colored_text("-" * 80, "dim"))

            for i, product in enumerate(products[:20], 1):  # Show first 20
                title = product.get("title", "Untitled")[:40]
                product_type = product.get("product_type", "Unknown")
                vendor = product.get("vendor", "Unknown")
                status = product.get("status", "Unknown")

                # Color code by status
                status_color = {"active": "bright_green", "draft": "yellow", "archived": "red"}.get(
                    status.lower(), "white"
                )

                print(colored_text(f"{i:2d}. {title}", "bright_white"))
                print(
                    colored_text(f"    Type: {product_type} | Vendor: {vendor} | Status: ", "dim"),
                    end="",
                )
                print(colored_text(status.upper(), status_color))

            if len(products) > 20:
                print(colored_text(f"\n... and {len(products) - 20} more products", "dim"))

            return products

        except requests.RequestException as e:
            print(colored_text(f"❌ API Error: {e}", "red"))
            return []
        except Exception as e:
            print(colored_text(f"❌ Error: {e}", "red"))
            return []

        finally:
            input(colored_text("\nPress Enter to continue...", "dim"))

    def update_product(self):
        """Interactive product update"""
        if not self.check_connection():
            print(colored_text("❌ Shopify not connected!", "red"))
            return

        clear_screen()
        print(colored_text("✏️  UPDATE PRODUCT", "bright_blue"))
        print(colored_text("═" * 30, "blue"))

        product_id = input(colored_text("Enter Product ID: ", "bright_green"))

        try:
            product_id = int(product_id)
        except ValueError:
            print(colored_text("Invalid Product ID", "red"))
            return

        # Get current product
        try:
            url = f"{self.shopify_config.base_url}/products/{product_id}.json"
            response = self.session.get(url, timeout=10)

            if response.status_code == 404:
                print(colored_text(f"Product {product_id} not found", "red"))
                return

            response.raise_for_status()
            product = response.json().get("product", {})

            # Display current product info
            print(colored_text(f"\nCurrent Product:", "bright_white"))
            print(colored_text(f"Title: {product.get('title', 'N/A')}", "cyan"))
            print(colored_text(f"Status: {product.get('status', 'N/A')}", "cyan"))
            print(colored_text(f"Type: {product.get('product_type', 'N/A')}", "cyan"))

            # Update options
            print(colored_text("\nWhat would you like to update?", "bright_yellow"))
            print(colored_text("1. Title", "white"))
            print(colored_text("2. Description", "white"))
            print(colored_text("3. Product Type", "white"))
            print(colored_text("4. Status", "white"))
            print(colored_text("0. Cancel", "dim"))

            choice = input(colored_text("\nSelect option: ", "bright_green"))

            update_data = {}

            if choice == "1":
                new_title = input(colored_text("New title: ", "green"))
                if new_title.strip():
                    update_data["title"] = new_title
            elif choice == "2":
                new_desc = input(colored_text("New description: ", "green"))
                if new_desc.strip():
                    update_data["body_html"] = new_desc
            elif choice == "3":
                new_type = input(colored_text("New product type: ", "green"))
                if new_type.strip():
                    update_data["product_type"] = new_type
            elif choice == "4":
                print(colored_text("Status options: active, draft, archived", "dim"))
                new_status = input(colored_text("New status: ", "green"))
                if new_status.lower() in ["active", "draft", "archived"]:
                    update_data["status"] = new_status.lower()
                else:
                    print(colored_text("Invalid status", "red"))
                    return
            else:
                print(colored_text("Update cancelled", "yellow"))
                return

            if not update_data:
                print(colored_text("No changes made", "yellow"))
                return

            # Confirm update
            print(colored_text(f"\nUpdating: {json.dumps(update_data, indent=2)}", "cyan"))
            confirm = input(colored_text("Confirm update? (y/N): ", "yellow"))

            if confirm.lower() != "y":
                print(colored_text("Update cancelled", "yellow"))
                return

            # Apply update
            payload = {"product": update_data}
            response = self.session.put(url, json=payload, timeout=30)
            response.raise_for_status()

            print(colored_text("✅ Product updated successfully!", "bright_green"))

        except requests.RequestException as e:
            print(colored_text(f"❌ API Error: {e}", "red"))
        except Exception as e:
            print(colored_text(f"❌ Error: {e}", "red"))

        input(colored_text("\nPress Enter to continue...", "dim"))

    def sync_inventory(self):
        """Sync inventory with Shopify"""
        if not self.check_connection():
            print(colored_text("❌ Shopify not connected!", "red"))
            return

        clear_screen()
        print(colored_text("🔄 INVENTORY SYNC", "bright_blue"))
        print(colored_text("═" * 30, "blue"))

        try:
            # Get all products with variants
            print(colored_text("Fetching products and inventory...", "cyan"))

            url = f"{self.shopify_config.base_url}/products.json"
            params = {"limit": 250, "fields": "id,title,variants"}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            products = response.json().get("products", [])

            if not products:
                print(colored_text("No products found", "yellow"))
                return

            # Process inventory
            total_variants = sum(len(p.get("variants", [])) for p in products)

            print(
                colored_text(
                    f"Processing {len(products)} products, {total_variants} variants",
                    "bright_white",
                )
            )
            progress_bar("Syncing inventory", total_variants, 0.1)

            # Summary stats
            in_stock = out_of_stock = total_inventory = 0

            for product in products:
                for variant in product.get("variants", []):
                    inventory_qty = variant.get("inventory_quantity", 0)
                    total_inventory += inventory_qty

                    if inventory_qty > 0:
                        in_stock += 1
                    else:
                        out_of_stock += 1

            # Display results
            print(colored_text("\n📊 INVENTORY SUMMARY:", "bright_green"))
            print(colored_text(f"Total Products: {len(products)}", "white"))
            print(colored_text(f"Total Variants: {total_variants}", "white"))
            print(colored_text(f"In Stock: {in_stock}", "bright_green"))
            print(colored_text(f"Out of Stock: {out_of_stock}", "yellow"))
            print(colored_text(f"Total Inventory: {total_inventory:,} units", "bright_cyan"))

        except requests.RequestException as e:
            print(colored_text(f"❌ API Error: {e}", "red"))
        except Exception as e:
            print(colored_text(f"❌ Error: {e}", "red"))

        input(colored_text("\nPress Enter to continue...", "dim"))

    def export_catalog(self):
        """Export product catalog to CSV"""
        if not self.check_connection():
            print(colored_text("❌ Shopify not connected!", "red"))
            return

        clear_screen()
        print(colored_text("📤 EXPORT CATALOG", "bright_blue"))
        print(colored_text("═" * 30, "blue"))

        try:
            # Fetch all products
            all_products = []
            page_info = None
            page = 1

            while True:
                print(colored_text(f"Fetching page {page}...", "cyan"))

                url = f"{self.shopify_config.base_url}/products.json"
                params = {"limit": 250}

                if page_info:
                    params["page_info"] = page_info

                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()

                products = response.json().get("products", [])
                if not products:
                    break

                all_products.extend(products)

                # Check for pagination
                link_header = response.headers.get("Link", "")
                if 'rel="next"' not in link_header:
                    break

                # Extract page_info for next page (simplified)
                page += 1
                if page > 10:  # Safety limit
                    break

            if not all_products:
                print(colored_text("No products to export", "yellow"))
                return

            # Create CSV
            output_file = f"shopify_catalog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Headers
                headers = [
                    "ID",
                    "Title",
                    "Handle",
                    "Product Type",
                    "Vendor",
                    "Status",
                    "Created At",
                    "Updated At",
                    "Tags",
                    "Variant Count",
                ]
                writer.writerow(headers)

                # Progress bar
                progress_bar(f"Exporting {len(all_products)} products", len(all_products), 0.01)

                # Write product data
                for product in all_products:
                    row = [
                        product.get("id", ""),
                        product.get("title", ""),
                        product.get("handle", ""),
                        product.get("product_type", ""),
                        product.get("vendor", ""),
                        product.get("status", ""),
                        product.get("created_at", ""),
                        product.get("updated_at", ""),
                        product.get("tags", ""),
                        len(product.get("variants", [])),
                    ]
                    writer.writerow(row)

            print(
                colored_text(
                    f"✅ Exported {len(all_products):,} products to: {output_file}", "bright_green"
                )
            )

        except requests.RequestException as e:
            print(colored_text(f"❌ API Error: {e}", "red"))
        except Exception as e:
            print(colored_text(f"❌ Error: {e}", "red"))

        input(colored_text("\nPress Enter to continue...", "dim"))

    def get_api_stats(self) -> Dict[str, Any]:
        """Get Shopify API usage statistics"""
        if not self.shopify_config:
            return {"configured": False}

        try:
            url = f"{self.shopify_config.base_url}/shop.json"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                # Get API call limit info from headers
                api_calls = response.headers.get("X-Shopify-Shop-Api-Call-Limit", "Unknown")

                shop_data = response.json().get("shop", {})

                return {
                    "configured": True,
                    "connected": True,
                    "shop_name": shop_data.get("name", "Unknown"),
                    "plan": shop_data.get("plan_name", "Unknown"),
                    "api_calls": api_calls,
                    "response_time": response.elapsed.total_seconds() * 1000,
                }
            else:
                return {
                    "configured": True,
                    "connected": False,
                    "error": f"HTTP {response.status_code}",
                }

        except requests.RequestException as e:
            return {"configured": True, "connected": False, "error": str(e)}


if __name__ == "__main__":
    # Demo Shopify operations
    from config import get_config

    config = get_config()
    shopify_manager = ShopifyManager(config)

    if shopify_manager.check_connection():
        print("✅ Shopify connected successfully")
        stats = shopify_manager.get_api_stats()
        print(f"Shop: {stats.get('shop_name', 'Unknown')}")
        print(f"Plan: {stats.get('plan', 'Unknown')}")
    else:
        print("❌ Shopify connection failed or not configured")
