#!/usr/bin/env python3
"""Generate synthetic policy PDFs for the ctrlmap demo.

One-time generator script. Produces realistic multi-page policy PDFs
in ``demo/policies/`` using fpdf2. The output PDFs are committed to
the repository; this script is not needed at runtime.

Usage::

    uv run --with fpdf2 python scripts/generate_demo_pdfs.py
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "demo" / "policies"


class PolicyPDF(FPDF):
    """PDF with standard policy formatting."""

    def __init__(self, title: str, company: str = "Acme Corp") -> None:
        super().__init__()
        self._title = title
        self._company = company
        self.set_auto_page_break(auto=True, margin=25)

    def header(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"{self._company} - {self._title}", align="L")
        self.cell(0, 8, "CONFIDENTIAL", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 0, 0)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def add_title_page(self, version: str, date: str) -> None:
        self.add_page()
        self.ln(40)
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(0, 51, 102)
        self.cell(0, 15, self._company, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(0, 0, 0)
        self.cell(0, 12, self._title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(10)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(80, 80, 80)
        self.cell(
            0,
            8,
            f"Version {version} | Effective: {date}",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.cell(
            0,
            8,
            "Classification: Internal / Confidential",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(20)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(
            0,
            6,
            (
                "This document is the property of Acme Corp and is intended for internal "
                "use only. Unauthorized distribution, reproduction, or disclosure is strictly "
                "prohibited. This policy has been approved by the Chief Information Security "
                "Officer (CISO) and is effective as of the date indicated above."
            ),
            align="C",
        )

    def add_section(self, number: str, title: str) -> None:
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(0, 51, 102)
        self.ln(6)
        self.cell(0, 10, f"{number}  {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def add_subsection(self, number: str, title: str) -> None:
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(51, 51, 51)
        self.cell(0, 8, f"{number}  {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def add_body(self, text: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(2)


def generate_access_control_policy() -> None:
    """Generate Acme Corp Access Control Policy."""
    pdf = PolicyPDF("Access Control Policy")
    pdf.alias_nb_pages()
    pdf.add_title_page("3.1", "January 15, 2025")

    # Section 1 - Purpose
    pdf.add_page()
    pdf.add_section("1", "Purpose and Scope")
    pdf.add_body(
        "This policy establishes the requirements for managing access to Acme Corp "
        "information systems, applications, and data assets. It applies to all employees, "
        "contractors, temporary workers, and third-party service providers who require "
        "access to Acme Corp systems and the Cardholder Data Environment (CDE). "
        "The objective is to ensure that access is granted on a need-to-know and "
        "least-privilege basis, and that all access is properly authorized, authenticated, "
        "and auditable."
    )

    # Section 2 - User Identification
    pdf.add_section("2", "User Identification and Authentication")
    pdf.add_subsection("2.1", "Unique User Identification")
    pdf.add_body(
        "All users must be assigned a unique user ID before they are allowed access to "
        "any system component or cardholder data. Generic, shared, or group IDs are "
        "strictly prohibited for standard operations. Each user ID must be traceable to "
        "an individual person. In cases where shared accounts are technically unavoidable "
        "(e.g., certain legacy systems), compensating controls including enhanced logging "
        "and dual-authorization must be implemented and documented."
    )

    pdf.add_subsection("2.2", "Multi-Factor Authentication (MFA)")
    pdf.add_body(
        "Multi-factor authentication is required for all remote access to the corporate "
        "network and for all access to the Cardholder Data Environment (CDE). MFA must "
        "use at least two of the following factors: something the user knows (password or "
        "passphrase), something the user has (smart card, hardware token, or authenticator "
        "app), or something the user is (biometric verification). MFA tokens must not be "
        "shared between users. Service provider personnel with remote access to customer "
        "premises must also use unique MFA credentials per customer."
    )

    pdf.add_subsection("2.3", "Password Requirements")
    pdf.add_body(
        "All system and application passwords must meet the following minimum requirements: "
        "minimum length of 12 characters, inclusion of numeric and alphabetic characters, "
        "passwords must be changed at least every 90 days, new passwords must not match "
        "any of the last four passwords used, first-time or reset passwords must be unique "
        "to each user and changed upon first use. Default vendor-supplied passwords on all "
        "system components must be changed before deployment to production."
    )

    # Section 3 - Access Authorization
    pdf.add_section("3", "Access Authorization and Role Management")
    pdf.add_subsection("3.1", "Role-Based Access Control (RBAC)")
    pdf.add_body(
        "Access rights must be assigned based on job classification and function, following "
        "the principle of least privilege. Access control systems must default to deny-all "
        "and restrict access to the minimum necessary for business functions. All access "
        "permissions must be documented in an access control matrix that maps roles to "
        "specific system privileges. The Human Resources department must notify IT Security "
        "of all role changes within 24 hours of the change."
    )

    pdf.add_subsection("3.2", "Privileged Access Management")
    pdf.add_body(
        "Administrative and privileged access must be restricted to personnel whose job "
        "duties specifically require such access. Privileged accounts must use separate "
        "credentials from standard user accounts. All privileged access sessions must be "
        "logged and monitored. Privileged access must be reviewed quarterly by the "
        "Information Security team. Privileged accounts must not be used for routine "
        "daily activities such as email or web browsing."
    )

    # Section 4 - Access Reviews
    pdf.add_section("4", "Periodic Access Reviews")
    pdf.add_body(
        "User access rights must be reviewed at least every six months to verify that "
        "access remains appropriate for the user's current role. Access review must be "
        "conducted by system owners in coordination with the Information Security team. "
        "Results of access reviews must be documented and retained for a minimum of "
        "twelve months. Any discrepancies identified during access reviews must be "
        "remediated within 30 calendar days."
    )

    # Section 5 - Termination
    pdf.add_section("5", "Access Revocation and Termination")
    pdf.add_body(
        "Upon termination of employment, all logical and physical access must be revoked "
        "immediately. The Human Resources department must notify IT Security within four "
        "hours of any termination. All authentication tokens, badges, keys, and company "
        "equipment must be collected and documented before the employee departs the "
        "premises. For voluntary departures, access must be revoked no later than the "
        "last day of employment. Accounts belonging to terminated users must be disabled "
        "and retained in a dormant state for 90 days for forensic purposes before deletion."
    )

    # Section 6 - Audit and Compliance
    pdf.add_section("6", "Audit Logging and Monitoring")
    pdf.add_body(
        "All access to system components and cardholder data must be logged. Audit logs "
        "must capture: user identification, type of event, date and time, success or "
        "failure indication, origination of event, and identity or name of affected data, "
        "system component, or resource. Audit trails must be retained for a minimum of "
        "twelve months, with at least three months immediately available for analysis. "
        "Automated alerts must be configured for suspicious activity such as repeated "
        "failed login attempts, privilege escalation, and access from unusual locations."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_DIR / "access_control_policy.pdf"))
    print(f"  Created: {OUTPUT_DIR / 'access_control_policy.pdf'}")


def generate_data_protection_policy() -> None:
    """Generate Acme Corp Data Protection & Encryption Policy."""
    pdf = PolicyPDF("Data Protection & Encryption Policy")
    pdf.alias_nb_pages()
    pdf.add_title_page("2.4", "February 1, 2025")

    # Section 1 - Purpose
    pdf.add_page()
    pdf.add_section("1", "Purpose and Scope")
    pdf.add_body(
        "This policy defines the requirements for protecting sensitive data including "
        "cardholder data (CHD), personally identifiable information (PII), and other "
        "confidential business information throughout its lifecycle. It covers data "
        "classification, encryption standards, key management, data retention, and "
        "secure disposal procedures. This policy applies to all systems that store, "
        "process, or transmit protected data within Acme Corp environments."
    )

    # Section 2 - Data Classification
    pdf.add_section("2", "Data Classification")
    pdf.add_body(
        "All data must be classified according to its sensitivity level. The "
        "classification levels are: Public (information approved for unrestricted "
        "distribution), Internal (information for internal use that could cause minor "
        "harm if disclosed), Confidential (information whose disclosure could cause "
        "significant harm including PII and business-sensitive data), and Restricted "
        "(the highest sensitivity level including cardholder data, authentication "
        "credentials, and cryptographic keys). Data owners are responsible for "
        "assigning the appropriate classification level."
    )

    # Section 3 - Encryption at Rest
    pdf.add_section("3", "Encryption of Data at Rest")
    pdf.add_subsection("3.1", "Encryption Standards")
    pdf.add_body(
        "All cardholder data stored in databases, file systems, backup media, and "
        "portable storage devices must be encrypted using AES-256 or equivalent "
        "cryptographic algorithms approved by NIST. Full-disk encryption must be "
        "enabled on all laptops and workstations that may contain sensitive data. "
        "Database-level encryption using Transparent Data Encryption (TDE) is required "
        "for all production databases containing cardholder data."
    )

    pdf.add_subsection("3.2", "Primary Account Number (PAN) Protection")
    pdf.add_body(
        "The full Primary Account Number must be rendered unreadable anywhere it is "
        "stored, whether in databases, log files, backup media, or removable media. "
        "Acceptable methods include: one-way cryptographic hashes based on strong "
        "cryptography (SHA-256 minimum), truncation (showing no more than the first "
        "six and last four digits), index tokens and pads with securely stored pads, "
        "or strong cryptography with associated key-management processes. PAN must "
        "not appear in plaintext in log files, debugging output, or error messages."
    )

    # Section 4 - Encryption in Transit
    pdf.add_section("4", "Encryption of Data in Transit")
    pdf.add_body(
        "All sensitive data transmitted over public networks must be encrypted using "
        "TLS 1.2 or higher. SSL and early TLS protocols (TLS 1.0, TLS 1.1) are "
        "explicitly prohibited. Wireless networks transmitting cardholder data must "
        "use industry best-practice encryption (WPA3 or WPA2 with AES). Internal "
        "network transmissions of cardholder data between system components must also "
        "be encrypted. Email communications containing sensitive data must use S/MIME "
        "or PGP encryption."
    )

    # Section 5 - Key Management
    pdf.add_section("5", "Cryptographic Key Management")
    pdf.add_subsection("5.1", "Key Generation and Storage")
    pdf.add_body(
        "Cryptographic keys must be generated using approved random number generators "
        "within FIPS 140-2 validated hardware security modules (HSMs) or equivalent. "
        "Keys must be stored in a secure key management system separate from the data "
        "they protect. Key-encrypting keys must be at least as strong as the data-"
        "encrypting keys they protect. Split knowledge and dual control procedures "
        "must be used for all manual key-management operations."
    )

    pdf.add_subsection("5.2", "Key Rotation and Retirement")
    pdf.add_body(
        "Data-encrypting keys must be rotated at least annually or whenever there is "
        "a suspicion of compromise. Retired keys must not be used for new encryption "
        "operations but may be retained in a read-only state for decryption of archived "
        "data. Key destruction must use approved methods such as zeroization of HSM key "
        "slots or cryptographic erasure. All key lifecycle events must be logged and "
        "auditable. A key custodian must be formally designated and must acknowledge "
        "their responsibilities in writing."
    )

    # Section 6 - Data Retention and Disposal
    pdf.add_section("6", "Data Retention and Secure Disposal")
    pdf.add_body(
        "Account data storage must be kept to a minimum. Data retention policies must "
        "define the specific retention period for each data type and the business "
        "justification for retaining it. Cardholder data that exceeds the defined "
        "retention period must be securely deleted on a quarterly basis. Secure deletion "
        "methods include: cryptographic erasure, degaussing of magnetic media, physical "
        "destruction (cross-cut shredding for paper, incineration for optical media). "
        "Sensitive authentication data (SAD) including the full track data, card "
        "verification codes (CVV/CVC), and PINs must never be stored after authorization, "
        "even in encrypted form."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_DIR / "data_protection_policy.pdf"))
    print(f"  Created: {OUTPUT_DIR / 'data_protection_policy.pdf'}")


def generate_network_security_policy() -> None:
    """Generate Acme Corp Network Security Policy."""
    pdf = PolicyPDF("Network Security Policy")
    pdf.alias_nb_pages()
    pdf.add_title_page("4.0", "March 1, 2025")

    # Section 1 - Purpose
    pdf.add_page()
    pdf.add_section("1", "Purpose and Scope")
    pdf.add_body(
        "This policy establishes the requirements for securing Acme Corp network "
        "infrastructure, including internal networks, the Cardholder Data Environment "
        "(CDE), wireless networks, and external-facing connections. It defines the "
        "standards for firewall management, network segmentation, intrusion detection, "
        "vulnerability management, and change control procedures for all network "
        "components. This policy applies to all network devices, security appliances, "
        "and personnel responsible for network operations."
    )

    # Section 2 - Firewall and NSC Management
    pdf.add_section("2", "Network Security Controls (NSC)")
    pdf.add_subsection("2.1", "Firewall Configuration Standards")
    pdf.add_body(
        "Configuration standards for all network security control (NSC) rulesets must "
        "be defined, documented, and maintained. All firewall rules must be reviewed "
        "at least every six months to confirm they are relevant and effective. Firewall "
        "ruleset changes must follow the change management process defined in the "
        "organizational change control policy. Configuration files for NSCs must be "
        "secured from unauthorized access and kept consistent with active network "
        "configurations. Default vendor-supplied credentials on all network devices "
        "must be changed immediately upon deployment."
    )

    pdf.add_subsection("2.2", "Traffic Control Rules")
    pdf.add_body(
        "Inbound traffic to the CDE must be restricted to only traffic that is "
        "necessary, and all other traffic must be specifically denied. Outbound traffic "
        "from the CDE must also be restricted to only traffic that is necessary for "
        "business operations. All allowed services, protocols, and ports must be "
        "identified, approved, and have a defined business justification documented. "
        "Security features must be defined and implemented for all services, protocols, "
        "and ports that are considered insecure to mitigate associated risks."
    )

    # Section 3 - Network Segmentation
    pdf.add_section("3", "Network Segmentation and CDE Isolation")
    pdf.add_body(
        "The Cardholder Data Environment must be isolated from all other networks "
        "through proper network segmentation. An accurate network diagram must be "
        "maintained that shows all connections between the CDE and other networks, "
        "including wireless networks. An accurate data-flow diagram must be maintained "
        "that shows all account data flows across systems and networks and must be "
        "updated whenever changes occur. DMZ zones must be implemented to limit "
        "inbound traffic to only system components that provide authorized publicly "
        "accessible services. Private IP addresses must not be disclosed to external "
        "entities."
    )

    # Section 4 - Wireless Security
    pdf.add_section("4", "Wireless Network Security")
    pdf.add_body(
        "NSCs must be installed between all wireless networks and the CDE, regardless "
        "of whether the wireless network is part of the CDE. All wireless traffic from "
        "wireless networks into the CDE must be denied by default, and only wireless "
        "traffic with an authorized business purpose may be allowed. Wireless networks "
        "must use WPA3 or WPA2 with AES encryption at minimum. Default wireless "
        "encryption keys, passwords, and SNMP community strings must be changed at "
        "installation. A wireless intrusion detection system (WIDS) must be deployed "
        "to detect and alert on unauthorized wireless access points on a quarterly basis."
    )

    # Section 5 - Vulnerability Management
    pdf.add_section("5", "Vulnerability Management")
    pdf.add_body(
        "Internal and external network vulnerability scans must be performed at least "
        "quarterly and after any significant infrastructure change. External scans must "
        "be performed by a PCI SSC Approved Scanning Vendor (ASV). Penetration testing "
        "of the network perimeter and critical systems must be conducted at least annually. "
        "High-risk vulnerabilities (CVSS score 7.0 or above) identified during scanning "
        "must be remediated within 30 calendar days. Critical vulnerabilities must be "
        "patched or mitigated within 72 hours of discovery. All remediation activities "
        "must be documented and verified through re-scanning."
    )

    # Section 6 - Change Management
    pdf.add_section("6", "Network Change Management")
    pdf.add_body(
        "All changes to network connections and to configurations of NSCs must be "
        "approved and managed in accordance with the organizational change control "
        "process. This includes the addition, removal, or modification of any network "
        "connection as well as changes that affect how network security controls perform "
        "their security function. Change requests must document the business justification, "
        "impact analysis, rollback procedures, and security review. Emergency changes "
        "must be reviewed and formally approved within 72 hours of implementation. "
        "All changes must be tested in a non-production environment before deployment."
    )

    # Section 7 - Monitoring and Logging
    pdf.add_section("7", "Network Monitoring and Intrusion Detection")
    pdf.add_body(
        "Network-based intrusion detection or prevention systems (IDS/IPS) must be "
        "deployed at the perimeter of the CDE and at critical points within the network. "
        "All IDS/IPS signatures must be updated within 24 hours of vendor release. "
        "Network traffic logs must be captured and retained for a minimum of twelve "
        "months, with at least three months immediately available for analysis. "
        "Security event monitoring must operate continuously (24/7/365). Automated "
        "alerts must be configured for anomalous network activity including unusual "
        "traffic patterns, unauthorized connection attempts, and data exfiltration "
        "indicators. All critical security alerts must be investigated and documented "
        "within four hours of detection."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_DIR / "network_security_policy.pdf"))
    print(f"  Created: {OUTPUT_DIR / 'network_security_policy.pdf'}")


def generate_incident_response_policy() -> None:
    """Generate Acme Corp Incident Response Policy."""
    pdf = PolicyPDF("Incident Response Policy")
    pdf.alias_nb_pages()
    pdf.add_title_page("2.0", "January 20, 2025")

    # Section 1 - Purpose
    pdf.add_page()
    pdf.add_section("1", "Purpose and Scope")
    pdf.add_body(
        "This policy establishes the requirements for detecting, reporting, responding "
        "to, and recovering from information security incidents affecting Acme Corp "
        "systems, networks, and data assets. It applies to all employees, contractors, "
        "and third-party service providers. This policy covers the Cardholder Data "
        "Environment (CDE) and all connected systems. The objective is to minimize the "
        "impact of security incidents and ensure rapid restoration of normal operations."
    )

    # Section 2 - Incident Classification
    pdf.add_section("2", "Incident Classification and Severity")
    pdf.add_subsection("2.1", "Severity Levels")
    pdf.add_body(
        "Security incidents are classified into four severity levels: Critical (active "
        "breach of cardholder data or system compromise with data exfiltration), High "
        "(unauthorized access to CDE systems, malware outbreak, or denial of service), "
        "Medium (policy violations, suspicious activity, or failed intrusion attempts), "
        "and Low (informational events such as port scans or reconnaissance activity). "
        "The severity level determines the response timeline, escalation path, and "
        "resource allocation for incident handling."
    )

    pdf.add_subsection("2.2", "Incident Categories")
    pdf.add_body(
        "Incidents are categorized as follows: malware infections (viruses, ransomware, "
        "trojans, worms, spyware), unauthorized access (compromised credentials, privilege "
        "escalation, insider threats), data breaches (unauthorized disclosure or theft of "
        "cardholder data or PII), denial of service (volumetric attacks, application-layer "
        "attacks), social engineering (phishing, pretexting, baiting), and physical security "
        "breaches (unauthorized facility access, device theft or tampering)."
    )

    # Section 3 - Incident Response Team
    pdf.add_section("3", "Incident Response Team")
    pdf.add_body(
        "The Incident Response Team (IRT) consists of the Chief Information Security "
        "Officer (team lead), Security Operations Center analysts, IT infrastructure "
        "engineers, legal counsel, communications and public relations, and human "
        "resources. The IRT must be available on a 24/7/365 basis. On-call rotation "
        "schedules must be maintained and tested monthly. All IRT members must complete "
        "incident response training annually and participate in tabletop exercises at "
        "least twice per year."
    )

    # Section 4 - Detection and Reporting
    pdf.add_section("4", "Detection and Reporting")
    pdf.add_body(
        "Security events must be detected through continuous monitoring using intrusion "
        "detection systems (IDS), security information and event management (SIEM) "
        "platforms, endpoint detection and response (EDR) agents, and anti-malware "
        "solutions. All employees are required to report suspected security incidents "
        "to the Security Operations Center within one hour of discovery via the "
        "designated reporting channels (security hotline, email, or ticketing system). "
        "Automated alerts from monitoring systems must be triaged within 15 minutes "
        "of generation."
    )

    # Section 5 - Response Procedures
    pdf.add_section("5", "Response and Containment")
    pdf.add_subsection("5.1", "Containment")
    pdf.add_body(
        "Upon confirmation of a security incident, immediate containment measures must "
        "be implemented to prevent further damage. Short-term containment includes "
        "isolating affected systems from the network, blocking malicious IP addresses "
        "and domains, disabling compromised user accounts, and preserving volatile "
        "evidence (memory dumps, running processes, network connections). Long-term "
        "containment includes rebuilding affected systems from known-good backups and "
        "applying emergency patches."
    )

    pdf.add_subsection("5.2", "Eradication and Recovery")
    pdf.add_body(
        "After containment, the root cause must be identified and eliminated. This "
        "includes removing malware, closing exploited vulnerabilities, resetting all "
        "compromised credentials, and verifying system integrity. Recovery procedures "
        "must include restoring systems from verified backups, validating that security "
        "controls are functioning correctly, conducting vulnerability scans to confirm "
        "remediation, and monitoring restored systems for signs of re-compromise for a "
        "minimum of 30 days."
    )

    # Section 6 - Post-Incident Review
    pdf.add_section("6", "Post-Incident Review and Lessons Learned")
    pdf.add_body(
        "A post-incident review meeting must be conducted within five business days of "
        "incident closure. The review must document the incident timeline, root cause "
        "analysis, effectiveness of the response, lessons learned, and corrective actions "
        "to prevent recurrence. All findings must be tracked to completion. Incident "
        "records must be retained for a minimum of twelve months. The incident response "
        "plan must be updated based on lessons learned. Metrics including mean time to "
        "detect (MTTD), mean time to respond (MTTR), and incident volume trends must be "
        "reported to executive management quarterly."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_DIR / "incident_response_policy.pdf"))
    print(f"  Created: {OUTPUT_DIR / 'incident_response_policy.pdf'}")


def generate_security_awareness_policy() -> None:
    """Generate Acme Corp Security Awareness & Training Policy."""
    pdf = PolicyPDF("Security Awareness & Training Policy")
    pdf.alias_nb_pages()
    pdf.add_title_page("1.5", "February 15, 2025")

    # Section 1 - Purpose
    pdf.add_page()
    pdf.add_section("1", "Purpose and Scope")
    pdf.add_body(
        "This policy establishes the requirements for security awareness and training "
        "programs at Acme Corp. It applies to all employees, contractors, temporary "
        "workers, and third-party personnel who access Acme Corp systems or handle "
        "cardholder data. The objective is to ensure all personnel understand their "
        "security responsibilities, can recognize threats, and follow established "
        "security procedures to protect the Cardholder Data Environment."
    )

    # Section 2 - New Hire Training
    pdf.add_section("2", "New Hire Security Training")
    pdf.add_body(
        "All new employees and contractors must complete mandatory security awareness "
        "training within 30 calendar days of their start date and before being granted "
        "access to any system containing cardholder data. The training must cover: the "
        "organization's information security policy, acceptable use policies for "
        "end-user technologies, data classification and handling procedures, password "
        "and authentication requirements, physical security procedures, incident "
        "reporting procedures, social engineering awareness, and consequences of "
        "non-compliance. Completion must be documented and acknowledged in writing."
    )

    # Section 3 - Annual Refresher
    pdf.add_section("3", "Annual Security Awareness Refresher")
    pdf.add_body(
        "All personnel must complete annual security awareness refresher training. The "
        "refresher must be completed within 12 months of the previous training session. "
        "Annual training must include updates on current threat landscape, changes to "
        "security policies and procedures, review of recent security incidents and "
        "lessons learned, phishing identification and response procedures, secure "
        "remote access practices, social engineering attack techniques, and proper "
        "handling of cardholder data and sensitive information. Training completion "
        "rates must be tracked and reported to management quarterly."
    )

    # Section 4 - Role-Based Training
    pdf.add_section("4", "Role-Based Security Training")
    pdf.add_subsection("4.1", "Developer Security Training")
    pdf.add_body(
        "Software development personnel working on bespoke and custom software must "
        "receive specialized training at least once every 12 months covering: secure "
        "coding practices and common vulnerability prevention (OWASP Top 10), secure "
        "software design principles, input validation and output encoding techniques, "
        "security testing methodologies and tools, code review for security "
        "vulnerabilities, and secure configuration of development environments. "
        "Developers must demonstrate competency through assessments."
    )

    pdf.add_subsection("4.2", "Administrator Security Training")
    pdf.add_body(
        "System administrators and privileged users must receive specialized training "
        "covering: secure system configuration and hardening, patch management "
        "procedures, log review and monitoring techniques, incident detection and "
        "initial response, key management and cryptographic controls, network "
        "segmentation and access control configuration, and change management "
        "procedures. Training must be updated to reflect new technologies deployed."
    )

    # Section 5 - Phishing Simulation
    pdf.add_section("5", "Phishing Simulation Program")
    pdf.add_body(
        "Phishing simulation exercises must be conducted at least quarterly to assess "
        "employee susceptibility to social engineering attacks. Simulations must cover "
        "various attack vectors including email phishing, spear phishing, SMS phishing "
        "(smishing), and voice phishing (vishing). Employees who fail simulations must "
        "complete additional targeted training within 14 calendar days. Results of "
        "phishing simulations including click rates, report rates, and trend data "
        "must be reported to the CISO monthly. The program must be continuously "
        "improved based on emerging threats."
    )

    # Section 6 - Compliance and Documentation
    pdf.add_section("6", "Training Records and Compliance")
    pdf.add_body(
        "All training completion records must be maintained for a minimum of three "
        "years. Records must include the name of the trainee, date of completion, "
        "training content covered, acknowledgment of understanding, and assessment "
        "results where applicable. Non-compliance with training requirements may "
        "result in suspension of system access until training is completed. The "
        "overall training program effectiveness must be assessed annually and "
        "improvements implemented based on the assessment findings."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_DIR / "security_awareness_policy.pdf"))
    print(f"  Created: {OUTPUT_DIR / 'security_awareness_policy.pdf'}")


def generate_change_management_policy() -> None:
    """Generate Acme Corp Change Management & SDLC Policy."""
    pdf = PolicyPDF("Change Management & SDLC Policy")
    pdf.alias_nb_pages()
    pdf.add_title_page("3.2", "March 10, 2025")

    # Section 1 - Purpose
    pdf.add_page()
    pdf.add_section("1", "Purpose and Scope")
    pdf.add_body(
        "This policy establishes the requirements for managing changes to all system "
        "components, software, and configurations within Acme Corp environments. It "
        "covers the change control process for infrastructure, network, application, "
        "and security system modifications, as well as the secure software development "
        "lifecycle (SDLC) for bespoke and custom software. This policy applies to all "
        "production, staging, and development environments, with particular emphasis on "
        "changes affecting the Cardholder Data Environment (CDE)."
    )

    # Section 2 - Change Control
    pdf.add_section("2", "Change Control Process")
    pdf.add_subsection("2.1", "Change Request and Approval")
    pdf.add_body(
        "All changes to system components, network configurations, and software must "
        "follow the formal change control process. Change requests must document: a "
        "description of the change and its business justification, impact analysis "
        "including security implications, rollback procedures in case of failure, "
        "testing plan and expected outcomes, approval from the Change Advisory Board "
        "(CAB), and scheduled implementation window. Emergency changes must receive "
        "verbal approval from the CISO or designated authority and must be formally "
        "documented and reviewed within 72 hours of implementation."
    )

    pdf.add_subsection("2.2", "Configuration Standards")
    pdf.add_body(
        "Configuration standards must be developed, implemented, and maintained for "
        "all system components. Standards must cover all system components including "
        "servers, network devices, databases, and applications. Standards must address "
        "all known security vulnerabilities. Standards must be consistent with "
        "industry-accepted system hardening benchmarks such as CIS Benchmarks, NIST, "
        "or vendor-specific hardening guides. Standards must be updated as new "
        "vulnerability issues are identified. Vendor default accounts must be managed: "
        "default passwords must be changed, and unused default accounts must be removed "
        "or disabled before deployment to production."
    )

    # Section 3 - Environment Separation
    pdf.add_section("3", "Environment Separation")
    pdf.add_body(
        "Development, testing, and production environments must be separated. "
        "Developers must not have direct access to production systems or production "
        "cardholder data. Test data must not contain live cardholder data unless the "
        "test environment maintains the same security controls as production. "
        "Production credentials must not be used in development or test environments. "
        "Primary functions requiring different security levels must not coexist on "
        "the same system component unless properly isolated. Code promotion from "
        "development to testing to production must follow the approved deployment "
        "pipeline with appropriate approvals at each stage."
    )

    # Section 4 - SDLC
    pdf.add_section("4", "Secure Software Development Lifecycle")
    pdf.add_subsection("4.1", "Secure Development Practices")
    pdf.add_body(
        "All bespoke and custom software must be developed securely based on "
        "industry standards and best practices. Security must be incorporated into "
        "each stage of the software development lifecycle including requirements, "
        "design, implementation, testing, deployment, and maintenance. Developers "
        "must follow secure coding guidelines that address common vulnerabilities "
        "including injection flaws, cross-site scripting, broken authentication, "
        "insecure direct object references, security misconfiguration, sensitive "
        "data exposure, and cross-site request forgery."
    )

    pdf.add_subsection("4.2", "Code Review and Testing")
    pdf.add_body(
        "All bespoke and custom software must undergo security code review prior to "
        "release to production. Code reviews must ensure code is developed according "
        "to secure coding guidelines, look for both existing and emerging software "
        "vulnerabilities, and verify that appropriate corrections are implemented "
        "prior to release. Static application security testing (SAST) must be "
        "performed on all code changes. Dynamic application security testing (DAST) "
        "must be performed on web applications before deployment. Identified "
        "vulnerabilities must be remediated and re-tested before release."
    )

    # Section 5 - Anti-Malware
    pdf.add_section("5", "Anti-Malware and System Protection")
    pdf.add_body(
        "Anti-malware solutions must be deployed on all system components that are "
        "commonly affected by malicious software, including workstations, servers, "
        "and mobile devices. The deployed anti-malware solution must detect all known "
        "types of malware and must remove, block, or contain all known types of "
        "malware. Anti-malware definitions and signatures must be kept current via "
        "automatic updates. Any system components that are determined to not be at "
        "risk for malware must be documented and periodically re-evaluated to confirm "
        "that anti-malware protection is still not required. Periodic malware scans "
        "must be performed on all systems in the CDE."
    )

    # Section 6 - Wireless Configuration
    pdf.add_section("6", "Wireless and Default Configuration Management")
    pdf.add_body(
        "For wireless environments connected to the CDE or transmitting account data, "
        "all wireless vendor defaults must be changed at installation, including "
        "default wireless encryption keys, passwords on wireless access points, and "
        "SNMP community strings. Authorized and unauthorized wireless access points "
        "must be identified and managed. Testing for the presence of wireless access "
        "points must be performed at least once every three months. Internal "
        "vulnerability scans must be performed at least once every three months, and "
        "after any significant change. High-risk and critical vulnerabilities must be "
        "remediated in accordance with the entity's vulnerability risk rankings."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_DIR / "change_management_policy.pdf"))
    print(f"  Created: {OUTPUT_DIR / 'change_management_policy.pdf'}")


def generate_physical_security_policy() -> None:
    """Generate Acme Corp Physical Security Policy."""
    pdf = PolicyPDF("Physical Security Policy")
    pdf.alias_nb_pages()
    pdf.add_title_page("2.3", "April 1, 2025")

    # Section 1 - Purpose
    pdf.add_page()
    pdf.add_section("1", "Purpose and Scope")
    pdf.add_body(
        "This policy establishes the requirements for physical security controls "
        "to protect Acme Corp facilities, systems, and media that store, process, or "
        "transmit cardholder data. It applies to all data centers, server rooms, offices, "
        "and any location housing system components within the Cardholder Data Environment "
        "(CDE). This policy covers facility access controls, visitor management, media "
        "handling and destruction, and point-of-interaction (POI) device security."
    )

    # Section 2 - Facility Access
    pdf.add_section("2", "Facility Access Controls")
    pdf.add_subsection("2.1", "Entry Controls")
    pdf.add_body(
        "Appropriate facility entry controls must be in place to restrict physical access "
        "to systems in the CDE. Entry to sensitive areas including data centers, server "
        "rooms, and network closets must require badge access with multi-factor "
        "authentication (badge plus PIN or biometric). All entry points must be monitored "
        "by security cameras operating 24/7/365. Camera recordings must be retained for "
        "a minimum of three months. Security personnel must be stationed at primary "
        "building entry points during business hours."
    )

    pdf.add_subsection("2.2", "Individual Access Monitoring")
    pdf.add_body(
        "Individual physical access to sensitive areas within the CDE must be monitored "
        "with either video cameras or physical access control mechanisms (or both) that "
        "can record and identify individual access. Data from these monitoring mechanisms "
        "must be reviewed regularly and correlated with other entries. Physical access "
        "data must be stored for at least three months. Physical or logical controls must "
        "be implemented to restrict the use of publicly accessible network jacks within "
        "the facility to prevent unauthorized network connections."
    )

    # Section 3 - Personnel Access
    pdf.add_section("3", "Personnel Access Management")
    pdf.add_body(
        "Procedures must be implemented for authorizing and managing physical access of "
        "personnel to the CDE. Access to sensitive areas must be authorized based on "
        "individual job function and documented by an authorized approver. Access devices "
        "such as badges, keys, and access cards must be inventoried and controlled. "
        "Access lists must be reviewed at least quarterly to remove personnel who no "
        "longer require access. Upon termination of employment, all physical access "
        "devices must be collected and access must be revoked immediately. Badge readers "
        "and access control systems must be configured to log all entry and exit events."
    )

    # Section 4 - Visitor Management
    pdf.add_section("4", "Visitor Management")
    pdf.add_body(
        "All visitors must be authorized before entering areas where cardholder data is "
        "processed or stored. Visitors must be identified by a government-issued photo ID "
        "and issued a temporary visitor badge that is visually distinguishable from "
        "employee badges. Visitors must be escorted at all times within sensitive areas "
        "by authorized personnel. A visitor log must be maintained that records the "
        "visitor's name, organization, date and time of entry and exit, and the name of "
        "the escort. Visitor logs must be retained for a minimum of three months. Visitor "
        "badges must be surrendered upon departure."
    )

    # Section 5 - Media Handling
    pdf.add_section("5", "Media Protection and Destruction")
    pdf.add_subsection("5.1", "Media Storage")
    pdf.add_body(
        "All media containing cardholder data must be physically secured in locked "
        "storage with access limited to authorized personnel only. Media includes hard "
        "drives, backup tapes, removable storage devices, paper receipts, and printouts "
        "containing cardholder data. Media must be classified according to the sensitivity "
        "of the data it contains. An inventory of all sensitive media must be maintained "
        "and verified at least annually. Media transported outside the facility must be "
        "tracked using a secure courier service with chain-of-custody documentation."
    )

    pdf.add_subsection("5.2", "Media Destruction")
    pdf.add_body(
        "Media containing cardholder data must be destroyed when no longer needed for "
        "business or legal reasons. Destruction methods must render cardholder data "
        "unrecoverable: hard-copy materials must be cross-cut shredded, incinerated, "
        "or pulped. Electronic media must be degaussed, purged, or physically destroyed "
        "(shredding, disintegration). A certificate of destruction must be obtained and "
        "retained for all media destruction activities. Third-party destruction services "
        "must be vetted and contracted with documented chain-of-custody procedures."
    )

    # Section 6 - POI Device Security
    pdf.add_section("6", "Point-of-Interaction Device Security")
    pdf.add_body(
        "Point-of-interaction (POI) devices such as payment terminals and PIN entry "
        "devices must be protected from tampering and unauthorized substitution. An "
        "up-to-date list of POI devices must be maintained including make, model, serial "
        "number, and location of each device. Device surfaces must be periodically "
        "inspected to detect tampering (for example, addition of card skimmers) or "
        "unauthorized substitution. Personnel who interact with POI devices must be "
        "trained to recognize evidence of tampering and to report suspicious activity "
        "immediately. POI device inspections must be performed at least quarterly."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_DIR / "physical_security_policy.pdf"))
    print(f"  Created: {OUTPUT_DIR / 'physical_security_policy.pdf'}")


if __name__ == "__main__":
    print("Generating demo policy PDFs...")
    generate_access_control_policy()
    generate_data_protection_policy()
    generate_network_security_policy()
    generate_incident_response_policy()
    generate_security_awareness_policy()
    generate_change_management_policy()
    generate_physical_security_policy()
    print("Done!")
