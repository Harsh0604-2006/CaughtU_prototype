"""
Example script: How to use the Red Agent
Demonstrates the full attack vector analysis flow
"""
import json
import logging
from red_agent import RedAgent
from config import PRODUCTION_GRAPH, SIMULATION_GRAPH

# Setup logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def example_1_basic_analysis():
    """Example 1: Basic attack vector analysis on production graph"""
    print_section("Example 1: Basic Attack Vector Analysis (Production Graph)")
    
    try:
        agent = RedAgent()
        
        # Run analysis on production graph
        result = agent.analyze_attack_vectors(graph_name=PRODUCTION_GRAPH)
        
        if result.get('status') == 'success':
            print(f"✓ Analysis successful\n")
            print(f"  Servers analyzed: {result['servers_analyzed']}")
            print(f"  Vulnerabilities found: {result['vulnerabilities_found']}")
            print(f"  Timestamp: {result.get('timestamp')}\n")
            
            # Print top attack vectors
            print("Top Attack Vectors:")
            for vector in result.get('attack_vectors', [])[:3]:
                print(f"\n  Rank {vector.get('rank', '?')}:")
                print(f"    Target: {vector.get('target_server')}")
                print(f"    CVE: {vector.get('entry_cve')}")
                print(f"    CVSS: {vector.get('cvss_score')}")
                print(f"    Exploitability: {vector.get('exploitability_score')}/10")
            
            # Print executive summary
            print(f"\nExecutive Summary:")
            print(f"  {result.get('executive_summary', 'N/A')}")
            
            # Print defensive priorities
            print(f"\nDefensive Priorities:")
            for i, priority in enumerate(result.get('defensive_priorities', [])[:5], 1):
                print(f"  {i}. {priority}")
        
        else:
            print(f"✗ Analysis failed: {result.get('message')}")
        
        agent.close()
    
    except Exception as e:
        logger.error(f"Example 1 failed: {str(e)}")


def example_2_simulation_graph():
    """Example 2: Analysis on simulation graph (for testing)"""
    print_section("Example 2: Attack Vector Analysis (Simulation Graph)")
    
    try:
        agent = RedAgent()
        
        # Run analysis on simulation graph
        result = agent.analyze_attack_vectors(graph_name=SIMULATION_GRAPH)
        
        if result.get('status') == 'success':
            print(f"✓ Simulation graph analysis complete\n")
            print(f"  Servers in SIM graph: {result['servers_analyzed']}")
            print(f"  Vulnerabilities in SIM: {result['vulnerabilities_found']}")
            
            # This is the graph we'll use for Red Agent attacks and Blue Agent fixes
            print("\n  This graph can be reset and re-attacked for simulation cycles")
        
        else:
            print(f"✗ Analysis failed: {result.get('message')}")
        
        agent.close()
    
    except Exception as e:
        logger.error(f"Example 2 failed: {str(e)}")


def example_3_servers_and_vulns():
    """Example 3: Fetch servers and vulnerabilities separately"""
    print_section("Example 3: Fetch Servers and Vulnerabilities Separately")
    
    try:
        agent = RedAgent()
        
        # Fetch all servers
        print("Fetching servers from production graph...\n")
        servers = agent.neo4j.get_servers(graph_name=PRODUCTION_GRAPH)
        
        print(f"Found {len(servers)} servers:\n")
        for i, server in enumerate(servers[:5], 1):
            print(f"  {i}. {server['name']}")
            print(f"     Product: {server['product']} {server['version']}")
            print(f"     IP: {server['ip']}")
            print(f"     Criticality: {server['criticality']}")
            print(f"     Zone: {server['zone']}\n")
        
        # Fetch vulnerabilities for these servers
        print("\nFetching vulnerabilities...\n")
        vulnerabilities = agent.neo4j.get_vulnerabilities_for_servers(servers)
        
        print(f"Found {len(vulnerabilities)} vulnerabilities:\n")
        for i, vuln in enumerate(vulnerabilities[:5], 1):
            print(f"  {i}. {vuln['cve_id']} on {vuln['server_name']}")
            print(f"     CVSS: {vuln['cvss_score']}")
            print(f"     Attack Vector: {vuln['attack_vector']}")
            print(f"     Exploit Available: {vuln['exploit_available']}\n")
        
        agent.close()
    
    except Exception as e:
        logger.error(f"Example 3 failed: {str(e)}")


def example_4_blast_radius():
    """Example 4: Calculate blast radius for a specific server"""
    print_section("Example 4: Calculate Blast Radius")
    
    try:
        agent = RedAgent()
        
        # Get high criticality servers
        high_risk = agent.neo4j.get_high_criticality_servers(PRODUCTION_GRAPH)
        
        if high_risk:
            # Focus on the first critical server
            target_server = high_risk[0]['name']
            
            print(f"Calculating blast radius for: {target_server}\n")
            
            # Get blast radius
            blast_radius = agent.neo4j.get_blast_radius(target_server, PRODUCTION_GRAPH)
            
            print(f"If {target_server} is compromised, the following nodes are at risk:\n")
            for i, node in enumerate(blast_radius, 1):
                print(f"  {i}. {node['name']}")
                print(f"     Type: {node['labels']}")
                print(f"     Criticality: {node.get('criticality', 'N/A')}\n")
            
            print(f"Total affected nodes: {len(blast_radius)}")
        
        else:
            print("No high-criticality servers found")
        
        agent.close()
    
    except Exception as e:
        logger.error(f"Example 4 failed: {str(e)}")


def example_5_cve_lookup():
    """Example 5: Look up CVEs for specific products"""
    print_section("Example 5: CVE Lookup for Products")
    
    try:
        agent = RedAgent()
        
        # Products to check
        products = ["openssh", "openssl", "nginx", "redis"]
        
        for product in products:
            print(f"\nCVEs for {product.upper()}:\n")
            
            cves = agent.nvd.get_cves_for_product(product)
            
            if cves:
                for i, cve in enumerate(cves[:3], 1):  # Show top 3
                    print(f"  {i}. {cve.get('cve_id')}")
                    print(f"     CVSS: {cve.get('cvss_score')}")
                    print(f"     Severity: {cve.get('cvss_severity')}")
                    print(f"     Attack Vector: {cve.get('attack_vector')}")
                    print(f"     Exploit Available: {cve.get('exploit_available')}")
                    print(f"     Published: {cve.get('published_date', 'N/A')}\n")
            
            else:
                print(f"  No CVEs found (or {product} not in demo cache)\n")
        
        agent.close()
    
    except Exception as e:
        logger.error(f"Example 5 failed: {str(e)}")


def example_6_high_risk_servers():
    """Example 6: Identify high-risk servers"""
    print_section("Example 6: High-Risk Server Identification")
    
    try:
        agent = RedAgent()
        
        # Run full analysis to get high-risk servers
        result = agent.analyze_attack_vectors(graph_name=PRODUCTION_GRAPH)
        
        if result.get('status') == 'success':
            high_risk = result.get('high_risk_servers', [])
            
            print("Top High-Risk Servers:\n")
            for i, server in enumerate(high_risk[:5], 1):
                print(f"  {i}. {server['server_name']}")
                print(f"     Risk Score: {server['risk_score']:.2f}")
                print(f"     Total Vulnerabilities: {server['total_vulns']}")
                print(f"     Exploitable: {server['exploitable_vulns']}")
                print(f"     Max CVSS: {server['max_cvss']}\n")
        
        else:
            print(f"Analysis failed: {result.get('message')}")
        
        agent.close()
    
    except Exception as e:
        logger.error(f"Example 6 failed: {str(e)}")


def example_7_demo_scenario():
    """Example 7: Real demo scenario - AUTH-03 attack chain"""
    print_section("Example 7: Demo Scenario - AUTH-03 Attack Chain")
    
    print("""
This example walks through the attack chain identified by Red Agent:

SCENARIO: Credential stuffing attack on AUTH-03

1. RECONNAISSANCE
   - Auth-03 is an Authentication Server (CRITICAL criticality)
   - Runs OpenSSH with CVE-2024-6387 (regreSSHion, CVSS 8.1)
   - No authentication required to exploit
   - Exploit code is publicly available

2. INITIAL COMPROMISE
   - Attacker gains RCE on AUTH-03 via CVE-2024-6387
   - Can execute arbitrary commands as root

3. LATERAL MOVEMENT
   - Auth-03 CONNECTS_TO: CBS-APP-01, PAYMENT-GW, SWIFT-NODE, DB-CORE-01
   - Attacker pivots through the network

4. HIGH-VALUE TARGETS COMPROMISED
   - CBS-APP-01: Core Banking System
   - PAYMENT-GW: Payment gateway
   - SWIFT-NODE: SWIFT communication node
   - DB-CORE-01: Database with account information

5. BUSINESS IMPACT
   - $170M+ fraud potential (like 2016 Union Bank SWIFT hack)
   - Payment processing disruption
   - SWIFT message theft/manipulation

REMEDIATION (Generated by Blue Agent):
   - Immediate: Isolate AUTH-03 (block SSH port)
   - Short-term: Patch OpenSSH to 9.2p1+
   - Short-term: Rebuild from golden image
   - Long-term: Continuous vulnerability scanning

DETECTION:
   - UEBA baseline for AUTH-03: 800 RPM
   - Current: 2850 RPM (3.5x anomaly)
   - INC001 flagged for credential stuffing
   - MITRE TTPs: T1110.004 (credential stuffing), T1078 (valid accounts)
    """)
    
    print("\nThis is the complete attack story that Red Agent identifies in seconds.")
    print("Blue Agent then generates the human-executable playbook to fix it.")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                        Red Agent - Example Scripts                         ║
║                                                                            ║
║  Caught U! - GenAI Cybersecurity Platform for Banking                     ║
║  PSBs Hackathon 2026 - IDEA 2.0                                          ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Run examples
    example_1_basic_analysis()
    example_2_simulation_graph()
    example_3_servers_and_vulns()
    example_4_blast_radius()
    example_5_cve_lookup()
    example_6_high_risk_servers()
    example_7_demo_scenario()
    
    print("\n" + "="*80)
    print("  Examples Complete!")
    print("="*80 + "\n")
    print("Next step: Start the FastAPI server to use the REST API")
    print("  $ python -m uvicorn main:app --reload")
    print("\nThen visit: http://localhost:8000/docs")
