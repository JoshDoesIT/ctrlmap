# Compliance Mapping Results

## 1.1.1 — PCI DSS 1.1.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.90)

**Rationale:** Inferred from sibling controls: all 3 evaluated controls in Requirement 1 are compliant. Aggregated confidence from sibling assessments.

---

## 1.1.2 — PCI DSS 1.1.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.90)

**Rationale:** Inferred from sibling controls: all 4 evaluated controls in Requirement 1 are compliant. Aggregated confidence from sibling assessments.

---

## 1.2.1 — PCI DSS 1.2.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text explicitly states that configuration standards for NSC rulesets must be defined, documented, and maintained, which aligns with the requirements of PCI DSS 1.2.1.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 2 | 2.1  Firewall Configuration Standards | Configuration standards for all network security control (NSC) rulesets must be defined, documented, and maintained. |

---

## 1.2.2 — PCI DSS 1.2.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.90)

**Rationale:** Inferred from sibling controls: all 5 evaluated controls in Requirement 1 are compliant. Aggregated confidence from sibling assessments.

---

## 1.2.3 — PCI DSS 1.2.3

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.80)

**Rationale:** The policy text directly addresses the requirement of maintaining an accurate network diagram that shows connections between the CDE and other networks, including wireless networks.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 2 | 3  Network Segmentation and CDE Isolation | An accurate network diagram must be maintained that shows all connections between the CDE and other networks, includi... |

---

## 1.2.4 — PCI DSS 1.2.4

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.90)

**Rationale:** The policy text matches the control requirement by mentioning that an accurate data-flow diagram must be maintained and updated whenever changes occur, which aligns with the PCI DSS requirement.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 2 | 3  Network Segmentation and CDE Isolation | An accurate data-flow diagram must be maintained that shows all account data flows across systems and networks and mu... |

---

## 3.1.1 — PCI DSS 3.1.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.90)

**Rationale:** Inferred from sibling controls: all 2 evaluated controls in Requirement 3 are compliant. Aggregated confidence from sibling assessments.

---

## 3.1.2 — PCI DSS 3.1.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.90)

**Rationale:** Inferred from sibling controls: all 3 evaluated controls in Requirement 3 are compliant. Aggregated confidence from sibling assessments.

---

## 3.2.1 — PCI DSS 3.2.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.90)

**Rationale:** Inferred from sibling controls: all 4 evaluated controls in Requirement 3 are compliant. Aggregated confidence from sibling assessments.

---

## 3.3.1 — PCI DSS 3.3.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The control requires that sensitive authentication data (SAD) not be stored after authorization, even if encrypted. This indicates a strong requirement for data minimization and destruction. The lack of policy coverage on this topic suggests that the organization may not have a clear policy for handling SAD, which can lead to non-compliance with PCI DSS 3.3.1. To address this gap, policy documentation would be needed to outline procedures for ensuring that SAD is properly authorized and destroyed after use.

---

## 3.3.1.1 — PCI DSS 3.3.1.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.80)

**Rationale:** The policy text explicitly states that SAD, including full track data, must never be stored, which aligns with the requirement to not store the full contents of any track upon completion of the authorization process.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 2 | 3.1  Encryption Standards | authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must never be |

---

## 3.3.1.2 — PCI DSS 3.3.1.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text explicitly states that card verification codes (CVV/CVC) must never be stored, which aligns with the security control requirement of not storing the card verification code upon completion of the authorization process.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 2 | 3.1  Encryption Standards | authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must never be |

---

## 3.3.1.3 — PCI DSS 3.3.1.3

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (1.00)

**Rationale:** The organization lacks a policy that explicitly prohibits storing PINs and PIN blocks during authorization, making it non-compliant with PCI DSS 3.3.1.3. A policy would be needed to address this control requirement, such as: 'All systems and applications processing payment card information will not store personal identification numbers (PINs) or PIN blocks upon completion of the authorization process.'

---

## 6.1.1 — PCI DSS 6.1.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The security control requires documentation and update of all security policies and operational procedures identified in Requirement 6, which is not reflected in any existing policy. To address this gap, a new policy or procedure would need to be created, specifically outlining the process for documenting, updating, and communicating these policies/procedures to all affected parties.

---

## 6.1.2 — PCI DSS 6.1.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The organization lacks policy documentation defining roles and responsibilities for performing activities related to PCI DSS Requirement 6, which is necessary for ensuring that personnel are aware of their duties and expectations. To address this gap, the organization would need to develop a policy outlining job descriptions, roles, and responsibilities for individuals handling sensitive cardholder data in accordance with PCI DSS 6.1.2.

---

## 6.2.1 — PCI DSS 6.2.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The organization lacks a policy governing the secure development of bespoke and custom software, specifically addressing industry standards and best practices for secure coding, as well as PCI DSS compliance requirements. A policy should be created to outline the procedures for ensuring that all software development projects incorporate security considerations from the outset, including authentication, logging, and other information security controls.

---

## 6.2.2 — PCI DSS 6.2.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** This security control requires software development personnel to receive regular training on software security, including secure design and coding techniques, as well as tool usage for detecting vulnerabilities. Since there is no matching policy documentation in the organization's library, this control is non-compliant. To address this gap, a new policy would be needed that outlines the training requirements for software development personnel, including the frequency, scope, and content of such training.

---

## 6.2.3 — PCI DSS 6.2.3

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization does not have a policy outlining the requirements for code reviews and vulnerability identification prior to software release. A policy document would be needed to address this control requirement, such as a Secure Coding Policy or a Software Development Policy that includes provisions for code review, vulnerability identification, and correction before release.

---

## 8.1.1 — PCI DSS 8.1.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.95)

**Rationale:** Inferred from sibling controls: all 2 evaluated controls in Requirement 8 are compliant. Aggregated confidence from sibling assessments.

---

## 8.1.2 — PCI DSS 8.1.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.95)

**Rationale:** Inferred from sibling controls: all 3 evaluated controls in Requirement 8 are compliant. Aggregated confidence from sibling assessments.

---

## 8.2.1 — PCI DSS 8.2.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (0.90)

**Rationale:** The policy text requires all users to be assigned a unique user ID before access to any system component or cardholder data is allowed, which aligns with the security control requirement of assigning unique IDs to users before granting access to system components or cardholder data.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 2.1  Unique User Identification | All users must be assigned a unique user ID before they are allowed access to any system component or cardholder depa... |

---

## 8.2.2 — PCI DSS 8.2.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The organization lacks policy documentation to govern the use of group, shared, or generic IDs and authentication credentials. The PCI DSS requirement emphasizes the need for management approval, business justification, and individual accountability for exceptional circumstances where these IDs are used. Absent a policy that mirrors this control's requirements, the organization may be at risk of non-compliance with PCI DSS and potentially other regulatory standards.

---

## 8.2.3 — PCI DSS 8.2.3

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization does not have a policy in place to ensure unique authentication factors are used for each customer premises when service providers with remote access use this method. This is a specific requirement only applicable to service providers, and the lack of policy coverage creates uncertainty around how this control will be enforced or monitored.

---

## 8.2.4 — PCI DSS 8.2.4

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The organization lacks a policy that outlines the procedures and approval processes for managing changes to user IDs, authentication factors, and other identifier objects, as required by PCI DSS 8.2.4. A policy documenting the roles and responsibilities for requesting and approving such changes would be necessary to ensure compliance with this control.

---

## 8.2.5 — PCI DSS 8.2.5

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text explicitly states that logical and physical access must be revoked immediately upon termination, which aligns with the requirement to revoke access for terminated users.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 2.1  Unique User Identification | Upon termination of employment, all logical and physical access must be revoked immediately. The Human Resources |

---

## 12.1.1 — PCI DSS 12.1.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The organization lacks a comprehensive information security policy that outlines its approach to securing sensitive data and ensuring the confidentiality, integrity, and availability of critical systems. The absence of such a policy hinders the establishment of clear guidelines for all relevant personnel, vendors, and business partners, making it challenging to maintain compliance with PCI DSS requirements.

---

## 12.1.2 — PCI DSS 12.1.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (1.00)

**Rationale:** The security control PCI DSS 12.1.2 requires a review and update of the information security policy at least once every 12 months, which is not covered in any existing organizational policies. To address this gap, a new policy would be needed that outlines the procedures for reviewing and updating the information security policy to ensure it remains relevant and effective in achieving business objectives and mitigating risks to the environment.

---

## 12.1.3 — PCI DSS 12.1.3

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a security policy that defines information security roles and responsibilities for all personnel. This is critical as it ensures everyone understands their duties and obligations in maintaining the confidentiality, integrity, and availability of sensitive data.

---

## 12.1.4 — PCI DSS 12.1.4

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.80)

**Rationale:** The organization lacks a policy that formally assigns responsibility for information security to a Chief Information Security Officer (CISO) or other information security knowledgeable member of executive management, as required by PCI DSS 12.1.4. To address this gap, the organization would need to develop and document a policy that clearly defines the CISO's role and responsibilities in overseeing and managing the overall information security program.

---

## 12.2.1 — PCI DSS 12.2.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** The organization lacks a policy that outlines acceptable use policies for end-user technologies, specifically regarding explicit approval by authorized parties, acceptable uses of technology, and approved products for employee use. This gap creates uncertainty around what constitutes appropriate usage, leaving the company vulnerable to potential misuse or unauthorized activities.

---

