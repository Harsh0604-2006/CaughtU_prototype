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
from config import PRODUCTION_GRAPH, SIMULATION_GRAPH

logger = logging.getLogger(__name__)


class NVDSync:
    """
    Synchronize CVE data from NVD to Neo4j nodes
    Fetches vulnerability data for all products in the graph
    """
    
    def __init__(self):
        """Initialize NVD sync with clients"""
        self.neo4j = Neo4jClient()
        self.nvd = NVDClient()
    
    def sync_cves_to_graph(self, graph_name: str = PRODUCTION_GRAPH) -> Dict[str, Any]:
        """
        Main sync method - fetch CVEs and write to Neo4j
        
        Args:
            graph_name: "prod" or "sim"
        
        Returns:
            Sync results with counts of CVEs processed
        """
        logger.info(f"Starting NVD sync for {graph_name} graph")
        
        try:
            # Step 1: Get all unique products from Neo4j nodes
            logger.info("Step 1: Fetching unique products from Neo4j")
            products = self._get_products_from_graph()
            
            if not products:
                logger.warning("No products found in graph")
                return {
                    "status": "warning",
                    "message": "No products found in graph",
                    "products_processed": 0,
                    "nodes_enriched": 0
                }
            
            logger.info(f"Found {len(products)} unique products")
            
            # Step 2: Fetch CVEs for each product
            logger.info("Step 2: Fetching CVEs from NVD")
            product_cves = {}
            for product in products:
                cves = self.nvd.get_cves_for_product(product)
                if cves:
                    product_cves[product] = cves
                    logger.info(f"  {product}: {len(cves)} CVEs found")
            
            logger.info(f"Fetched CVEs for {len(product_cves)} products")
            
            # Step 3: Write CVE data to corresponding nodes in Neo4j
            logger.info("Step 3: Writing CVE data to Neo4j nodes")
            nodes_enriched = self._write_cves_to_nodes(product_cves)
            
            result = {
                "status": "success",
                "graph": graph_name,
                "products_processed": len(product_cves),
                "nodes_enriched": nodes_enriched,
                "cves_written": sum(len(cves) for cves in product_cves.values())
            }
            
            logger.info(f"NVD sync complete: {nodes_enriched} nodes enriched")
            return result
        
        except Exception as e:
            logger.error(f"NVD sync failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "products_processed": 0,
                "nodes_enriched": 0
            }
    
    def _get_products_from_graph(self) -> List[str]:
        """
        Get all unique product names from Neo4j nodes
        
        Returns:
            List of unique product names
        """
        query = """
        MATCH (n)
        WHERE n.product IS NOT NULL
        RETURN DISTINCT n.product as product
        ORDER BY product
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query)
                products = [record.get("product") for record in result if record.get("product")]
            
            logger.info(f"Retrieved {len(products)} unique products from graph")
            return products
        
        except Exception as e:
            logger.error(f"Failed to get products: {str(e)}")
            return []
    
    def _write_cves_to_nodes(self, product_cves: Dict[str, List[Dict[str, Any]]]) -> int:
        """
        Write CVE data to Neo4j nodes
        For each product, find nodes with that product and update with highest CVSS CVE
        
        Args:
            product_cves: Dictionary mapping product name to CVE list
        
        Returns:
            Number of nodes updated
        """
        nodes_updated = 0
        
        for product, cves in product_cves.items():
            if not cves:
                continue
            
            # Sort by CVSS score (highest first)
            cves_sorted = sorted(cves, key=lambda c: c.get('cvss_score', 0), reverse=True)
            highest_cve = cves_sorted[0]
            
            # Update all nodes with this product with the highest-severity CVE data
            update_query = """
            MATCH (n)
            WHERE n.product = $product
            SET n.cvss_score = $cvss_score,
                n.exploit_available = $exploit_available,
                n.attack_vector = $attack_vector,
                n.cve_id = $cve_id,
                n.cve_updated_at = datetime()
            RETURN count(n) as updated_count
            """
            
            try:
                with self.neo4j.driver.session() as session:
                    result = session.run(
                        update_query,
                        {
                            "product": product,
                            "cvss_score": float(highest_cve.get('cvss_score', 0)),
                            "exploit_available": "true" if highest_cve.get('exploit_available') else "false",
                            "attack_vector": highest_cve.get('attack_vector', 'Unknown'),
                            "cve_id": highest_cve.get('cve_id', 'Unknown')
                        }
                    )
                    
                    record = result.single()
                    count = record.get("updated_count") if record else 0
                    nodes_updated += count
                    
                    logger.info(f"  {product}: Updated {count} nodes with CVE {highest_cve.get('cve_id')}")
            
            except Exception as e:
                logger.warning(f"Failed to update nodes for {product}: {str(e)}")
        
        return nodes_updated
    
    def close(self):
        """Close database connection"""
        self.neo4j.close()
        logger.info("NVD Sync closed")


def run_nvd_sync(graph_name: str = PRODUCTION_GRAPH) -> Dict[str, Any]:
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
    graph = sys.argv[1] if len(sys.argv) > 1 else PRODUCTION_GRAPH
    logger.info(f"Running NVD sync on {graph} graph")
    
    result = run_nvd_sync(graph_name=graph)
    print(f"\nSync Result:")
    print(f"  Status: {result['status']}")
    print(f"  Products: {result['products_processed']}")
    print(f"  Nodes enriched: {result['nodes_enriched']}")
    if result.get('cves_written'):
        print(f"  CVEs written: {result['cves_written']}")
    if result.get('message'):
        print(f"  Message: {result['message']}")
