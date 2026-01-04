#!/usr/bin/env python3
"""
Saarthi Fund Data Updater - REALLY FIXED THIS TIME!
The issue: Fund name is in field index 3, not 2!
"""

import json
import requests
from datetime import datetime
import re
import sys
import os

class FundDataUpdater:
    def __init__(self):
        self.funds_data = {}
        self.errors = []
        self.output_dir = 'saarthi/data'
        
    def fetch_amfi_nav_data(self):
        """Fetch NAV data from AMFI"""
        print("📥 Fetching AMFI NAV data...")
        
        try:
            url = 'https://portal.amfiindia.com/spages/NAVAll.txt'
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            lines = response.text.split('\n')
            current_amc = None
            fund_count = 0
            
            for line in lines:
                line = line.strip()
                
                # AMC name line
                if line and not line[0].isdigit():
                    current_amc = line
                    continue
                
                # Fund data line
                if ';' in line:
                    parts = line.split(';')
                    
                    # AMFI format has 6 fields: Code;ISIN;-;Name;NAV;Date
                    if len(parts) >= 6:
                        scheme_code = parts[0].strip()
                        scheme_name = parts[3].strip()  # ← FIXED: Index 3, not 2!
                        nav_str = parts[4].strip()      # ← FIXED: Index 4, not 3!
                        nav_date = parts[5].strip()     # ← FIXED: Index 5, not 4!
                        
                        # Include ALL funds (Direct, Regular, Growth, Dividend, etc.)
                        # GitHub Pages is the comprehensive fallback database
                        
                        # Skip if no valid data
                        if not scheme_name or not scheme_code:
                            continue
                        
                        clean_name = self.clean_fund_name(scheme_name)
                        
                        # Parse NAV
                        try:
                            nav = float(nav_str) if nav_str else None
                        except:
                            nav = None
                        
                        if clean_name not in self.funds_data:
                            self.funds_data[clean_name] = {
                                'name': scheme_name,
                                'amc': current_amc,
                                'scheme_code': scheme_code,
                                'nav': nav,
                                'nav_date': nav_date,
                                'category': self.determine_category(clean_name),
                                'returns': {'1year': None, '3year': None, '5year': None},
                                'benchmark': {'name': 'N/A', 'returns': {'1year': None}},
                                'source': 'AMFI India',
                                'last_updated': datetime.now().strftime('%Y-%m-%d')
                            }
                            fund_count += 1
            
            print(f"✅ Fetched {fund_count} mutual funds from AMFI (all variants)")
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
        elif 'infrastructure' in name_lower or 'banking' in name_lower or 'technology' in name_lower or 'healthcare' in name_lower or 'defence' in name_lower or 'psu' in name_lower or 'manufacturing' in name_lower:
            return 'Equity - Sectoral'
        else:
            return 'Other'
    
    def add_dummy_aum(self):
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
            
            index_data = {
                'version': datetime.now().strftime('%Y.%m'),
                'total_funds': len(self.funds_data),
                'funds': sorted(list(self.funds_data.keys()))
            }
            
            with open(f'{self.output_dir}/funds-index.json', 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Created funds-index.json")
            
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
        print("=" * 60)
        print("🧭 Saarthi Fund Data Updater - BluSummit")
        print("=" * 60)
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self.fetch_amfi_nav_data():
            print("❌ Failed to fetch AMFI data. Aborting.")
            return False
        
        self.add_dummy_aum()
        
        if not self.generate_json_files():
            print("❌ Failed to generate JSON files. Aborting.")
            return False
        
        print()
        print("=" * 60)
        print("✅ Update Complete!")
        print(f"📊 Total funds: {len(self.funds_data)}")
        print(f"⚠️ Errors: {len(self.errors)}")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        print(f"📁 Files created in {self.output_dir}/:")
        print("   - funds-data.json")
        print("   - funds-index.json")
        print("   - metadata.json")
        print()
        print("🚀 Next steps:")
        print("   1. git add saarthi/")
        print("   2. git commit -m 'Add Saarthi fund data'")
        print("   3. git push origin main")
        print()
        print("🌐 Data will be available at:")
        print("   https://blusummit.github.io/saarthi/data/funds-data.json")
        
        return True


if __name__ == '__main__':
    try:
        import requests
    except ImportError:
        print("❌ Error: 'requests' library not found")
        print("📦 Please install it with: pip3 install requests")
        sys.exit(1)
    
    updater = FundDataUpdater()
    success = updater.run()
    sys.exit(0 if success else 1)
