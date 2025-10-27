#!/usr/bin/env python3
"""Test script for X (Twitter) trends fetching functionality."""

import sys
import unittest
from unittest.mock import patch, MagicMock
from platforms.x import fetch_x_trends


class TestFetchXTrends(unittest.TestCase):
    """Unit tests for fetch_x_trends function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_trends_data = [
            {'name': '#Bitcoin', 'url': 'https://twitter.com/search?q=%23Bitcoin', 'tweet_volume': 50000},
            {'name': '#Ethereum', 'url': 'https://twitter.com/search?q=%23Ethereum', 'tweet_volume': 30000},
            {'name': '#Sports', 'url': 'https://twitter.com/search?q=%23Sports', 'tweet_volume': 100000},
            {'name': 'DeFi Protocol', 'url': 'https://twitter.com/search?q=DeFi', 'tweet_volume': 15000},
            {'name': '#Politics', 'url': 'https://twitter.com/search?q=%23Politics', 'tweet_volume': 75000},
            {'name': 'NFT Drop', 'url': 'https://twitter.com/search?q=NFT', 'tweet_volume': 20000},
            {'name': '#Movies', 'url': 'https://twitter.com/search?q=%23Movies', 'tweet_volume': 40000},
            {'name': 'Solana Network', 'url': 'https://twitter.com/search?q=Solana', 'tweet_volume': 12000},
        ]
    
    @patch('platforms.x.get_trends')
    def test_fetch_x_trends_with_crypto_results(self, mock_get_trends):
        """Test that crypto trends are correctly filtered from all trends."""
        mock_get_trends.return_value = self.mock_trends_data
        
        result = fetch_x_trends()
        
        # Verify get_trends was called with worldwide WOEID
        mock_get_trends.assert_called_once_with(woeid=1)
        
        # Check result structure
        self.assertEqual(result['platform'], 'x')
        self.assertEqual(result['total_trends'], 8)
        self.assertEqual(result['crypto_trends'], 4)
        self.assertIsInstance(result['timestamp'], float)
        
        # Check that only crypto trends are included
        crypto_trend_names = [t['name'] for t in result['trends']]
        self.assertIn('#Bitcoin', crypto_trend_names)
        self.assertIn('#Ethereum', crypto_trend_names)
        self.assertIn('DeFi Protocol', crypto_trend_names)
        self.assertIn('NFT Drop', crypto_trend_names)
        self.assertNotIn('#Sports', crypto_trend_names)
        self.assertNotIn('#Politics', crypto_trend_names)
        
        # Verify matched_keywords are included
        bitcoin_trend = next(t for t in result['trends'] if t['name'] == '#Bitcoin')
        self.assertIn('matched_keywords', bitcoin_trend)
        self.assertIn('bitcoin', bitcoin_trend['matched_keywords'])
    
    @patch('platforms.x.get_trends')
    def test_fetch_x_trends_with_custom_keywords(self, mock_get_trends):
        """Test filtering with custom crypto keywords."""
        mock_get_trends.return_value = self.mock_trends_data
        
        custom_keywords = ['bitcoin', 'ethereum']
        result = fetch_x_trends(crypto_keywords=custom_keywords)
        
        # Should only match Bitcoin and Ethereum, not DeFi or NFT
        self.assertEqual(result['crypto_trends'], 2)
        crypto_trend_names = [t['name'] for t in result['trends']]
        self.assertIn('#Bitcoin', crypto_trend_names)
        self.assertIn('#Ethereum', crypto_trend_names)
        self.assertNotIn('DeFi Protocol', crypto_trend_names)
        self.assertNotIn('NFT Drop', crypto_trend_names)
    
    @patch('platforms.x.get_trends')
    def test_fetch_x_trends_no_crypto_trends(self, mock_get_trends):
        """Test when no crypto trends are found."""
        non_crypto_trends = [
            {'name': '#Sports', 'url': 'https://twitter.com/search?q=%23Sports', 'tweet_volume': 100000},
            {'name': '#Politics', 'url': 'https://twitter.com/search?q=%23Politics', 'tweet_volume': 75000},
        ]
        mock_get_trends.return_value = non_crypto_trends
        
        result = fetch_x_trends()
        
        self.assertEqual(result['platform'], 'x')
        self.assertEqual(result['total_trends'], 2)
        self.assertEqual(result['crypto_trends'], 0)
        self.assertEqual(len(result['trends']), 0)
    
    @patch('platforms.x.get_trends')
    def test_fetch_x_trends_empty_response(self, mock_get_trends):
        """Test handling of empty trends response."""
        mock_get_trends.return_value = []
        
        result = fetch_x_trends()
        
        self.assertEqual(result['platform'], 'x')
        self.assertEqual(result['total_trends'], 0)
        self.assertEqual(result['crypto_trends'], 0)
        self.assertEqual(len(result['trends']), 0)
    
    @patch('platforms.x.get_trends')
    def test_fetch_x_trends_case_insensitive_matching(self, mock_get_trends):
        """Test that keyword matching is case-insensitive."""
        mixed_case_trends = [
            {'name': 'BITCOIN Rally', 'url': 'https://twitter.com/search?q=BITCOIN', 'tweet_volume': 50000},
            {'name': 'EtHeReUm Update', 'url': 'https://twitter.com/search?q=ethereum', 'tweet_volume': 30000},
        ]
        mock_get_trends.return_value = mixed_case_trends
        
        result = fetch_x_trends()
        
        self.assertEqual(result['crypto_trends'], 2)
        self.assertEqual(len(result['trends']), 2)
    
    @patch('platforms.x.get_trends')
    def test_fetch_x_trends_preserves_metadata(self, mock_get_trends):
        """Test that trend metadata (URL, tweet_volume) is preserved."""
        mock_get_trends.return_value = [
            {'name': '#Bitcoin', 'url': 'https://twitter.com/search?q=%23Bitcoin', 'tweet_volume': 50000},
        ]
        
        result = fetch_x_trends()
        
        trend = result['trends'][0]
        self.assertEqual(trend['name'], '#Bitcoin')
        self.assertEqual(trend['url'], 'https://twitter.com/search?q=%23Bitcoin')
        self.assertEqual(trend['tweet_volume'], 50000)
        self.assertIn('matched_keywords', trend)
    
    @patch('platforms.x.get_trends')
    def test_fetch_x_trends_handles_none_tweet_volume(self, mock_get_trends):
        """Test handling of trends with None tweet_volume."""
        trends_with_none = [
            {'name': '#Bitcoin', 'url': 'https://twitter.com/search?q=%23Bitcoin', 'tweet_volume': None},
        ]
        mock_get_trends.return_value = trends_with_none
        
        result = fetch_x_trends()
        
        self.assertEqual(result['crypto_trends'], 1)
        trend = result['trends'][0]
        self.assertIsNone(trend['tweet_volume'])
    
    @patch('platforms.x.get_trends')
    def test_fetch_x_trends_multiple_keyword_matches(self, mock_get_trends):
        """Test that trends matching multiple keywords show all matches."""
        mock_get_trends.return_value = [
            {'name': 'Bitcoin and Ethereum News', 'url': 'https://twitter.com/search?q=crypto', 'tweet_volume': 25000},
        ]
        
        result = fetch_x_trends()
        
        trend = result['trends'][0]
        matched = trend['matched_keywords']
        # Should match bitcoin, ethereum, and potentially others
        self.assertIn('bitcoin', matched)
        self.assertIn('ethereum', matched)
        self.assertGreaterEqual(len(matched), 2)


def run_integration_test():
    """Run an integration test with actual API call (requires authentication)."""
    print("=== Integration Test: Fetch Real X Trends ===")
    print("Note: This requires valid X API credentials\n")
    
    try:
        result = fetch_x_trends()
        
        print(f"Platform: {result['platform']}")
        print(f"Total trends fetched: {result['total_trends']}")
        print(f"Crypto-related trends: {result['crypto_trends']}")
        print(f"Timestamp: {result['timestamp']}\n")
        
        if result['trends']:
            print("Crypto Trends Found:")
            for i, trend in enumerate(result['trends'], 1):
                volume = trend['tweet_volume'] if trend['tweet_volume'] else 'N/A'
                keywords = ', '.join(trend['matched_keywords'])
                print(f"{i}. {trend['name']}")
                print(f"   Tweet Volume: {volume}")
                print(f"   Matched Keywords: {keywords}")
                print(f"   URL: {trend['url']}\n")
        else:
            print("No crypto trends found in current trending topics.")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        print("\nThis is expected if X API credentials are not configured.")
        return False


if __name__ == '__main__':
    # Run unit tests
    print("Running unit tests...\n")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run integration test
    print("\n" + "="*60)
    run_integration_test()
