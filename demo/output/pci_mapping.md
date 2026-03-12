# Compliance Mapping Results

## 1.1.1 — PCI DSS 1.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.90)

**Rationale:** Inferred from sibling controls: 1 of 4 evaluated controls in Requirement 1 are fully compliant. Gaps remain in 1.2.4, 1.2.1, 1.2.2.

---

## 1.1.2 — PCI DSS 1.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.90)

**Rationale:** Inferred from sibling controls: 1 of 4 evaluated controls in Requirement 1 are fully compliant. Gaps remain in 1.2.4, 1.2.1, 1.2.2.

---

## 1.2.1 — PCI DSS 1.2.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** Combined evidence from 3 chunks covers 7/8 sub-requirements. Missing: Configuration standards for all network security control (NSC) rulesets must be implemented.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 2 | 2.1  Firewall Configuration Standards | Configuration standards for all network security control (NSC) rulesets must be defined, documented, and maintained. |
| 2 | change_management_policy.pdf | 2 | 2.2  Configuration Standards | Configuration standards must be developed, implemented, and maintained for all system components. Standards must cove... |
| 3 | network_security_policy.pdf | 2 | 2.1  Firewall Configuration Standards | Configuration files for NSCs must be secured from unauthorized access and kept consistent with active network configu... |

---

## 1.2.2 — PCI DSS 1.2.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk covers approval but does not specify management according to a specific requirement.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 3 | 6  Network Change Management | All changes to network connections and to configurations of NSCs must be approved and managed in accordance with the ... |
| 2 | change_management_policy.pdf | 2 | 2.1  Change Request and Approval | All changes to system components, network configurations, and software must follow the formal change control process.... |

---

## 1.2.3 — PCI DSS 1.2.3

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.80)

**Rationale:** Combined evidence from 2 chunks covers all 3 sub-requirements: An accurate network diagram must be maintained that shows all connections between the CDE and other networks, including wireless networks.; The network diagram must be updated whenever changes occur.; NSCs must be installed between all wireless networks and the CDE.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 2 | 3  Network Segmentation and CDE Isolation | An accurate network diagram must be maintained that shows all connections between the CDE and other networks, includi... |
| 2 | network_security_policy.pdf | 2 | 4  Wireless Network Security | NSCs must be installed between all wireless networks and the CDE, regardless of whether the wireless network is part ... |

---

## 1.2.4 — PCI DSS 1.2.4

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a policy that mandates the creation and maintenance of accurate data-flow diagrams for all account data flows across systems and networks as required by PCI DSS 1.2.4. A new policy should be established to ensure such diagrams are maintained and updated as needed.

---

## 2.1.1 — PCI DSS 2.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.88)

**Rationale:** Inferred from sibling controls: 2 of 4 evaluated controls in Requirement 2 are fully compliant. Gaps remain in 2.2.1, 2.2.3.

---

## 2.1.2 — PCI DSS 2.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.88)

**Rationale:** Inferred from sibling controls: 2 of 4 evaluated controls in Requirement 2 are fully compliant. Gaps remain in 2.2.1, 2.2.3.

---

## 2.2.1 — PCI DSS 2.2.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.50)

**Rationale:** Combined evidence from 3 chunks covers all 4 sub-requirements: Configuration standards are developed, implemented, and maintained to cover all system components.; Standards address all known security vulnerabilities.; Standards are consistent with industry-accepted system hardening standards or vendor hardening recommendations.; Standards are updated as new vulnerability issues are identified.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 2 | 2.2  Configuration Standards | Configuration standards must be developed, implemented, and maintained for all system components. Standards must cove... |
| 2 | network_security_policy.pdf | 2 | 2.1  Firewall Configuration Standards | Configuration standards for all network security control (NSC) rulesets must be defined, documented, and maintained. |
| 3 | network_security_policy.pdf | 2 | 2.2  Traffic Control Rules | All allowed services, protocols, and ports must be identified, approved, and have a defined business justification do... |

---

## 2.2.2 — PCI DSS 2.2.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** Combined evidence from 4 chunks covers all 2 sub-requirements: If the vendor default account(s) will be used, the default password is changed per Requirement 8.3.6.; If the vendor default account(s) will not be used, the account is removed or disabled.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 2 | 2.2  Configuration Standards | Vendor default accounts must be managed: default passwords must be changed, and unused default accounts must be remov... |
| 2 | network_security_policy.pdf | 2 | 2.1  Firewall Configuration Standards | Default vendor-supplied credentials on all network devices must be changed immediately upon deployment. |
| 3 | change_management_policy.pdf | 3 | 6  Wireless and Default Configuration Management | For wireless environments connected to the CDE or transmitting account data, all wireless vendor defaults must be cha... |
| 4 | access_control_policy.pdf | 2 | 2.3  Password Requirements | All system and application passwords must meet the following minimum requirements: minimum length of 12 characters, i... |

---

## 2.2.3 — PCI DSS 2.2.3

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk addresses part of the control by stating that primary functions requiring different security levels must not coexist unless properly isolated, but it does not address securing all functions to the level required by the function with the highest security need.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 2 | 3  Environment Separation | Primary functions requiring different security levels must not coexist on the same system component unless properly i... |

---

## 2.3.1 — PCI DSS 2.3.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** Combined evidence from 2 chunks covers all 4 sub-requirements: For wireless environments connected to the CDE or transmitting account data, all wireless vendor defaults must be changed at installation.; Default wireless encryption keys must be changed at installation.; Passwords on wireless access points must be changed at installation.; SNMP community strings must be changed at installation.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 3 | 6  Wireless and Default Configuration Management | For wireless environments connected to the CDE or transmitting account data, all wireless vendor defaults must be cha... |
| 2 | network_security_policy.pdf | 2 | 4  Wireless Network Security | NSCs must be installed between all wireless networks and the CDE, regardless of whether the wireless network is part ... |

---

## 3.1.1 — PCI DSS 3.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** Inferred from sibling controls: 4 of 5 evaluated controls in Requirement 3 are fully compliant. Gaps remain in 3.2.1.

---

## 3.1.2 — PCI DSS 3.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** Inferred from sibling controls: 4 of 5 evaluated controls in Requirement 3 are fully compliant. Gaps remain in 3.2.1.

---

## 3.2.1 — PCI DSS 3.2.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk provides evidence for defining specific retention periods and secure deletion of cardholder data but does not address coverage for all locations of stored account data.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Account data storage must be kept to a minimum. Data retention policies must define the specific retention period for... |
| 2 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 3.3.1 — PCI DSS 3.3.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The chunk directly addresses the requirement to not store SAD after authorization.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 3.3.1.1 — PCI DSS 3.3.1.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy explicitly states that sensitive authentication data such as full track data cannot be stored post-authorization, which directly aligns with the security control.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 3.3.1.2 — PCI DSS 3.3.1.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The chunk explicitly states that sensitive authentication data such as CVVs must not be stored post-authorization, which directly aligns with the security control.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 3.3.1.3 — PCI DSS 3.3.1.3

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy explicitly states that sensitive authentication data, which includes PINs, must not be stored after authorization. This directly aligns with the security control requirement.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 4.1.1 — PCI DSS 4.1.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** Inferred from sibling controls: all 3 evaluated controls in Requirement 4 are non-compliant (4.2.1, 4.2.1.1, 4.2.2). This governance requirement cannot be met.

---

## 4.1.2 — PCI DSS 4.1.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** Inferred from sibling controls: all 3 evaluated controls in Requirement 4 are non-compliant (4.2.1, 4.2.1.1, 4.2.2). This governance requirement cannot be met.

---

## 4.2.1 — PCI DSS 4.2.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks specific policy documentation that directly addresses PCI DSS requirement 4.2.1, which mandates strong cryptography and security protocols for safeguarding PAN during transmission over open, public networks. To address this control, the organization needs to establish a detailed policy that outlines the acceptance criteria for trusted keys and certificates, procedures for validating certificate validity and non-revocation, restrictions on using insecure protocol versions or algorithms, and guidelines for appropriate encryption strength based on the chosen methodology.

---

## 4.2.1.1 — PCI DSS 4.2.1.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a policy that mandates maintaining an inventory of trusted keys and certificates as required by PCI DSS 4.2.1.1. This control is non-compliant because without such a policy, there is no documented process or procedure to ensure the entity regularly updates and maintains this critical information.

---

## 4.2.2 — PCI DSS 4.2.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a policy that specifically addresses the secure transmission of PAN (Primary Account Number) using end-user messaging technologies as required by PCI DSS 4.2.2. A new or updated policy is needed to ensure that appropriate strong cryptography measures are implemented and enforced for such transmissions.

---

## 5.1.1 — PCI DSS 5.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** Inferred from sibling controls: 3 of 4 evaluated controls in Requirement 5 are fully compliant. Gaps remain in 5.2.3.

---

## 5.1.2 — PCI DSS 5.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** Inferred from sibling controls: 3 of 4 evaluated controls in Requirement 5 are fully compliant. Gaps remain in 5.2.3.

---

## 5.2.1 — PCI DSS 5.2.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The chunk provides evidence for deploying anti-malware solutions and keeping them updated. However, it does not specify how system components are evaluated periodically to determine if they are at risk from malware.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 3 | 5  Anti-Malware and System Protection | Anti-malware solutions must be deployed on all system components that are commonly affected by malicious software, in... |

---

## 5.2.2 — PCI DSS 5.2.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy excerpt explicitly states that the anti-malware solution must detect and handle (remove, block, or contain) all known types of malware.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 3 | 5  Anti-Malware and System Protection | Anti-malware solutions must be deployed on all system components that are commonly affected by malicious software, in... |

---

## 5.2.3 — PCI DSS 5.2.3

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk mentions the periodic evaluation of systems not at risk for malware but does not explicitly state a requirement for documenting such components. It covers identification and evaluation of evolving threats, as well as confirmation of continued lack of need for anti-malware protection.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 3 | 5  Anti-Malware and System Protection | Anti-malware solutions must be deployed on all system components that are commonly affected by malicious software, in... |

---

## 5.3.1 — PCI DSS 5.3.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The chunk provides clear evidence that anti-malware solutions are deployed on all relevant system components, detect and handle malware effectively, and maintain up-to-date definitions through automatic updates.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 3 | 5  Anti-Malware and System Protection | Anti-malware solutions must be deployed on all system components that are commonly affected by malicious software, in... |

---

## 6.1.1 — PCI DSS 6.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.90)

**Rationale:** Inferred from sibling controls: 2 of 3 evaluated controls in Requirement 6 are fully compliant. Gaps remain in 6.2.1.

---

## 6.1.2 — PCI DSS 6.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.90)

**Rationale:** Inferred from sibling controls: 2 of 3 evaluated controls in Requirement 6 are fully compliant. Gaps remain in 6.2.1.

---

## 6.2.1 — PCI DSS 6.2.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk covers secure development practices based on industry standards but does not explicitly mention PCI DSS compliance or specific security controls like authentication and logging.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 2 | 4.1  Secure Development Practices | All bespoke and custom software must be developed securely based on industry standards and best practices. Security m... |
| 2 | security_awareness_policy.pdf | 2 | 4.1  Developer Security Training | Software development personnel working on bespoke and custom software must receive specialized training at least once... |
| 3 | change_management_policy.pdf | 3 | 4.2  Code Review and Testing | All bespoke and custom software must undergo security code review prior to release to production. Code reviews must e... |

---

## 6.2.2 — PCI DSS 6.2.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.85)

**Rationale:** Combined evidence from 3 chunks covers all 3 sub-requirements: Software development personnel working on bespoke and custom software are trained at least once every 12 months.; Training includes secure software design and secure coding techniques.; If security testing tools are used, training must include how to use the tools for detecting vulnerabilities in software.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | security_awareness_policy.pdf | 2 | 4.1  Developer Security Training | Software development personnel working on bespoke and custom software must receive specialized training at least once... |
| 2 | change_management_policy.pdf | 2 | 4.1  Secure Development Practices | All bespoke and custom software must be developed securely based on industry standards and best practices. Security m... |
| 3 | change_management_policy.pdf | 3 | 4.2  Code Review and Testing | All bespoke and custom software must undergo security code review prior to release to production. Code reviews must e... |

---

## 6.2.3 — PCI DSS 6.2.3

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.85)

**Rationale:** Combined evidence from 3 chunks covers all 3 sub-requirements: Code reviews ensure code is developed according to secure coding guidelines.; Code reviews look for both existing and emerging software vulnerabilities.; Appropriate corrections are implemented prior to release.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 3 | 4.2  Code Review and Testing | All bespoke and custom software must undergo security code review prior to release to production. Code reviews must e... |
| 2 | change_management_policy.pdf | 2 | 4.1  Secure Development Practices | All bespoke and custom software must be developed securely based on industry standards and best practices. Security m... |
| 3 | security_awareness_policy.pdf | 2 | 4.1  Developer Security Training | Software development personnel working on bespoke and custom software must receive specialized training at least once... |

---

## 7.1.1 — PCI DSS 7.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.87)

**Rationale:** Inferred from sibling controls: 1 of 3 evaluated controls in Requirement 7 are fully compliant. Gaps remain in 7.2.2, 7.2.3.

---

## 7.1.2 — PCI DSS 7.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.87)

**Rationale:** Inferred from sibling controls: 1 of 3 evaluated controls in Requirement 7 are fully compliant. Gaps remain in 7.2.2, 7.2.3.

---

## 7.2.1 — PCI DSS 7.2.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy excerpt clearly outlines that access rights are assigned based on job classification and functions, adhering to the principle of least privilege. This directly addresses all sub-requirements of PCI DSS 7.2.1.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 3.1  Role-Based Access Control (RBAC) | Access rights must be assigned based on job classification and function, following the principle of least privilege. ... |

---

## 7.2.2 — PCI DSS 7.2.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a policy that explicitly outlines how access is assigned to users based on job classification and function, as well as the principle of least privileges necessary for performing job responsibilities. This missing documentation makes it difficult to ensure that all user access aligns with PCI DSS 7.2.2 requirements.

---

## 7.2.3 — PCI DSS 7.2.3

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a policy that explicitly outlines the process for approving required privileges as mandated by PCI DSS 7.2.3. This results in a gap where there is no documented procedure to ensure that all privileges are reviewed and approved by authorized personnel.

---

## 8.1.1 — PCI DSS 8.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.96)

**Rationale:** Inferred from sibling controls: 2 of 5 evaluated controls in Requirement 8 are fully compliant. Gaps remain in 8.2.4, 8.2.2, 8.2.5.

---

## 8.1.2 — PCI DSS 8.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.96)

**Rationale:** Inferred from sibling controls: 2 of 5 evaluated controls in Requirement 8 are fully compliant. Gaps remain in 8.2.4, 8.2.2, 8.2.5.

---

## 8.2.1 — PCI DSS 8.2.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The chunk directly addresses the requirement by mandating that all users receive a unique identifier prior to gaining access to system components and cardholder data.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 2.1  Unique User Identification | All users must be assigned a unique user ID before they are allowed access to any system component or cardholder data... |

---

## 8.2.2 — PCI DSS 8.2.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk addresses the requirement for unique user identification but does not cover other aspects of managing group IDs and shared authentication credentials as specified in PCI DSS 8.2.2.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 2.1  Unique User Identification | All users must be assigned a unique user ID before they are allowed access to any system component or cardholder data... |
| 2 | access_control_policy.pdf | 3 | 6  Audit Logging and Monitoring | All access to system components and cardholder data must be logged. Audit logs must capture: user identification, typ... |

---

## 8.2.3 — PCI DSS 8.2.3

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy explicitly states that service provider personnel with remote access to customer premises must use unique MFA credentials for each customer, which directly aligns with the security control requirement.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 2.2  Multi-Factor Authentication (MFA) | Multi-factor authentication is required for all remote access to the corporate network and for all access to the Card... |

---

## 8.2.4 — PCI DSS 8.2.4

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks policy documentation that outlines the procedures for managing user IDs, authentication factors, and other identifier objects as required by PCI DSS 8.2.4. Specifically, there are no documented processes for obtaining appropriate approvals or specifying privileges associated with these actions.

---

## 8.2.5 — PCI DSS 8.2.5

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk specifies that accounts of terminated users are disabled after departure but retains them for 90 days. This partially aligns with the requirement as it does not immediately revoke access, but instead disables and retains accounts temporarily.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 3 | 5  Access Revocation and Termination | All authentication tokens, badges, keys, and company equipment must be collected and documented before the employee d... |

---

## 9.1.1 — PCI DSS 9.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** Inferred from sibling controls: 2 of 4 evaluated controls in Requirement 9 are fully compliant. Gaps remain in 9.2.1.1, 9.3.1.

---

## 9.1.2 — PCI DSS 9.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** Inferred from sibling controls: 2 of 4 evaluated controls in Requirement 9 are fully compliant. Gaps remain in 9.2.1.1, 9.3.1.

---

## 9.2.1 — PCI DSS 9.2.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The chunk provides specific details on facility entry controls, multi-factor authentication requirements for sensitive areas, and continuous monitoring with security cameras.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | physical_security_policy.pdf | 2 | 2.1  Entry Controls | Appropriate facility entry controls must be in place to restrict physical access to systems in the CDE. Entry to sens... |
| 2 | physical_security_policy.pdf | 2 | 2.2  Individual Access Monitoring | Individual physical access to sensitive areas within the CDE must be monitored with either video cameras or physical ... |

---

## 9.2.1.1 — PCI DSS 9.2.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk covers the monitoring of entry points but does not address protection against tampering or disabling of monitoring devices, review and correlation of collected data, or storage duration.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | physical_security_policy.pdf | 2 | 2.1  Entry Controls | Appropriate facility entry controls must be in place to restrict physical access to systems in the CDE. Entry to sens... |
| 2 | physical_security_policy.pdf | 2 | 2.2  Individual Access Monitoring | Individual physical access to sensitive areas within the CDE must be monitored with either video cameras or physical ... |
| 3 | physical_security_policy.pdf | 2 | 4  Visitor Management | All visitors must be authorized before entering areas where cardholder data is processed or stored. Visitors must be ... |

---

## 9.3.1 — PCI DSS 9.3.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk mentions authorizing and managing physical access based on job function but does not specify how changes in access requirements are managed.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | physical_security_policy.pdf | 2 | 3  Personnel Access Management | Procedures must be implemented for authorizing and managing physical access of personnel to the CDE. Access to sensit... |
| 2 | physical_security_policy.pdf | 2 | 2.1  Entry Controls | Appropriate facility entry controls must be in place to restrict physical access to systems in the CDE. Entry to sens... |
| 3 | physical_security_policy.pdf | 2 | 2.2  Individual Access Monitoring | Individual physical access to sensitive areas within the CDE must be monitored with either video cameras or physical ... |
| 4 | physical_security_policy.pdf | 2 | 4  Visitor Management | All visitors must be authorized before entering areas where cardholder data is processed or stored. Visitors must be ... |

---

## 9.4.1 — PCI DSS 9.4.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The chunk directly addresses the requirement by specifying that all media containing cardholder data must be stored securely and access is restricted to authorized personnel.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | physical_security_policy.pdf | 3 | 5.1  Media Storage | All media containing cardholder data must be physically secured in locked storage with access limited to authorized p... |

---

## 10.1.1 — PCI DSS 10.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.95)

**Rationale:** Inferred from sibling controls: 3 of 4 evaluated controls in Requirement 10 are fully compliant. Gaps remain in 10.3.1.

---

## 10.1.2 — PCI DSS 10.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.95)

**Rationale:** Inferred from sibling controls: 3 of 4 evaluated controls in Requirement 10 are fully compliant. Gaps remain in 10.3.1.

---

## 10.2.1 — PCI DSS 10.2.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy excerpt explicitly states that all access to system components and cardholder data must be logged with specific details captured in the audit logs.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 3 | 6  Audit Logging and Monitoring | All access to system components and cardholder data must be logged. Audit logs must capture: user identification, typ... |

---

## 10.2.1.1 — PCI DSS 10.2.1.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The chunk provides detailed requirements for logging all access to cardholder data and includes specific elements that must be captured in the audit logs.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 3 | 6  Audit Logging and Monitoring | All access to system components and cardholder data must be logged. Audit logs must capture: user identification, typ... |

---

## 10.2.2 — PCI DSS 10.2.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy excerpt explicitly states that audit logs must capture all the required details for each auditable event as per PCI DSS 10.2.2.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 3 | 6  Audit Logging and Monitoring | All access to system components and cardholder data must be logged. Audit logs must capture: user identification, typ... |

---

## 10.3.1 — PCI DSS 10.3.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a policy that explicitly limits read access to audit log files based on job-related need, which is required by PCI DSS 10.3.1.

---

## 11.1.1 — PCI DSS 11.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.96)

**Rationale:** Inferred from sibling controls: 0 of 4 evaluated controls in Requirement 11 are fully compliant. Gaps remain in 11.2.1, 11.3.1, 11.3.1.1, 11.4.1.

---

## 11.1.2 — PCI DSS 11.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.96)

**Rationale:** Inferred from sibling controls: 0 of 4 evaluated controls in Requirement 11 are fully compliant. Gaps remain in 11.2.1, 11.3.1, 11.3.1.1, 11.4.1.

---

## 11.2.1 — PCI DSS 11.2.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk mentions testing for the presence of wireless access points and performing internal vulnerability scans at least once every three months. However, it does not specify detection and identification of all authorized and unauthorized wireless access points or notification through automated monitoring alerts.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 3 | 6  Wireless and Default Configuration Management | Authorized and unauthorized wireless access points must be identified and managed. Testing for the presence of wirele... |
| 2 | network_security_policy.pdf | 2 | 4  Wireless Network Security | A wireless intrusion detection system (WIDS) must be deployed to detect and alert on unauthorized wireless access poi... |

---

## 11.3.1 — PCI DSS 11.3.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk specifies quarterly scans but does not address remediation of high-risk and critical vulnerabilities.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 3 | 5  Vulnerability Management | Internal and external network vulnerability scans must be performed at least quarterly and after any significant infr... |
| 2 | change_management_policy.pdf | 3 | 6  Wireless and Default Configuration Management | Authorized and unauthorized wireless access points must be identified and managed. Testing for the presence of wirele... |
| 3 | network_security_policy.pdf | 3 | 5  Vulnerability Management | High-risk vulnerabilities (CVSS score 7.0 or above) identified during scanning must be remediated within 30 calendar ... |

---

## 11.3.1.1 — PCI DSS 11.3.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.85)

**Rationale:** The chunk addresses the management of vulnerabilities based on risk analysis but does not explicitly mention conducting rescans as needed. The evidence provided focuses on maintaining configuration standards and addressing known security vulnerabilities, which aligns with part of the control requirement.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | change_management_policy.pdf | 2 | 2.2  Configuration Standards | Configuration standards must be developed, implemented, and maintained for all system components. Standards must cove... |

---

## 11.4.1 — PCI DSS 11.4.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The chunk specifies annual penetration testing but does not cover other aspects such as methodology definition, internal/external testing, validation of segmentation controls, application-layer testing, network-layer testing, review of past threats/vulnerabilities, risk assessment approach, and retention of results.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 3 | 5  Vulnerability Management | Penetration testing of the network perimeter and critical systems must be conducted at least annually. |
| 2 | change_management_policy.pdf | 3 | 4.2  Code Review and Testing | Static application security testing (SAST) must be performed on all code changes. Dynamic application security testin... |

---

## 12.1.1 — PCI DSS 12.1.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks policy documentation that explicitly outlines an overall information security policy established, published, maintained, and disseminated to all relevant personnel, vendors, and business partners as per PCI DSS 12.1.1 requirements.

---

## 12.1.2 — PCI DSS 12.1.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The organization lacks policy documentation that outlines a schedule for reviewing and updating their information security policy in accordance with PCI DSS 12.1.2 requirements. To address this, the organization should establish and maintain a formal process detailing how and when the information security policy will be reviewed and updated.

---

## 12.1.3 — PCI DSS 12.1.3

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.85)

**Rationale:** The chunk provides evidence that new hires are made aware of their responsibilities through mandatory training but does not explicitly state how roles and responsibilities are defined or acknowledged by all personnel.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | security_awareness_policy.pdf | 2 | 2  New Hire Security Training | All new employees and contractors must complete mandatory security awareness training within 30 calendar days of thei... |

---

## 12.1.4 — PCI DSS 12.1.4

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a formal policy document assigning responsibility for information security to either a Chief Information Security Officer (CISO) or another executive management member knowledgeable in information security. This is non-compliant with PCI DSS requirement 12.1.4, which mandates such an assignment.

---

## 12.2.1 — PCI DSS 12.2.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a documented policy that explicitly outlines acceptable use for end-user technologies as required by PCI DSS 12.2.1. This includes the need for explicit approval from authorized parties, defining acceptable uses of technology, and listing approved products (hardware and software). Such a policy is essential to ensure that employees are using appropriate technologies in ways that comply with security standards.

---

