"""
LLM Client Module
Handles Google Gemini API interactions for attack vector prioritization
"""
import json
from typing import List, Dict, Any
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for Google Gemini LLM interactions"""
    
    def __init__(self):
        """Initialize Gemini client"""
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = GEMINI_MODEL
        self.client = genai.GenerativeModel(self.model)
    
    def prioritize_attack_vectors(
        self,
        servers: List[Dict[str, Any]],
        vulnerabilities: List[Dict[str, Any]],
        blast_radius: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use Gemini to analyze servers, vulnerabilities, and blast radius
        to generate a prioritized list of attack vectors
        
        Args:
            servers: List of server nodes from Neo4j
            vulnerabilities: List of vulnerability relationships
            blast_radius: Pre-calculated blast radius if known
        
        Returns:
            Structured attack vector analysis
        """
        
        # Format the input data for Gemini
        server_summary = self._format_servers(servers)
        vuln_summary = self._format_vulnerabilities(vulnerabilities)
        
        prompt = f"""You are a cybersecurity red team analyst for a major bank. 
Analyze the following bank infrastructure and vulnerabilities to identify the TOP 3 MOST EXPLOITABLE attack vectors.

BANKING INFRASTRUCTURE (Neo4j Topology):
{server_summary}

VULNERABILITY ANALYSIS (from NVD CVE Database):
{vuln_summary}

TASK:
1. For each attack vector, provide:
   - Target Server: Which server to attack
   - Entry Point CVE: Which CVE to exploit
   - Exploitation Strategy: How it would be exploited
   - Blast Radius Impact: What would be compromised if successful
   - Exploitability Score (1-10): How easily exploitable
   - Business Impact: What banking operations are affected

2. Rank by: Exploitability × CVSS Score × Server Criticality × Blast Radius

3. Output MUST be valid JSON format:
{{
  "attack_vectors": [
    {{
      "rank": 1,
      "target_server": "...",
      "target_ip": "...",
      "entry_cve": "...",
      "cvss_score": 8.1,
      "strategy": "...",
      "blast_radius": [...],
      "exploitability_score": 9,
      "business_impact": "..."
    }}
  ],
  "executive_summary": "...",
  "defensive_priorities": ["..."]
}}

Be specific with server names and CVE identifiers from the data provided."""
        
        try:
            response = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2000,
                    temperature=0.7,
                )
            )
            
            # Extract and parse the response
            response_text = response.text
            
            # Try to extract JSON from response
            try:
                # Find JSON block in response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    result = {
                        "raw_response": response_text,
                        "parse_error": "Could not extract JSON from response"
                    }
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                result = {
                    "raw_response": response_text,
                    "parse_error": f"JSON decode error: {str(e)}"
                }
            
            logger.info("Successfully generated attack vector analysis")
            return result
        
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            return {
                "error": str(e),
                "fallback": True
            }
    
    def generate_remediation_playbook(
        self,
        attack_vector: Dict[str, Any],
        server_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a developer-friendly remediation playbook
        
        Args:
            attack_vector: The attack vector to remediate
            server_properties: Properties of affected server
        
        Returns:
            Structured remediation steps
        """
        
        prompt = f"""You are an expert DevSecOps engineer and developer.
A specific attack vector has been identified on a critical server.
Generate a step-by-step DEVELOPER-FRIENDLY REMEDIATION PLAYBOOK.

ATTACK VECTOR:
- Target Server: {attack_vector.get('target_server')}
- Target IP: {attack_vector.get('target_ip')}
- Entry CVE: {attack_vector.get('entry_cve')}
- Attack Strategy: {attack_vector.get('strategy')}
- Blast Radius: {json.dumps(attack_vector.get('blast_radius', []))}

SERVER PROPERTIES:
{json.dumps(server_properties, indent=2)}

OUTPUT REQUIREMENTS:
1. Each step must be highly TECHNICAL and DEVELOPER-FRIENDLY.
2. Provide concrete commands, configuration edits, or code updates needed to patch vulnerabilities.
3. Include both IMMEDIATE workarounds (e.g., isolating network/disabling features) and LONG-TERM fixes (e.g., upgrading package versions).
4. Specify which technical team should execute each step (e.g., Platform Team, Backend Developers, DevOps).
5. Provide clear validation commands (e.g., bash/cli commands to verify the fix).
6. Provide rollback procedures if needed.

CRITICAL: You MUST return ONLY valid, parseable JSON. Do NOT include any conversational introduction, explanations, or Markdown formatting. Just output the raw JSON object starting with {{ and ending with }}.

{{
  "playbook": [
    {{
      "step": 1,
      "phase": "IMMEDIATE" | "SHORT-TERM" | "LONG-TERM",
      "responsible_team": "DevOps | Backend Team | Security Engineering",
      "action": "Detailed technical instruction, including CLI commands or code changes if applicable",
      "success_criteria": "Commands or checks to verify the fix",
      "estimated_time": "15 minutes",
      "rollback_procedure": "How to undo if needed"
    }}
  ],
  "total_remediation_time": "30 minutes",
  "risk_level_before": "Critical",
  "risk_level_after": "Low",
  "validation_checklist": [...]
}}"""
        
        try:
            response = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=8192,
                    temperature=0.0, # Lower temperature to prevent unstructured intros
                )
            )
            
            response_text = response.text
            
            # Extract JSON
            try:
                # Clean the response text by removing markdown if it exists
                clean_text = response_text
                if clean_text.strip().startswith('```json'):
                    clean_text = clean_text.strip()[7:]
                elif clean_text.strip().startswith('```'):
                     clean_text = clean_text.strip()[3:]
                if clean_text.strip().endswith('```'):
                    clean_text = clean_text.strip()[:-3]
                    
                json_start = clean_text.find('{')
                json_end = clean_text.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = clean_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    result = {"raw_response": response_text}
            except json.JSONDecodeError:
                result = {"raw_response": response_text}
            
            logger.info("Successfully generated remediation playbook")
            return result
        
        except Exception as e:
            logger.error(f"Playbook generation failed: {str(e)}")
            return {
                "error": str(e),
                "playbook": []
            }
    
    def _format_servers(self, servers: List[Dict[str, Any]]) -> str:
        """Format servers for prompt"""
        if not servers:
            return "No servers available"
        
        formatted = []
        for server in servers[:20]:  # Limit to first 20 to save tokens
            formatted.append(
                f"- {server.get('name', 'Unknown')} "
                f"({server.get('product', 'Unknown')} {server.get('version', '')}) "
                f"IP: {server.get('ip', 'N/A')} "
                f"Criticality: {server.get('criticality', 'N/A')} "
                f"OS: {server.get('os', 'N/A')}"
            )
        
        return "\n".join(formatted)
    
    def _format_vulnerabilities(self, vulnerabilities: List[Dict[str, Any]]) -> str:
        """Format vulnerabilities for prompt"""
        if not vulnerabilities:
            return "No vulnerabilities found"
        
        formatted = []
        for vuln in vulnerabilities[:30]:  # Limit to first 30
            formatted.append(
                f"- {vuln.get('server_name', 'Unknown')}: "
                f"{vuln.get('cve_id', 'Unknown')} "
                f"(CVSS: {vuln.get('cvss_score', 'N/A')}) "
                f"Vector: {vuln.get('attack_vector', 'N/A')} "
                f"Exploit: {vuln.get('exploit_available', False)}"
            )
        
        return "\n".join(formatted)
