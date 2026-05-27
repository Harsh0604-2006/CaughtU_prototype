"""
NVD Sync Module
Reads node names from Neo4j and fetches CVE data from NVD
Writes cvss_score, exploit_available, attack_vector to nodes
This is Step 1 of the dynamic risk scoring pipeline
"""
import logging
from typing import List, Dict, Any
from neo4j_client import Neo4jClient
from nvd_client import NVDClient
from config import PRODUCTION_GRAPH, SIMULATION_GRAPH, DEFAULT_GRAPH

logger = logging.getLogger(__name__)


class NVDSync:
    """
    Synchronize CVE data from NVD to Neo4j nodes
    Fetches vulnerability data for all products in the graph
    Maps banking node names to common IT products for realistic CVE enrichment
    """
    
    # Mapping of banking node name patterns to NVD product names
    PRODUCT_MAPPING = {
        "ledger": "oracle-database",
        "core": "apache-tomcat",
        "api": "openssl",
        "gateway": "nginx",
        "broker": "apache-activemq",
        "backup": "postgresql",
        "cache": "redis",
        "auth": "openldap",
        "vault": "hashicorp-vault",
        "database": "mysql",
        "server": "linux",
        "service": "apache-http-server",
        "node": "nodejs",
        "worker": "python",
        "queue": "rabbitmq",
        "treasury": "oracle-database",
        "settlement": "postgresql",
        "credit": "apache-tomcat",
        "compliance": "elasticsearch",
        "audit": "postgresql",
    }
    
    def __init__(self):
        """Initialize NVD sync with clients"""
        self.neo4j = Neo4jClient()
        self.nvd = NVDClient()
    
    def sync_cves_to_graph(self, graph_name: str = DEFAULT_GRAPH) -> Dict[str, Any]:
        """
        Main sync method - fetch CVEs and write to Neo4j
        
        Args:
            graph_name: "prod" or "sim"
        
        Returns:
            Sync results with counts of CVEs processed
        """
        logger.info(f"Starting NVD sync for {graph_name} graph")
        
        try:
            # Step 1: Get all nodes and map to products
            logger.info("Step 1: Fetching node names and mapping to NVD products")
            node_to_product = self._get_products_from_graph()
            
            if not node_to_product:
                logger.warning("No nodes found in graph")
                return {
                    "status": "warning",
                    "message": "No nodes found in graph",
                    "nodes_processed": 0,
                    "nodes_enriched": 0
                }
            
            logger.info(f"Found {len(node_to_product)} nodes to enrich")
            
            # Step 2: Get unique products and fetch CVEs
            logger.info("Step 2: Fetching CVEs from NVD for mapped products")
            unique_products = set(node_to_product.values())
            product_cves = {}
            
            for product in unique_products:
                cves = self.nvd.get_cves_for_product(product)
                if cves:
                    product_cves[product] = cves
                    logger.info(f"  {product} ({label}): {len(cves)} CVEs found")
                else:
                    logger.warning(f"  {product} ({label}): No CVEs found")
            
            logger.info(f"Fetched CVEs for {len(product_cves)} products")
            
            # Step 3: Write CVE data to corresponding nodes in Neo4j
            logger.info("Step 3: Writing CVE data to Neo4j nodes")
            nodes_enriched = self._write_cves_to_nodes(node_to_product, product_cves)
            
            result = {
                "status": "success",
                "graph": graph_name,
                "nodes_processed": len(node_to_product),
                "nodes_enriched": nodes_enriched,
                "cves_written": sum(len(cves) for cves in product_cves.values()),
                "products_mapped": len(unique_products)
            }
            
            logger.info(f"NVD sync complete: {nodes_enriched} nodes enriched with CVE data")
            return result
        
        except Exception as e:
            logger.error(f"NVD sync failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e),
                "nodes_processed": 0,
                "nodes_enriched": 0
            }
    
    def _get_products_from_graph(self) -> Dict[str, str]:
        """
        Get all node names from Neo4j and map to NVD product names
        Uses keyword matching to categorize banking systems
        
        Returns:
            Dictionary mapping node names to product names
        """
        query = """
        MATCH (n)
        RETURN DISTINCT n.name as name
        ORDER BY n.name
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query)
                node_names = [record.get("name") for record in result if record.get("name")]
            
            logger.info(f"Retrieved {len(node_names)} unique node names from graph")
            
            # Map each node name to a product
            node_to_product = {}
            for node_name in node_names:
                product = self._map_node_to_product(node_name)
                node_to_product[node_name] = product
                logger.debug(f"  {node_name} → {product}")
            
            return node_to_product
        
        except Exception as e:
            logger.error(f"Failed to get node names: {str(e)}")
            return {}
    
    def _map_node_to_product(self, node_name: str) -> str:
        """
        Map a banking node name to a real NVD product name
        Uses keyword matching against PRODUCT_MAPPING
        
        Args:
            node_name: Name of the banking node
        
        Returns:
            NVD product name for CVE lookup
        """
        node_lower = node_name.lower()
        
        # Check for keyword matches (longest match wins for specificity)
        best_match = None
        best_match_len = 0
        
        for keyword, product in self.PRODUCT_MAPPING.items():
            if keyword in node_lower and len(keyword) > best_match_len:
                best_match = product
                best_match_len = len(keyword)
        
        # Default to apache if no keyword match
        return best_match if best_match else "apache-http-server"
    
    def _write_cves_to_nodes(self, node_to_product: Dict[str, str], product_cves: Dict[str, List[Dict[str, Any]]]) -> int:
        """
        Write CVE data to Neo4j nodes based on their mapped products
        For each node, find its product mapping and update with highest CVSS CVE
        
        Args:
            node_to_product: Dictionary mapping node names to product names
            product_cves: Dictionary mapping product names to CVE lists
        
        Returns:
            Number of nodes updated
        """
        nodes_updated = 0
        
        for node_name, product in node_to_product.items():
            if product not in product_cves or not product_cves[product]:
                continue
            
            # Sort by CVSS score (highest first)
            cves_sorted = sorted(product_cves[product], key=lambda c: c.get('cvss_score', 0), reverse=True)
            highest_cve = cves_sorted[0]
            
            # Update the node with the highest-severity CVE data
            update_query = """
            MATCH (n)
            WHERE n.name = $node_name
            SET n.cvss_score = $cvss_score,
                n.exploit_available = $exploit_available,
                n.attack_vector = $attack_vector,
                n.cve_id = $cve_id,
                n.product_mapped = $product_mapped,
                n.cve_updated_at = datetime()
            RETURN count(n) as updated_count
            """
            
            try:
                with self.neo4j.driver.session() as session:
                    result = session.run(
                        update_query,
                        {
                            "node_name": node_name,
                            "cvss_score": float(highest_cve.get('cvss_score', 0)),
                            "exploit_available": highest_cve.get('exploit_available', False),
                            "attack_vector": highest_cve.get('attack_vector', 'Unknown'),
                            "cve_id": highest_cve.get('cve_id', 'Unknown'),
                            "product_mapped": product
                        }
                    )
                    
                    record = result.single()
                    count = record.get("updated_count") if record else 0
                    if count > 0:
                        nodes_updated += count
                        logger.info(f"  {node_name} ({product}): Updated with {highest_cve.get('cve_id')} (CVSS {highest_cve.get('cvss_score')})")
            
            except Exception as e:
                logger.warning(f"Failed to update node {node_name}: {str(e)}")
        
        return nodes_updated
    
    def close(self):
        """Close database connection"""
        self.neo4j.close()
        logger.info("NVD Sync closed")


def run_nvd_sync(graph_name: str = DEFAULT_GRAPH) -> Dict[str, Any]:
    """
    Convenience function to run NVD sync
    
    Args:
        graph_name: "prod" or "sim"
    
    Returns:
        Sync results
    """
    sync = NVDSync()
    try:
        result = sync.sync_cves_to_graph(graph_name=graph_name)
        return result
    finally:
        sync.close()


if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run sync on specified graph
    graph = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GRAPH
    logger.info(f"Running NVD sync on {graph} graph")
    
    result = run_nvd_sync(graph_name=graph)
    print(f"\nSync Result:")
    print(f"  Status: {result['status']}")
    print(f"  Nodes: {result.get('nodes_processed', 0)}")
    print(f"  Nodes enriched: {result.get('nodes_enriched', 0)}")
    if result.get('products_mapped'):
        print(f"  Products mapped: {result['products_mapped']}")
    if result.get('cves_written'):
        print(f"  CVEs written: {result['cves_written']}")
    if result.get('message'):
        print(f"  Message: {result['message']}")
