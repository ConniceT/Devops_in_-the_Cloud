import requests
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple
from .utils.helper import make_post_or_get_request
from functools import lru_cache

class MarketAnalyzer:
    def __init__(self):
        self.bls_api_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        self.bls_api_key = "644e7c11385b4defbffe882d300457e2"  # Register at https://data.bls.gov/registrationEngine/
        
        # Important economic indicators and their series IDs
        self.indicators = {
            'CPI': 'CUSR0000SA0',           # Consumer Price Index
            'UNEMPLOYMENT': 'LNS14000000',    # Unemployment Rate
            'PAYROLLS': 'CES0000000001',     # Total Nonfarm Payrolls
            'WAGES': 'CES0500000003',        # Average Hourly Earnings
            'JOBLESS_CLAIMS': 'ICSA',        # Initial Jobless Claims
            'PPI': 'WPUFD4',                 # Producer Price Index
            'EMPLOYMENT_COST': 'CIU1010000000000A' # Employment Cost Index
        }
        
        # Cache for economic data
        self._cache = {}
        self._cache_duration = 3600  # 1 hour cache for economic data
        
    @lru_cache(maxsize=100)
    def get_economic_data(self, series_id: str, months: int = 12) -> List[Dict]:
        """Get economic data from BLS API"""
        try:
            headers = {'Content-type': 'application/json'}
            data = json.dumps({
                "seriesid": [series_id],
                "startyear": str(datetime.now().year - 1),
                "endyear": str(datetime.now().year),
                "registrationkey": self.bls_api_key
            })
            
            response = requests.post(self.bls_api_url, data=data, headers=headers)
            result = response.json()
            
            if 'Results' in result and result['Results']:
                return result['Results']['series'][0]['data']
            return []
        except Exception as e:
            print(f"Error getting economic data for {series_id}: {str(e)}")
            return []
    
    def analyze_economic_conditions(self) -> Dict:
        """Analyze current economic conditions using BLS data"""
        try:
            # Get latest data for each indicator
            conditions = {}
            risk_factors = 0
            total_factors = len(self.indicators)
            
            for indicator, series_id in self.indicators.items():
                data = self.get_economic_data(series_id)
                if not data:
                    continue
                
                # Get latest value and previous value
                latest = float(data[0]['value'])
                previous = float(data[1]['value'])
                change = ((latest - previous) / previous) * 100
                
                conditions[indicator] = {
                    'latest': latest,
                    'previous': previous,
                    'change': change
                }
                
                # Analyze risk factors
                if indicator == 'CPI' and change > 2:  # High inflation
                    risk_factors += 1
                elif indicator == 'UNEMPLOYMENT' and change > 0:  # Rising unemployment
                    risk_factors += 1
                elif indicator == 'PAYROLLS' and change < 0:  # Declining payrolls
                    risk_factors += 1
                elif indicator == 'WAGES' and change < 0:  # Declining wages
                    risk_factors += 1
                elif indicator == 'JOBLESS_CLAIMS' and change > 5:  # Rising jobless claims
                    risk_factors += 1
                elif indicator == 'PPI' and change > 2:  # High producer inflation
                    risk_factors += 1
            
            # Calculate overall economic sentiment
            risk_level = "low" if risk_factors <= total_factors * 0.3 else \
                        "high" if risk_factors >= total_factors * 0.7 else "medium"
            
            sentiment = 1 - (risk_factors / total_factors)  # 0 to 1, higher is better
            
            return {
                "sentiment": sentiment,
                "risk_level": risk_level,
                "conditions": conditions
            }
        except Exception as e:
            print(f"Error analyzing economic conditions: {str(e)}")
            return {"sentiment": 0.5, "risk_level": "medium", "conditions": {}}
    
    def get_market_sentiment(self, symbol: str) -> Dict:
        """Get market sentiment combining economic data and technical analysis"""
        # Get economic conditions
        economic_data = self.analyze_economic_conditions()
        
        # Get stock-specific data
        stock_url = f"https://api.robinhood.com/fundamentals/{symbol}/"
        stock_data = make_post_or_get_request(stock_url)
        
        # Analyze sector sensitivity to economic conditions
        sector = stock_data.get('sector', '').lower() if stock_data else ''
        sector_sensitivity = {
            'technology': 0.7,    # Less sensitive to economic data
            'healthcare': 0.6,
            'consumer_staples': 0.3,
            'utilities': 0.2,
            'financials': 0.9,    # More sensitive to economic data
            'industrials': 0.8,
            'consumer_discretionary': 0.8,
            'materials': 0.7,
            'energy': 0.6,
            'real_estate': 0.8
        }.get(sector, 0.5)
        
        # Adjust sentiment based on sector sensitivity
        adjusted_sentiment = economic_data['sentiment'] * sector_sensitivity
        
        return {
            "sentiment": adjusted_sentiment,
            "risk_level": economic_data['risk_level'],
            "economic_data": economic_data['conditions'],
            "sector": sector,
            "sector_sensitivity": sector_sensitivity
        }

    
    def calculate_volatility(self, prices: List[float]) -> float:
        """Calculate market volatility using standard deviation"""
        import numpy as np
        return np.std(prices) if len(prices) > 0 else 0
    
    def adjust_position_size(self, base_position: float, volatility: float, risk_level: str) -> float:
        """Adjust position size based on volatility and risk level"""
        volatility_factor = 1 - (volatility * 2)  # Reduce position size as volatility increases
        
        risk_factors = {
            "low": 1.0,
            "medium": 0.7,
            "high": 0.5
        }
        
        return base_position * max(0.2, volatility_factor * risk_factors[risk_level])
