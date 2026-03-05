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


if __name__ == "__main__":
    print("Generating demo policy PDFs...")
    generate_access_control_policy()
    generate_data_protection_policy()
    generate_network_security_policy()
    print("Done!")
