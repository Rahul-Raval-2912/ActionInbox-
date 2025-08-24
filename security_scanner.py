"""Security Scanner for ActionInbox - Detects threats and sensitive data"""

import re
from typing import Dict, List

class SecurityScanner:
    def __init__(self):
        # Malicious patterns
        self.malicious_patterns = [
            r'click here to claim',
            r'urgent.*action.*required',
            r'verify.*account.*immediately',
            r'suspended.*account',
            r'winner.*lottery',
            r'inheritance.*million',
            r'bitcoin.*investment',
            r'crypto.*opportunity'
        ]
        
        # Sensitive data patterns
        self.sensitive_patterns = {
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'password': r'password[\s:=]+\w+',
            'api_key': r'(api[_-]?key|token)[\s:=]+[a-zA-Z0-9_-]+',
            'bank_account': r'\b\d{8,12}\b'
        }
        
        # Suspicious domains
        self.suspicious_domains = [
            'bit.ly', 'tinyurl.com', 'goo.gl', 't.co',
            'phishing-site.com', 'fake-bank.net', 'scam-alert.org'
        ]
    
    def scan_email(self, subject: str, body: str, sender_email: str) -> Dict:
        """Comprehensive security scan of email"""
        
        email_text = f"{subject} {body}".lower()
        
        # Initialize results
        threats = []
        sensitive_data = []
        security_score = 100
        risk_level = "LOW"
        
        # Check for malicious patterns
        for pattern in self.malicious_patterns:
            if re.search(pattern, email_text, re.IGNORECASE):
                threats.append(f"Suspicious phrase detected: {pattern}")
                security_score -= 20
        
        # Check for sensitive data
        for data_type, pattern in self.sensitive_patterns.items():
            matches = re.findall(pattern, f"{subject} {body}", re.IGNORECASE)
            if matches:
                sensitive_data.append({
                    'type': data_type,
                    'count': len(matches),
                    'masked_examples': [self._mask_sensitive(match) for match in matches[:2]]
                })
                security_score -= 15
        
        # Check sender domain
        sender_domain = sender_email.split('@')[1] if '@' in sender_email else ""
        if sender_domain in self.suspicious_domains:
            threats.append(f"Suspicious sender domain: {sender_domain}")
            security_score -= 30
        
        # Check for suspicious links
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, body)
        suspicious_urls = []
        
        for url in urls:
            for domain in self.suspicious_domains:
                if domain in url:
                    suspicious_urls.append(url)
                    security_score -= 25
        
        if suspicious_urls:
            threats.append(f"Suspicious URLs detected: {len(suspicious_urls)} links")
        
        # Determine risk level
        if security_score >= 80:
            risk_level = "LOW"
        elif security_score >= 60:
            risk_level = "MEDIUM"
        elif security_score >= 40:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"
        
        return {
            'security_score': max(0, security_score),
            'risk_level': risk_level,
            'threats_detected': len(threats),
            'threats': threats,
            'sensitive_data_found': len(sensitive_data),
            'sensitive_data': sensitive_data,
            'suspicious_urls': len(suspicious_urls),
            'recommendations': self._get_recommendations(security_score, threats, sensitive_data)
        }
    
    def _mask_sensitive(self, data: str) -> str:
        """Mask sensitive data for display"""
        if len(data) <= 4:
            return "*" * len(data)
        return data[:2] + "*" * (len(data) - 4) + data[-2:]
    
    def _get_recommendations(self, score: int, threats: List, sensitive_data: List) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        if score < 50:
            recommendations.append("HIGH RISK: Do not interact with this email")
            recommendations.append("Report as phishing/spam")
        elif score < 70:
            recommendations.append("CAUTION: Verify sender before taking action")
            recommendations.append("Check URLs before clicking")
        
        if threats:
            recommendations.append("Block sender if suspicious")
        
        if sensitive_data:
            recommendations.append("Handle sensitive data with care")
            recommendations.append("Ensure secure communication channels")
        
        if not recommendations:
            recommendations.append("Email appears safe to process")
        
        return recommendations

def demo_security_scan():
    """Demo the security scanner with sample emails"""
    
    scanner = SecurityScanner()
    
    # Sample emails for demo
    test_emails = [
        {
            'subject': 'URGENT: Your account will be suspended!',
            'body': 'Click here to verify your account immediately or lose access forever! Visit http://phishing-site.com/verify',
            'sender': 'security@fake-bank.net',
            'description': 'Phishing Email'
        },
        {
            'subject': 'Meeting Notes - Project Alpha',
            'body': 'Hi team, here are the meeting notes. My phone is 555-123-4567 if you need to reach me.',
            'sender': 'colleague@company.com',
            'description': 'Business Email with Phone'
        },
        {
            'subject': 'Invoice Payment',
            'body': 'Please process payment to account 1234567890. Credit card ending in 4567 was declined.',
            'sender': 'billing@vendor.com',
            'description': 'Invoice with Financial Data'
        },
        {
            'subject': 'Weekly Newsletter',
            'body': 'Welcome to our weekly update! Check out our latest blog posts and company news.',
            'sender': 'newsletter@company.com',
            'description': 'Safe Newsletter'
        }
    ]
    
    print("ActionInbox Security Scanner Demo")
    print("=" * 50)
    
    for i, email in enumerate(test_emails, 1):
        print(f"\nEmail {i}: {email['description']}")
        print(f"From: {email['sender']}")
        print(f"Subject: {email['subject']}")
        
        # Scan the email
        result = scanner.scan_email(
            email['subject'],
            email['body'], 
            email['sender']
        )
        
        # Display results
        print(f"\nSecurity Analysis:")
        print(f"   Security Score: {result['security_score']}/100")
        print(f"   Risk Level: {result['risk_level']}")
        print(f"   Threats Detected: {result['threats_detected']}")
        print(f"   Sensitive Data: {result['sensitive_data_found']} types found")
        
        if result['threats']:
            print(f"\nThreats:")
            for threat in result['threats']:
                print(f"   • {threat}")
        
        if result['sensitive_data']:
            print(f"\nSensitive Data:")
            for data in result['sensitive_data']:
                print(f"   • {data['type'].upper()}: {data['count']} instances")
        
        print(f"\nRecommendations:")
        for rec in result['recommendations']:
            print(f"   {rec}")
        
        print("-" * 50)

if __name__ == "__main__":
    demo_security_scan()