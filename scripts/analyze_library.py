#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zotero Library Analysis Script - Simplified Version
Only shows collection statistics
"""

import os
import json
import requests
from typing import List, Dict, Any
from collections import defaultdict

class ZoteroAnalyzer:
    """Zotero Library Analyzer - Simplified"""
    
    def __init__(self, user_id: str = None, api_key: str = None):
        """Initialize analyzer"""
        self.base_url = "https://api.zotero.org"
        self.user_id = user_id or os.getenv('ZOTERO_USER_ID') or ""
        self.api_key = api_key or os.getenv('ZOTERO_API_KEY') or ""
        
        if not self.user_id or not self.api_key:
            print("Error: Please set ZOTERO_USER_ID and ZOTERO_API_KEY environment variables")
            return
            
        self.headers = {
            'Zotero-API-Version': '3',
            'Zotero-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """Get all literature items"""
        all_items = []
        start = 0
        limit = 100
        
        while True:
            try:
                url = f"{self.base_url}/users/{self.user_id}/items"
                params = {
                    'format': 'json',
                    'limit': limit,
                    'start': start,
                    'sort': 'dateModified',
                    'direction': 'desc'
                }
                
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                items = response.json()
                if not items:
                    break
                    
                all_items.extend(items)
                start += limit
                
            except Exception as e:
                print(f"Failed to get items: {e}")
                break
        
        return all_items
    
    def get_all_collections(self) -> List[Dict[str, Any]]:
        """Get all collections"""
        try:
            url = f"{self.base_url}/users/{self.user_id}/collections"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            collections = response.json()
            return collections
        except Exception as e:
            print(f"Failed to get collections: {e}")
            return []
    
    def analyze_collection_stats(self, items: List[Dict[str, Any]], 
                               collections: List[Dict[str, Any]]) -> None:
        """Analyze and print collection statistics"""
        
        # Build collection mapping
        collection_map = {c['key']: c['data']['name'] for c in collections}
        
        # Debug: Print all available collections
        print("Available Collections:")
        print("-" * 30)
        for key, name in collection_map.items():
            print(f"Key: {key} -> Name: {name}")
        print()
        
        # Count literature per collection
        collection_stats = defaultdict(int)
        total_literature = 0
        missing_collections = set()  # Track missing collection keys
        
        # Analyze each item
        for item in items:
            data = item['data']
            
            # Skip non-literature items
            item_type = data.get('itemType', 'unknown')
            if item_type == 'note':
                continue
            elif item_type == 'attachment':
                # Only skip attachments that have a parent item
                if data.get('parentItem'):
                    continue
                # Independent attachments are treated as literature
            
            total_literature += 1
            
            # Count literature per collection
            collections_list = data.get('collections', [])
            for collection_key in collections_list:
                collection_name = collection_map.get(collection_key, collection_key)
                collection_stats[collection_name] += 1
                
                # Track missing collections
                if collection_key not in collection_map:
                    missing_collections.add(collection_key)
        
        # Print missing collections warning
        if missing_collections:
            print("Warning: Found references to missing collections:")
            print("-" * 50)
            for missing_key in missing_collections:
                count = collection_stats[missing_key]
                print(f"Missing Collection Key: {missing_key} (referenced by {count} items)")
            print()
        
        # Print results
        print(f"Total Literature Items: {total_literature}")
        print("\nCollection Statistics:")
        print("-" * 40)
        
        # Sort collections by item count
        sorted_collections = sorted(collection_stats.items(), key=lambda x: x[1], reverse=True)
        
        for collection_name, count in sorted_collections:
            # Mark missing collections
            if collection_name in missing_collections:
                print(f"{collection_name}: {count} ⚠️  (Missing collection)")
            else:
                print(f"{collection_name}: {count}")
        
        if not sorted_collections:
            print("No items found in collections")
    
    def run_analysis(self):
        """Run simplified analysis"""
        # Get data
        items = self.get_all_items()
        if not items:
            print("No items found")
            return
        
        collections = self.get_all_collections()
        if not collections:
            print("No collections found")
            return
        
        # Show statistics
        self.analyze_collection_stats(items, collections)


def main():
    """Main function"""
    analyzer = ZoteroAnalyzer()
    if analyzer.user_id and analyzer.api_key:
        analyzer.run_analysis()
    else:
        print("Please set environment variables first:")
        print("export ZOTERO_USER_ID='your_user_id'")
        print("export ZOTERO_API_KEY='your_api_key'")


if __name__ == "__main__":
    main() 