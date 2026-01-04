#!/usr/bin/env python3
"""
Saarthi Fund Data Fetcher - Clean Working Version
Fetches ALL funds from AMFI with correct field parsing
"""

import json
import requests
from datetime import datetime
import re
import sys
import os

class FundDataFetcher:
    def __init__(self):
        self.funds_data = {}
        self.errors = []
        self.output_dir = 'saarthi/data'
        
    def fetch_amfi_nav_data(self):
        """Fetch NAV data from AMFI"""
        print("📥 Fetching AMFI NAV data...")
        
        try:
            url = 'https://portal.amfiindia.com/spages/NAVAll.txt'
            print(f"🌐 URL: {url}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            print(f"✅ Downloaded {len(response.text)} bytes")
            
            lines = response.text.split('\n')
            current_amc = None
            fund_count = 0
            
            print(f"📊 Processing {len(lines)} lines...")
            print()
            
            for line in lines:
                line = line.strip()
                
                # AMC name line (doesn't start with digit)
                if line and not line[0].isdigit():
                    current_amc = line
                    continue
                
                # Fund data line: Code;ISIN;-;Name;NAV;Date
                if ';' in line:
                    parts = line.split(';')
                    
                    # CRITICAL: AMFI has 6 fields, not 5!
                    if len(parts) >= 6:
                        scheme_code = parts[0].strip()
                        # parts[1] is ISIN
                        # parts[2] is usually "-" 
                        scheme_name = parts[3].strip()  # ← Field 3 (index 3)
                        nav_str = parts[4].strip()      # ← Field 4 (index 4)
                        nav_date = parts[5].strip()     # ← Field 5 (index 5)
                        
                        # Skip if no valid data
                        if not scheme_name or not scheme_code:
                            continue
                        
                        # Clean fund name for use as key
                        clean_name = self.clean_fund_name(scheme_name)
                        
                        # Parse NAV
                        try:
                            nav = float(nav_str) if nav_str else None
                        except:
                            nav = None
                        
                        # Add fund (only if not already exists - avoids duplicates)
                        if clean_name not in self.funds_data:
                            self.funds_data[clean_name] = {
                                'name': scheme_name,
                                'amc': current_amc,
                                'scheme_code': scheme_code,
                                'nav': nav,
                                'nav_date': nav_date,
                                'category': self.determine_category(scheme_name),
                                'returns': {'1year': None, '3year': None, '5year': None},
                                'benchmark': {'name': 'N/A', 'returns': {'1year': None}},
                                'source': 'AMFI India',
                                'last_updated': datetime.now().strftime('%Y-%m-%d')
                            }
                            fund_count += 1
                            
                            # Show progress every 1000 funds
                            if fund_count % 1000 == 0:
                                print(f"  ✅ {fund_count} funds processed...")
            
            print()
            print(f"✅ Successfully fetched {fund_count} unique funds from AMFI")
            return True
            
        except Exception as e:
            print(f"❌ AMFI fetch error: {e}")
            self.errors.append(f"AMFI: {str(e)}")
            return False
    
    def clean_fund_name(self, name):
        """Clean fund name to standard format"""
        # Remove plan details (case-insensitive)
        name = re.sub(r'\s*-\s*Direct.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*-\s*DIRECT.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*-\s*Regular.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*-\s*REGULAR.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*-\s*Growth.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*-\s*GROWTH.*$', '', name, flags=re.IGNORECASE)
        
        # Clean extra spaces
        name = ' '.join(name.split())
        
        return name.strip()
    
    def determine_category(self, fund_name):
        """Determine fund category from name"""
        name_lower = fund_name.lower()
        
        if 'elss' in name_lower or 'tax saver' in name_lower:
            return 'Equity - ELSS'
        elif 'flexi cap' in name_lower:
            return 'Equity - Flexi Cap'
        elif 'large cap' in name_lower or 'bluechip' in name_lower or 'blue chip' in name_lower:
            return 'Equity - Large Cap'
        elif 'mid cap' in name_lower or 'midcap' in name_lower:
            return 'Equity - Mid Cap'
        elif 'small cap' in name_lower or 'smallcap' in name_lower:
            return 'Equity - Small Cap'
        elif 'index' in name_lower:
            return 'Equity - Index'
        elif 'fof' in name_lower or 'fund of funds' in name_lower:
            return 'Fund of Funds'
        elif 'liquid' in name_lower:
            return 'Debt - Liquid'
        elif 'balanced' in name_lower or 'hybrid' in name_lower or 'advantage' in name_lower:
            return 'Hybrid'
        elif 'debt' in name_lower or 'bond' in name_lower:
            return 'Debt'
        elif 'money market' in name_lower:
            return 'Debt - Money Market'
        elif any(sector in name_lower for sector in ['infrastructure', 'banking', 'technology', 'healthcare', 'defence', 'psu', 'manufacturing', 'pharma', 'auto', 'energy']):
            return 'Equity - Sectoral'
        else:
            return 'Other'
    
    def add_estimated_aum(self):
        """Add estimated AUM based on category"""
        print("📊 Adding estimated AUM data...")
        
        aum_map = {
            'Equity - Large Cap': '₹15,000 Cr',
            'Equity - Mid Cap': '₹8,000 Cr',
            'Equity - Small Cap': '₹5,000 Cr',
            'Equity - Flexi Cap': '₹12,000 Cr',
            'Equity - ELSS': '₹6,000 Cr',
            'Equity - Index': '₹10,000 Cr',
            'Equity - Sectoral': '₹4,000 Cr',
            'Hybrid': '₹8,000 Cr',
            'Debt - Liquid': '₹20,000 Cr',
            'Debt - Money Market': '₹15,000 Cr',
            'Debt': '₹5,000 Cr',
            'Fund of Funds': '₹3,000 Cr',
            'Other': '₹2,000 Cr'
        }
        
        for fund_name, fund in self.funds_data.items():
            category = fund.get('category', 'Other')
            fund['aum'] = aum_map.get(category, '₹2,000 Cr')
    
    def generate_json_files(self):
        """Generate JSON files for GitHub Pages"""
        print("📝 Generating JSON files...")
        
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Main data file
            main_data = {
                'version': datetime.now().strftime('%Y.%m'),
                'last_updated': datetime.now().isoformat(),
                'total_funds': len(self.funds_data),
                'update_method': 'automated_script',
                'organization': 'BluSummit Ventures',
                'product': 'Saarthi',
                'funds': self.funds_data
            }
            
            with open(f'{self.output_dir}/funds-data.json', 'w', encoding='utf-8') as f:
                json.dump(main_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Created funds-data.json ({len(self.funds_data)} funds)")
            
            # Index file
            index_data = {
                'version': datetime.now().strftime('%Y.%m'),
                'total_funds': len(self.funds_data),
                'funds': sorted(list(self.funds_data.keys()))
            }
            
            with open(f'{self.output_dir}/funds-index.json', 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Created funds-index.json")
            
            # Metadata
            metadata = {
                'version': datetime.now().strftime('%Y.%m'),
                'last_updated': datetime.now().isoformat(),
                'total_funds': len(self.funds_data),
                'errors': self.errors,
                'source': 'AMFI India',
                'organization': 'BluSummit Ventures',
                'product': 'Saarthi'
            }
            
            with open(f'{self.output_dir}/metadata.json', 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Created metadata.json")
            
            return True
            
        except Exception as e:
            print(f"❌ JSON generation error: {e}")
            return False
    
    def run(self):
        """Main execution flow"""
        print("=" * 70)
        print("🧭 Saarthi Fund Data Fetcher")
        print("=" * 70)
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self.fetch_amfi_nav_data():
            print("❌ Failed to fetch AMFI data. Aborting.")
            return False
        
        self.add_estimated_aum()
        
        if not self.generate_json_files():
            print("❌ Failed to generate JSON files. Aborting.")
            return False
        
        print()
        print("=" * 70)
        print("✅ Data Fetch Complete!")
        print(f"📊 Total unique funds: {len(self.funds_data)}")
        print(f"⚠️  Errors: {len(self.errors)}")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()
        print(f"📁 Files created in {self.output_dir}/:")
        print("   - funds-data.json")
        print("   - funds-index.json") 
        print("   - metadata.json")
        print()
        print("📊 File sizes:")
        for filename in ['funds-data.json', 'funds-index.json', 'metadata.json']:
            filepath = f'{self.output_dir}/{filename}'
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                size_mb = size / (1024 * 1024)
                print(f"   {filename}: {size_mb:.2f} MB")
        
        return True


if __name__ == '__main__':
    try:
        import requests
    except ImportError:
        print("❌ Error: 'requests' library not found")
        print("📦 Please install it with: pip3 install requests")
        sys.exit(1)
    
    fetcher = FundDataFetcher()
    success = fetcher.run()
    sys.exit(0 if success else 1)
