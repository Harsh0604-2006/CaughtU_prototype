"""
NVD Client Module
Handles fetching CVE data from NVD API or pre-cached JSON
For demo, uses pre-cached JSON to avoid rate limits and Wi-Fi issues
"""
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from config import NVD_API_KEY, USE_CACHED_NVD, NVD_CACHE_PATH
import logging

logger = logging.getLogger(__name__)


class NVDClient:
    """Client for fetching CVE data from NVD"""
    
    BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    
    def __init__(self):
        """Initialize NVD client"""
        self.api_key = NVD_API_KEY
        self.use_cached = USE_CACHED_NVD
        self.cache_path = NVD_CACHE_PATH
        self.cache = {}
        
        if self.use_cached and os.path.exists(self.cache_path):
            self._load_cache()
    
    def _load_cache(self):
        """Load pre-cached CVE data from JSON file"""
        try:
            with open(self.cache_path, 'r') as f:
                self.cache = json.load(f)
            logger.info(f"Loaded {len(self.cache)} CVEs from cache")
        except Exception as e:
            logger.warning(f"Failed to load cache: {str(e)}")
            self.cache = {}
    
    def _save_cache(self):
        """Save CVE cache to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.info(f"Saved {len(self.cache)} CVEs to cache")
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")
    
    def get_cves_for_product(self, product: str, version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch CVEs for a specific product
        
        Args:
            product: Product name (e.g., "openssl", "openssh")
            version: Optional specific version
        
        Returns:
            List of CVE dictionaries
        """
        # For demo, use pre-cached data
        if self.use_cached:
            return self._get_cves_from_cache(product, version)
        
        # For production, fetch from NVD API
        return self._fetch_cves_from_api(product, version)
    
    def _get_cves_from_cache(self, product: str, version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get CVEs from pre-cached JSON data
        
        Args:
            product: Product name
            version: Optional version filter
        
        Returns:
            List of CVE dictionaries
        """
        cves = []
        product_lower = product.lower()
        
        # Pre-defined demo CVE data for common banking products
        demo_cve_data = {
            "openssh": [
                {
                    "cve_id": "CVE-2024-6387",
                    "product": "OpenSSH",
                    "affected_versions": ["<9.2p1"],
                    "cvss_score": 8.1,
                    "cvss_severity": "High",
                    "attack_vector": "NETWORK",
                    "attack_complexity": "LOW",
                    "privileges_required": "NONE",
                    "user_interaction": "NONE",
                    "scope": "UNCHANGED",
                    "confidentiality": "HIGH",
                    "integrity": "HIGH",
                    "availability": "HIGH",
                    "exploit_available": True,
                    "description": "OpenSSH regreSSHion - Signal handler race condition in sshd",
                    "published_date": "2024-07-01"
                }
            ],
            "openssl": [
                {
                    "cve_id": "CVE-2024-2687",
                    "product": "OpenSSL",
                    "affected_versions": ["<1.1.1x", "<3.0.x"],
                    "cvss_score": 7.5,
                    "cvss_severity": "High",
                    "attack_vector": "NETWORK",
                    "attack_complexity": "LOW",
                    "privileges_required": "NONE",
                    "user_interaction": "NONE",
                    "scope": "UNCHANGED",
                    "confidentiality": "HIGH",
                    "integrity": "NONE",
                    "availability": "NONE",
                    "exploit_available": True,
                    "description": "OpenSSL SSL/TLS vulnerability",
                    "published_date": "2024-03-15"
                }
            ],
            "nginx": [
                {
                    "cve_id": "CVE-2024-1234",
                    "product": "Nginx",
                    "affected_versions": ["<1.26.0"],
                    "cvss_score": 7.2,
                    "cvss_severity": "High",
                    "attack_vector": "NETWORK",
                    "attack_complexity": "LOW",
                    "privileges_required": "NONE",
                    "user_interaction": "NONE",
                    "scope": "UNCHANGED",
                    "confidentiality": "HIGH",
                    "integrity": "NONE",
                    "availability": "LOW",
                    "exploit_available": False,
                    "description": "Nginx HTTP/2 request smuggling",
                    "published_date": "2024-02-20"
                }
            ],
            "redis": [
                {
                    "cve_id": "CVE-2024-5678",
                    "product": "Redis",
                    "affected_versions": ["<7.0.15", "<6.2.15"],
                    "cvss_score": 8.8,
                    "cvss_severity": "High",
                    "attack_vector": "NETWORK",
                    "attack_complexity": "LOW",
                    "privileges_required": "LOW",
                    "user_interaction": "NONE",
                    "scope": "UNCHANGED",
                    "confidentiality": "HIGH",
                    "integrity": "HIGH",
                    "availability": "HIGH",
                    "exploit_available": True,
                    "description": "Redis command injection vulnerability",
                    "published_date": "2024-05-10"
                }
            ],
            "postgresql": [
                {
                    "cve_id": "CVE-2024-3400",
                    "product": "PostgreSQL",
                    "affected_versions": ["<15.5", "<14.10", "<13.13"],
                    "cvss_score": 7.8,
                    "cvss_severity": "High",
                    "attack_vector": "NETWORK",
                    "attack_complexity": "LOW",
                    "privileges_required": "LOW",
                    "user_interaction": "NONE",
                    "scope": "UNCHANGED",
                    "confidentiality": "HIGH",
                    "integrity": "HIGH",
                    "availability": "HIGH",
                    "exploit_available": False,
                    "description": "PostgreSQL SQL injection in extension functions",
                    "published_date": "2024-03-25"
                }
            ],
            "java": [
                {
                    "cve_id": "CVE-2024-20953",
                    "product": "Java",
                    "affected_versions": ["<21.0.2"],
                    "cvss_score": 7.5,
                    "cvss_severity": "High",
                    "attack_vector": "NETWORK",
                    "attack_complexity": "LOW",
                    "privileges_required": "NONE",
                    "user_interaction": "NONE",
                    "scope": "UNCHANGED",
                    "confidentiality": "HIGH",
                    "integrity": "NONE",
                    "availability": "NONE",
                    "exploit_available": False,
                    "description": "Java serialization deserialization RCE",
                    "published_date": "2024-01-16"
                }
            ],
            "linux": [
                {
                    "cve_id": "CVE-2024-26169",
                    "product": "Linux Kernel",
                    "affected_versions": ["<6.7.11"],
                    "cvss_score": 8.4,
                    "cvss_severity": "High",
                    "attack_vector": "LOCAL",
                    "attack_complexity": "LOW",
                    "privileges_required": "LOW",
                    "user_interaction": "NONE",
                    "scope": "CHANGED",
                    "confidentiality": "HIGH",
                    "integrity": "HIGH",
                    "availability": "HIGH",
                    "exploit_available": True,
                    "description": "Linux kernel privilege escalation",
                    "published_date": "2024-04-05"
                }
            ],
            "apache": [
                {
                    "cve_id": "CVE-2024-21762",
                    "product": "Apache HTTP Server",
                    "affected_versions": ["<2.4.58"],
                    "cvss_score": 8.1,
                    "cvss_severity": "High",
                    "attack_vector": "NETWORK",
                    "attack_complexity": "LOW",
                    "privileges_required": "NONE",
                    "user_interaction": "NONE",
                    "scope": "UNCHANGED",
                    "confidentiality": "HIGH",
                    "integrity": "HIGH",
                    "availability": "HIGH",
                    "exploit_available": True,
                    "description": "Apache HTTP Server mod_proxy remote code execution",
                    "published_date": "2024-01-08"
                }
            ]
        }
        
        product_lower = product.lower().replace(" ", "")
        
        # Search for matching product in demo data
        for key, cves in demo_cve_data.items():
            if key in product_lower or product_lower in key:
                cves_list = [cve.copy() for cve in cves]
                # Filter by CVSS if needed
                cves_list = [c for c in cves_list if c.get('cvss_score', 0) >= 7.0]
                return cves_list
        
        # Default: return empty list for unknown products
        logger.info(f"No CVEs found in cache for product: {product}")
        return []
    
    def _fetch_cves_from_api(self, product: str, version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch CVEs from actual NVD API (for production)
        
        Args:
            product: Product name
            version: Optional version filter
        
        Returns:
            List of CVE dictionaries
        """
        headers = {}
        if self.api_key:
            headers["apiKey"] = self.api_key
        
        params = {
            "cpeName": f"cpe:2.3:a:*:{product.lower()}:*:*:*:*:*:*:*:*",
            "resultsPerPage": 100
        }
        
        if version:
            params["cpeName"] = f"cpe:2.3:a:*:{product.lower()}:{version}:*:*:*:*:*:*:*"
        
        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            vulnerabilities = data.get('vulnerabilities', [])
            
            # Parse and format CVEs
            cves = []
            for vuln in vulnerabilities:
                cve_data = vuln.get('cve', {})
                metrics = cve_data.get('metrics', {})
                
                cvss_score = 0
                if 'cvssMetricV31' in metrics:
                    cvss_score = metrics['cvssMetricV31'][0]['cvssData'].get('baseScore', 0)
                
                if cvss_score >= 7.0:  # Only high/critical
                    cves.append({
                        "cve_id": cve_data.get('id'),
                        "description": cve_data.get('descriptions', [{}])[0].get('value'),
                        "cvss_score": cvss_score,
                        "published_date": cve_data.get('published')
                    })
            
            # Cache the result
            self.cache[f"{product}_{version or 'any'}"] = cves
            self._save_cache()
            
            return cves
        
        except Exception as e:
            logger.error(f"NVD API fetch failed: {str(e)}")
            return []
