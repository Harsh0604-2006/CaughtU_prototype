"""
Neo4j Client Module
Handles connection to Neo4j AuraDB and executes Cypher queries
"""
from neo4j import GraphDatabase
from typing import List, Dict, Any
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, SIMULATION_GRAPH, PRODUCTION_GRAPH
import logging

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Client for Neo4j database operations"""
    
    def __init__(self):
        """Initialize Neo4j driver"""
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
    
    def close(self):
        """Close the driver connection"""
        self.driver.close()
    
    def get_servers(self, graph_name: str = PRODUCTION_GRAPH) -> List[Dict[str, Any]]:
        """
        Fetch all relevant nodes from Neo4j (Device, Server, or any primary entity)
        Dynamically adapts to whatever schema exists
        
        Args:
            graph_name: Either "prod" or "sim"
        
        Returns:
            List of node dictionaries with properties
        """
        # First try Server nodes, fall back to Device nodes
        query = """
        MATCH (n)
        WHERE n:Server OR n:Device OR n:Infrastructure
        RETURN n.name as name,
               n.product as product,
               n.version as version,
               n.ip as ip,
               n.os as os,
               n.type as type,
               n.criticality as criticality,
               n.zone as zone,
               labels(n) as node_type
        ORDER BY n.criticality DESC
        LIMIT 100
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            servers = [dict(record) for record in result]
        
        logger.info(f"Fetched {len(servers)} servers from {graph_name} graph")
        return servers
    
    def get_vulnerabilities_for_servers(self, servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fetch actual vulnerabilities from Neo4j via HAS_VULNERABILITY relationships
        
        Args:
            servers: List of node dictionaries
        
        Returns:
            List of vulnerabilities with their related nodes
        """
        if not servers:
            return []
        
        query = """
        MATCH (n)-[r:HAS_VULNERABILITY]->(v:Vulnerability)
        WHERE n.name IN $node_names
        RETURN n.name as source_name,
               labels(n) as source_type,
               v.name as vuln_name,
               v.cve_id as cve_id,
               v.cvss_score as cvss_score,
               v.attack_vector as attack_vector,
               v.attack_complexity as attack_complexity,
               v.exploit_available as exploit_available,
               v.description as description,
               properties(v) as all_properties
        ORDER BY v.cvss_score DESC
        """
        
        node_names = [s.get('name') for s in servers if s.get('name')]
        
        with self.driver.session() as session:
            result = session.run(query, node_names=node_names)
            vulnerabilities = [dict(record) for record in result]
        
        logger.info(f"Fetched {len(vulnerabilities)} vulnerabilities from Neo4j HAS_VULNERABILITY relationships")
        return vulnerabilities
    
    def get_blast_radius(self, server_name: str, graph_name: str = PRODUCTION_GRAPH) -> List[Dict[str, Any]]:
        """
        Calculate blast radius using Cypher traversal
        Returns all nodes reachable from the compromised node (schema-agnostic)
        
        Args:
            server_name: Name of the compromised node
            graph_name: Graph to query
        
        Returns:
            List of affected nodes
        """
        query = """
        MATCH (start {name: $server_name})
        MATCH (start)-[*1..5]->(affected)
        RETURN DISTINCT affected.name as name,
                        labels(affected) as labels,
                        affected.criticality as criticality,
                        affected.type as type
        ORDER BY affected.criticality DESC
        LIMIT 100
        """
        
        with self.driver.session() as session:
            result = session.run(query, server_name=server_name)
            blast_radius = [dict(record) for record in result]
        
        logger.info(f"Blast radius from {server_name}: {len(blast_radius)} nodes affected")
        return blast_radius
    
    def get_high_criticality_servers(self, graph_name: str = PRODUCTION_GRAPH) -> List[Dict[str, Any]]:
        """
        Fetch high/critical criticality nodes from any schema
        
        Args:
            graph_name: Either "prod" or "sim"
        
        Returns:
            List of high-priority nodes
        """
        query = """
        MATCH (n)
        WHERE n.criticality IN ["Critical", "High", "CRITICAL", "HIGH"]
        RETURN n.name as name,
               n.product as product,
               n.version as version,
               n.ip as ip,
               n.type as type,
               n.criticality as criticality,
               labels(n) as node_type
        ORDER BY n.criticality DESC, n.name
        LIMIT 100
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            nodes = [dict(record) for record in result]
        
        return nodes
    
    def check_connection(self) -> bool:
        """
        Test connection to Neo4j
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
            return True
        except Exception as e:
            logger.error(f"Neo4j connection failed: {str(e)}")
            return False
