#!/usr/bin/env python3
"""
Saarthi Returns Enrichment Script - Using MFApi.in
Calculates returns from historical NAV data
"""

import json
import requests
import time
from datetime import datetime, timedelta
import sys

class MFApiEnricher:
    def __init__(self):
        self.input_file = 'saarthi/data/funds-data.json'
        self.output_file = 'saarthi/data/funds-data-enriched.json'
        self.progress_file = 'saarthi/data/enrichment-progress.json'
        self.errors = []
        self.successful = 0
        self.failed = 0
        
    def calculate_returns(self, nav_history):
        """
        Calculate returns from NAV history
        nav_history: list of {'date': 'DD-MM-YYYY', 'nav': 'XXX.XX'}
        """
        try:
            if not nav_history or len(nav_history) < 2:
                return None
            
            # Current NAV (most recent)
            current_nav = float(nav_history[0]['nav'])
            
            returns = {
                '1year': None,
                '3year': None,
                '5year': None
            }
            
            # Helper function to find NAV closest to N days ago
            def get_nav_n_days_ago(days):
                target_date = datetime.now() - timedelta(days=days)
                
                for nav_entry in nav_history:
                    try:
                        nav_date = datetime.strptime(nav_entry['date'], '%d-%m-%Y')
                        
                        # If this NAV is older than target date, use it
                        if nav_date <= target_date:
                            return float(nav_entry['nav'])
                    except:
                        continue
                
                return None
            
            # Calculate 1-year return (~365 days)
            nav_1y = get_nav_n_days_ago(365)
            if nav_1y:
                returns['1year'] = round(((current_nav - nav_1y) / nav_1y) * 100, 2)
            
            # Calculate 3-year return (~1095 days)
            nav_3y = get_nav_n_days_ago(1095)
            if nav_3y:
                returns['3year'] = round(((current_nav - nav_3y) / nav_3y) * 100, 2)
            
            # Calculate 5-year return (~1825 days)
            nav_5y = get_nav_n_days_ago(1825)
            if nav_5y:
                returns['5year'] = round(((current_nav - nav_5y) / nav_5y) * 100, 2)
            
            return returns
            
        except Exception as e:
            return None
    
    def get_fund_data_from_mfapi(self, scheme_code):
        """
        Fetch fund data from MFApi.in
        """
        try:
            url = f"https://api.mfapi.in/mf/{scheme_code}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if data is valid
                if 'data' in data and len(data['data']) > 0:
                    return data['data']
            
            return None
            
        except Exception as e:
            return None
    
    def enrich_funds(self, start_from=0):
        """
        Main enrichment process
        """
        print("=" * 70)
        print("🔍 Saarthi Returns Enrichment - Using MFApi.in")
        print("=" * 70)
        print()
        
        # Load existing data
        print("📥 Loading fund data...")
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        funds = list(data['funds'].items())
        total_funds = len(funds)
        
        print(f"📊 Total funds to enrich: {total_funds}")
        if start_from > 0:
            print(f"▶️  Starting from fund #{start_from}")
        print()
        print("⏱️  Estimated time: ~{} hours".format(round(total_funds * 2 / 3600, 1)))
        print("   (2 seconds per fund with rate limiting)")
        print()
        
        # Process each fund
        for i in range(start_from, total_funds):
            fund_key, fund_info = funds[i]
            fund_name = fund_info['name']
            scheme_code = fund_info.get('scheme_code')
            
            # Progress indicator
            progress_pct = ((i + 1) / total_funds) * 100
            print(f"[{i+1}/{total_funds}] ({progress_pct:.1f}%) {fund_name[:55]}")
            
            if not scheme_code:
                print(f"  ⚠️  No scheme code - skipping")
                self.failed += 1
                continue
            
            # Fetch historical NAV data
            nav_history = self.get_fund_data_from_mfapi(scheme_code)
            
            if nav_history:
                # Calculate returns
                returns = self.calculate_returns(nav_history)
                
                if returns:
                    data['funds'][fund_key]['returns'] = returns
                    self.successful += 1
                    
                    # Show what we got
                    ret_str = []
                    if returns['1year']: ret_str.append(f"1Y:{returns['1year']:+.1f}%")
                    if returns['3year']: ret_str.append(f"3Y:{returns['3year']:+.1f}%")
                    if returns['5year']: ret_str.append(f"5Y:{returns['5year']:+.1f}%")
                    
                    print(f"  ✅ {' | '.join(ret_str)}")
                else:
                    print(f"  ⚠️  Could not calculate returns (insufficient history)")
                    self.failed += 1
            else:
                print(f"  ❌ Failed to fetch data from MFApi")
                self.failed += 1
                self.errors.append({
                    'fund': fund_name,
                    'scheme_code': scheme_code,
                    'error': 'API fetch failed'
                })
            
            # Rate limiting - be nice to the API
            time.sleep(2)  # 2 seconds between requests
            
            # Save progress every 50 funds
            if (i + 1) % 50 == 0:
                self.save_progress(data, i + 1)
                print()
                print(f"💾 Progress saved! ({self.successful} enriched, {self.failed} failed)")
                print(f"⏱️  Estimated time remaining: ~{round((total_funds - i - 1) * 2 / 3600, 1)} hours")
                print()
        
        # Save final data
        print()
        print("=" * 70)
        print("✅ Enrichment Complete!")
        print("=" * 70)
        print(f"📊 Total funds processed: {total_funds}")
        print(f"✅ Successfully enriched: {self.successful}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success rate: {(self.successful/total_funds*100):.1f}%")
        print("=" * 70)
        
        self.save_final(data)
        
        # Save error log
        if self.errors:
            with open('saarthi/data/enrichment-errors.json', 'w') as f:
                json.dump(self.errors, f, indent=2)
            print(f"\n⚠️  Error log saved to: saarthi/data/enrichment-errors.json")
        
        return True
    
    def save_progress(self, data, current_index):
        """Save intermediate progress"""
        data['last_updated'] = datetime.now().isoformat()
        data['enrichment_progress'] = {
            'last_index': current_index,
            'successful': self.successful,
            'failed': self.failed,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def save_final(self, data):
        """Save final enriched data"""
        data['last_updated'] = datetime.now().isoformat()
        data['enrichment_complete'] = True
        data['enrichment_stats'] = {
            'total_funds': len(data['funds']),
            'enriched': self.successful,
            'failed': self.failed,
            'completion_date': datetime.now().isoformat()
        }
        
        # Remove progress tracking
        if 'enrichment_progress' in data:
            del data['enrichment_progress']
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Enriched data saved to: {self.output_file}")
    
    def resume_from_progress(self):
        """Resume from last saved progress"""
        try:
            with open(self.output_file, 'r') as f:
                data = json.load(f)
                
            if 'enrichment_progress' in data:
                last_index = data['enrichment_progress']['last_index']
                print(f"📂 Found previous progress at index {last_index}")
                print(f"   Successful: {data['enrichment_progress']['successful']}")
                print(f"   Failed: {data['enrichment_progress']['failed']}")
                print()
                
                resume = input("Resume from this point? (yes/no): ")
                if resume.lower() == 'yes':
                    self.successful = data['enrichment_progress']['successful']
                    self.failed = data['enrichment_progress']['failed']
                    return last_index
        except:
            pass
        
        return 0


if __name__ == '__main__':
    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║                                                               ║")
    print("║   🧭 SAARTHI RETURNS ENRICHMENT - MFAPI.IN                   ║")
    print("║                                                               ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    print("📋 This script will:")
    print("   1. Fetch historical NAV data from MFApi.in")
    print("   2. Calculate 1Y, 3Y, 5Y returns for all funds")
    print("   3. Save enriched data with returns")
    print()
    print("⚠️  IMPORTANT:")
    print("   • This will take ~4 hours (7,414 funds × 2 sec)")
    print("   • Progress is saved every 50 funds")
    print("   • You can stop and resume anytime (Ctrl+C)")
    print("   • Be patient - API is free but rate-limited")
    print()
    
    proceed = input("Ready to start? (yes/no): ")
    
    if proceed.lower() != 'yes':
        print("\n👋 Exiting. Run again when ready!")
        sys.exit(0)
    
    enricher = MFApiEnricher()
    
    # Check for previous progress
    start_index = enricher.resume_from_progress()
    
    print()
    print("🚀 Starting enrichment process...")
    print()
    
    try:
        enricher.enrich_funds(start_from=start_index)
        print()
        print("🎉 All done! Your data is ready to push to GitHub!")
        
    except KeyboardInterrupt:
        print()
        print()
        print("⏸️  Process interrupted!")
        print("💾 Progress has been saved.")
        print("👉 Run the script again to resume from where you left off.")
        sys.exit(0)
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        print("💾 Progress has been saved up to last checkpoint.")
        sys.exit(1)
