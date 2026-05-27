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
    Maps Neo4j labels to real software products and fetches CVE data
    """
    
    def __init__(self):
        """Initialize NVD sync with clients"""
        self.neo4j = Neo4jClient()
        self.nvd = NVDClient()
        
        # Mapping of Neo4j labels to software products for CVE lookup
        self.LABEL_TO_PRODUCT = {
            "Server": "Apache Tomcat",
            "NetworkNode": "Cisco IOS XE",
            "API": "API Gateway",
            "Device": "Juniper ScreenOS",
            "User": "Microsoft Active Directory",
            "ComplianceModule": "Splunk Enterprise",
            "SecurityNode": "Fortinet FortiGate",
            "TreasurySystem": "SAP Treasury",
            "CRMSystem": "Salesforce",
            "HRSystem": "Workday",
            "AssetManagement": "Oracle Asset Management",
            "Governance": "ServiceNow",
            "DataCenter": "VMware vSphere",
            "Employee": "SAP SuccessFactors",
            "Transaction": "SWIFT",
            "Loan": "Temenos",
            "Account": "Oracle Banking",
            "Customer": "Salesforce CRM",
            "Branch": "Oracle Branch Banking",
            "Bank": "Core Banking System"
        }
    
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
            # Step 1: Get all labels from Neo4j and map to products
            logger.info("Step 1: Fetching labels from Neo4j")
            labels_to_sync = self._get_labels_from_graph()
            
            if not labels_to_sync:
                logger.warning("No labels found in graph")
                return {
                    "status": "warning",
                    "message": "No labels found in graph",
                    "labels_processed": 0,
                    "nodes_enriched": 0
                }
            
            logger.info(f"Found {len(labels_to_sync)} labels to process")
            
            # Step 2: Fetch CVEs for each product
            logger.info("Step 2: Fetching CVEs from NVD")
            product_cves = {}
            for label, product in labels_to_sync.items():
                cves = self.nvd.get_cves_for_product(product)
                if cves:
                    product_cves[product] = cves
                    logger.info(f"  {product} ({label}): {len(cves)} CVEs found")
                else:
                    logger.warning(f"  {product} ({label}): No CVEs found")
            
            logger.info(f"Fetched CVEs for {len(product_cves)} products")
            
            # Step 3: Write CVE data to corresponding nodes in Neo4j
            logger.info("Step 3: Writing CVE data to Neo4j nodes")
            nodes_enriched = self._write_cves_to_nodes(product_cves, labels_to_sync)
            
            result = {
                "status": "success",
                "graph": graph_name,
                "labels_processed": len(product_cves),
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
    
    def _get_labels_from_graph(self) -> Dict[str, str]:
        """
        Get all labels from Neo4j database and map to products
        
        Returns:
            Dictionary mapping label -> product name
        """
        query = "CALL db.labels()"
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query)
                all_labels = [record[0] for record in result if record[0]]
            
            # Map labels to products
            labels_to_sync = {}
            for label in all_labels:
                if label in self.LABEL_TO_PRODUCT:
                    product = self.LABEL_TO_PRODUCT[label]
                    labels_to_sync[label] = product
                    logger.info(f"  Mapped label '{label}' -> product '{product}'")
            
            logger.info(f"Retrieved {len(labels_to_sync)} mapped labels from {len(all_labels)} total")
            return labels_to_sync
        
        except Exception as e:
            logger.error(f"Failed to get labels: {str(e)}")
            return {}
    
    def _write_cves_to_nodes(self, product_cves: Dict[str, List[Dict[str, Any]]], labels_to_sync: Dict[str, str]) -> int:
        """
        Write CVE data to Neo4j nodes
        For each label, find nodes with that label and update with highest CVSS CVE
        
        Args:
            product_cves: Dictionary mapping product name to CVE list
            labels_to_sync: Dictionary mapping label -> product name
        
        Returns:
            Number of nodes updated
        """
        nodes_updated = 0
        
        # Create reverse mapping: product -> label
        product_to_label = {v: k for k, v in labels_to_sync.items()}
        
        for product, cves in product_cves.items():
            if not cves:
                continue
            
            label = product_to_label.get(product)
            if not label:
                logger.warning(f"No label mapping found for product: {product}")
                continue
            
            # Sort by CVSS score (highest first)
            cves_sorted = sorted(cves, key=lambda c: c.get('cvss_score', 0), reverse=True)
            highest_cve = cves_sorted[0]
            
            # Update all nodes with this label with the highest-severity CVE data
            update_query = f"""
            MATCH (n:{label})
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
                            "cvss_score": float(highest_cve.get('cvss_score', 0)),
                            "exploit_available": highest_cve.get('exploit_available', False),
                            "attack_vector": highest_cve.get('attack_vector', 'Unknown'),
                            "cve_id": highest_cve.get('cve_id', 'Unknown')
                        }
                    )
                    
                    record = result.single()
                    count = record.get("updated_count") if record else 0
                    nodes_updated += count
                    
                    logger.info(f"  {product} ({label}): Updated {count} nodes with CVE {highest_cve.get('cve_id')} (CVSS: {highest_cve.get('cvss_score')})")
            
            except Exception as e:
                logger.warning(f"Failed to update nodes for {product} ({label}): {str(e)}")
        
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
    print(f"  Labels processed: {result.get('labels_processed', 0)}")
    print(f"  Nodes enriched: {result['nodes_enriched']}")
    if result.get('cves_written'):
        print(f"  CVEs written: {result['cves_written']}")
    if result.get('message'):
        print(f"  Message: {result['message']}")
