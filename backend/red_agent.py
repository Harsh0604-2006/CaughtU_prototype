"""
Red Agent Module
Main orchestrator for attack vector analysis and prioritization
Flow: Neo4j Servers → NVD CVEs → LLM Analysis → Prioritized Attack Vectors
"""
from typing import List, Dict, Any, Optional
from neo4j_client import Neo4jClient
from nvd_client import NVDClient
from llm_client import LLMClient
from config import PRODUCTION_GRAPH, SIMULATION_GRAPH, MAX_ATTACK_VECTORS, CVSS_THRESHOLD
import logging

logger = logging.getLogger(__name__)


class RedAgent:
    """
    Red Agent for attack vector analysis
    Combines Neo4j topology, NVD CVE data, and LLM intelligence
    to identify and prioritize attack vectors
    """
    
    def __init__(self):
        """Initialize Red Agent with clients"""
        self.neo4j = Neo4jClient()
        self.nvd = NVDClient()
        self.llm = LLMClient()
    
    def analyze_attack_vectors(
        self,
        graph_name: str = PRODUCTION_GRAPH,
        focus_server: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main method to analyze and prioritize attack vectors
        
        Args:
            graph_name: "prod" or "sim" graph to analyze
            focus_server: Optional specific server to focus on
        
        Returns:
            Structured attack vector analysis with prioritization
        """
        logger.info(f"Red Agent starting analysis on {graph_name} graph")
        
        try:
            # Step 1: Fetch all servers from Neo4j
            logger.info("Step 1: Fetching servers from Neo4j")
            servers = self.neo4j.get_servers(graph_name=graph_name)
            
            if not servers:
                logger.error("No servers found in graph")
                return {
                    "status": "error",
                    "message": "No servers found in graph",
                    "servers_analyzed": 0
                }
            
            logger.info(f"Found {len(servers)} servers")
            
            # Step 2: Get vulnerabilities for these servers
            logger.info("Step 2: Fetching vulnerabilities from NVD")
            vulnerabilities = self.neo4j.get_vulnerabilities_for_servers(servers)
            logger.info(f"Found {len(vulnerabilities)} vulnerabilities")
            
            # Step 3: Enrich vulnerability data with NVD information
            logger.info("Step 3: Enriching with NVD CVE data")
            enriched_vulns = self._enrich_vulnerabilities(servers, vulnerabilities)
            logger.info(f"Enriched {len(enriched_vulns)} vulnerabilities")
            
            # Step 4: Calculate blast radius for high-risk servers
            logger.info("Step 4: Calculating blast radius")
            blast_radii = self._calculate_blast_radii(servers, graph_name)
            
            # Step 5: Use LLM to prioritize attack vectors
            logger.info("Step 5: Using LLM to prioritize attack vectors")
            attack_analysis = self.llm.prioritize_attack_vectors(
                servers=servers,
                vulnerabilities=enriched_vulns,
                blast_radius=blast_radii
            )
            
            # Step 6: Format final output
            result = {
                "status": "success",
                "graph": graph_name,
                "servers_analyzed": len(servers),
                "vulnerabilities_found": len(enriched_vulns),
                "high_risk_servers": self._identify_high_risk_servers(enriched_vulns),
                "attack_vectors": attack_analysis.get("attack_vectors", []),
                "executive_summary": attack_analysis.get("executive_summary", ""),
                "defensive_priorities": attack_analysis.get("defensive_priorities", []),
                "blast_radii_summary": blast_radii
            }
            
            logger.info("Red Agent analysis complete")
            return result
        
        except Exception as e:
            logger.error(f"Red Agent analysis failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "servers_analyzed": 0
            }
    
    def _enrich_vulnerabilities(
        self,
        servers: List[Dict[str, Any]],
        vulnerabilities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich vulnerability data with NVD information
        
        Args:
            servers: List of server nodes
            vulnerabilities: List of vulnerabilities from Neo4j
        
        Returns:
            Enriched vulnerability list with NVD data
        """
        enriched = []
        
        for vuln in vulnerabilities:
            # Get the server for context
            server_name = vuln.get('server_name')
            server = next((s for s in servers if s.get('name') == server_name), None)
            
            if not server:
                continue
            
            # Fetch CVE data from NVD for this product
            product = server.get('product', 'unknown')
            version = server.get('version', '')
            
            nvd_cves = self.nvd.get_cves_for_product(product, version)
            
            # Find matching CVE in NVD data
            cve_id = vuln.get('cve_id', '')
            matching_nvd = next((c for c in nvd_cves if c.get('cve_id') == cve_id), None)
            
            # Merge data
            enriched_vuln = {
                **vuln,
                "product": product,
                "server_ip": server.get('ip'),
                "server_zone": server.get('zone'),
                "server_criticality": server.get('criticality')
            }
            
            # Add NVD data if found
            if matching_nvd:
                enriched_vuln.update({
                    "nvd_description": matching_nvd.get('description'),
                    "exploit_available": matching_nvd.get('exploit_available', False),
                    "cvss_severity": matching_nvd.get('cvss_severity')
                })
            
            enriched.append(enriched_vuln)
        
        return enriched
    
    def _calculate_blast_radii(
        self,
        servers: List[Dict[str, Any]],
        graph_name: str
    ) -> Dict[str, List[str]]:
        """
        Calculate blast radius for each high-risk server
        
        Args:
            servers: List of servers
            graph_name: Graph to query
        
        Returns:
            Dictionary mapping server names to their blast radii
        """
        blast_radii = {}
        
        # Focus on critical/high criticality servers
        high_risk = [s for s in servers if s.get('criticality') in ['Critical', 'High']]
        
        for server in high_risk[:10]:  # Limit to first 10 to save time
            server_name = server.get('name')
            
            try:
                blast_radius = self.neo4j.get_blast_radius(server_name, graph_name)
                affected_nodes = [node.get('name') for node in blast_radius]
                blast_radii[server_name] = affected_nodes
                
                logger.info(f"Blast radius for {server_name}: {len(affected_nodes)} nodes")
            
            except Exception as e:
                logger.warning(f"Failed to calculate blast radius for {server_name}: {str(e)}")
                blast_radii[server_name] = []
        
        return blast_radii
    
    def _identify_high_risk_servers(
        self,
        vulnerabilities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identify servers with highest risk (most vulns, highest CVSS, exploitable)
        
        Args:
            vulnerabilities: List of enriched vulnerabilities
        
        Returns:
            List of high-risk servers sorted by risk
        """
        server_risk = {}
        
        for vuln in vulnerabilities:
            server_name = vuln.get('server_name')
            cvss = vuln.get('cvss_score', 0)
            exploit = vuln.get('exploit_available', False)
            criticality = vuln.get('server_criticality', 'Low')
            
            # Calculate risk score: (CVSS × criticality × exploit)
            criticality_multiplier = {'Critical': 3, 'High': 2, 'Medium': 1, 'Low': 0.5}.get(criticality, 1)
            exploit_multiplier = 1.5 if exploit else 1.0
            risk_score = cvss * criticality_multiplier * exploit_multiplier
            
            if server_name not in server_risk:
                server_risk[server_name] = {
                    'server_name': server_name,
                    'total_vulns': 0,
                    'risk_score': 0,
                    'max_cvss': 0,
                    'exploitable_vulns': 0
                }
            
            server_risk[server_name]['total_vulns'] += 1
            server_risk[server_name]['risk_score'] += risk_score
            server_risk[server_name]['max_cvss'] = max(server_risk[server_name]['max_cvss'], cvss)
            
            if exploit:
                server_risk[server_name]['exploitable_vulns'] += 1
        
        # Sort by risk score
        sorted_servers = sorted(
            server_risk.values(),
            key=lambda x: x['risk_score'],
            reverse=True
        )
        
        return sorted_servers[:5]  # Return top 5 high-risk servers
    
    def close(self):
        """Close all client connections"""
        self.neo4j.close()
        logger.info("Red Agent closed")


# Convenience function for direct usage
def run_red_agent_analysis(graph_name: str = PRODUCTION_GRAPH) -> Dict[str, Any]:
    """
    Convenience function to run red agent analysis
    
    Args:
        graph_name: "prod" or "sim"
    
    Returns:
        Analysis results
    """
    agent = RedAgent()
    try:
        result = agent.analyze_attack_vectors(graph_name=graph_name)
        return result
    finally:
        agent.close()
