# Compliance Mapping Results

## 1.1.1 — PCI DSS 1.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** Inferred from sibling controls: 3 of 4 evaluated controls in Requirement 1 are fully compliant. Gaps remain in 1.2.1.

---

## 1.1.2 — PCI DSS 1.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** Inferred from sibling controls: 3 of 4 evaluated controls in Requirement 1 are fully compliant. Gaps remain in 1.2.1.

---

## 1.2.1 — PCI DSS 1.2.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (1.00)

**Rationale:** The policy text covers the definition and maintenance of configuration standards but does not explicitly mention implementation. However, since 'defined' and 'maintained' are covered comprehensively, it is reasonable to infer that implementation would naturally follow from these actions.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 2 | 2.1  Firewall Configuration Standards | Configuration standards for all network security control (NSC) rulesets must be defined, documented, and maintained. |

---

## 1.2.2 — PCI DSS 1.2.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text directly addresses both sub-requirements by stating that all changes to network connections and configurations of NSCs are approved and managed according to an organizational change control process, which is equivalent to Requirement 6.5.1's defined process.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 3 | 6  Network Change Management | All changes to network connections and to configurations of NSCs must be approved and managed in accordance with the ... |

---

## 1.2.3 — PCI DSS 1.2.3

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text directly addresses the requirement by mandating the maintenance of an accurate network diagram showing all connections between the CDE and other networks, including wireless networks. There is a direct match in wording and intent.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 2 | 3  Network Segmentation and CDE Isolation | An accurate network diagram must be maintained that shows all connections between the CDE and other networks, includi... |

---

## 1.2.4 — PCI DSS 1.2.4

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** Both sub-requirements of the control are directly addressed in the policy text, with exact matching language for maintaining an accurate data-flow diagram and updating it upon environmental changes.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | network_security_policy.pdf | 2 | 3  Network Segmentation and CDE Isolation | An accurate data-flow diagram must be maintained that shows all account data flows across systems and networks and mu... |

---

## 3.1.1 — PCI DSS 3.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.95)

**Rationale:** Inferred from sibling controls: 4 of 5 evaluated controls in Requirement 3 are fully compliant. Gaps remain in 3.2.1.

---

## 3.1.2 — PCI DSS 3.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.95)

**Rationale:** Inferred from sibling controls: 4 of 5 evaluated controls in Requirement 3 are fully compliant. Gaps remain in 3.2.1.

---

## 3.2.1 — PCI DSS 3.2.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.75)

**Rationale:** The policy text provides evidence for one of the sub-requirements related to sensitive authentication data but does not address coverage for all locations of stored account data. Therefore, it is partially compliant with the control requirement.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Account data storage must be kept to a minimum. Data retention policies must define the specific retention period for... |
| 2 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 3.3.1 — PCI DSS 3.3.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text directly addresses the requirement by stating that sensitive authentication data must not be stored after authorization, regardless of encryption status. This matches exactly with the control's sub-requirement.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 3.3.1.1 — PCI DSS 3.3.1.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text explicitly states that sensitive authentication data, which includes full track data, must not be stored after authorization. This directly addresses the requirement to not store the full contents of any track upon completion of the authorization process.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 3.3.1.2 — PCI DSS 3.3.1.2

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text explicitly states that sensitive authentication data such as CVV/CVC must not be stored after authorization, which directly addresses the requirement to not store card verification codes upon completion of the authorization process.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 3.3.1.3 — PCI DSS 3.3.1.3

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text explicitly states that sensitive authentication data such as PINs must not be stored after authorization, which directly addresses the requirement to ensure that PINs are not stored upon completion of the authorization process.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | data_protection_policy.pdf | 3 | 6  Data Retention and Secure Disposal | Sensitive authentication data (SAD) including the full track data, card verification codes (CVV/CVC), and PINs must n... |

---

## 6.1.1 — PCI DSS 6.1.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** Inferred from sibling controls: all 3 evaluated controls in Requirement 6 are non-compliant (6.2.1, 6.2.2, 6.2.3). This governance requirement cannot be met.

---

## 6.1.2 — PCI DSS 6.1.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.90)

**Rationale:** Inferred from sibling controls: all 3 evaluated controls in Requirement 6 are non-compliant (6.2.1, 6.2.2, 6.2.3). This governance requirement cannot be met.

---

## 6.2.1 — PCI DSS 6.2.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The control is non-compliant because there is no corresponding policy documentation in the organization's library that addresses secure software development practices as per PCI DSS 6.2.1 requirements. To address this gap, the organization needs to create and implement policies covering industry standards for secure coding, adherence to PCI DSS guidelines (such as secure authentication and logging), and integration of information security considerations throughout the entire software development lifecycle.

---

## 6.2.2 — PCI DSS 6.2.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The organization's policy library lacks documentation for training software development personnel on secure coding practices and security testing tools as required by PCI DSS 6.2.2.

---

## 6.2.3 — PCI DSS 6.2.3

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The organization's policy library lacks documentation for PCI DSS 6.2.3, which mandates that bespoke and custom software undergoes review to identify and correct potential coding vulnerabilities before release. Without this specific policy coverage, the organization cannot ensure adherence to secure coding guidelines or address emerging software vulnerabilities as required by the standard.

---

## 8.1.1 — PCI DSS 8.1.1

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.73)

**Rationale:** Inferred from sibling controls: 3 of 5 evaluated controls in Requirement 8 are fully compliant. Gaps remain in 8.2.4, 8.2.2.

---

## 8.1.2 — PCI DSS 8.1.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.73)

**Rationale:** Inferred from sibling controls: 3 of 5 evaluated controls in Requirement 8 are fully compliant. Gaps remain in 8.2.4, 8.2.2.

---

## 8.2.1 — PCI DSS 8.2.1

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text directly addresses the requirement by stating that all users must have a unique user ID assigned before being granted access to system components or cardholder data, which is equivalent to the control's sub-requirement.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 2.1  Unique User Identification | All users must be assigned a unique user ID before they are allowed access to any system component or cardholder data. |

---

## 8.2.2 — PCI DSS 8.2.2

**Framework:** PCI-DSS | **Verdict:** 🟡 Partially compliant (0.65)

**Rationale:** The policy text provides evidence for two sub-requirements related to dual-authorization and enhanced logging, which address the need for confirming individual identity before access is granted and attributing actions to individuals. However, it does not provide direct evidence for preventing ID use unless necessary, limiting use to exceptional circumstances, documenting business justification, or requiring explicit management approval.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 2.1  Unique User Identification | In cases where shared accounts are technically unavoidable (e.g., certain legacy systems), compensating controls incl... |

---

## 8.2.3 — PCI DSS 8.2.3

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text explicitly states that service provider personnel with remote access to customer premises must use unique MFA credentials for each customer, which directly addresses the requirement in PCI DSS 8.2.3.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 2 | 2.2  Multi-Factor Authentication (MFA) | Multi-factor authentication is required for all remote access to the corporate network and for all access to the Card... |

---

## 8.2.4 — PCI DSS 8.2.4

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The control is non-compliant because there is no policy documentation that outlines the process for managing user IDs, authentication factors, and other identifier objects as required by PCI DSS 8.2.4. To address this gap, the organization needs to create a detailed policy document specifying the procedures for authorized approval of changes, the roles responsible for these approvals, and the specific privileges granted based on documented approvals.

---

## 8.2.5 — PCI DSS 8.2.5

**Framework:** PCI-DSS | **Verdict:** ✅ Compliant (1.00)

**Rationale:** The policy text directly addresses the requirement by stating that upon termination of employment, all logical and physical access must be revoked immediately. This matches exactly with the control's sub-requirement.

**Supporting Evidence:**

| # | Source | Page | Section | Excerpt |
|---|--------|------|---------|---------|
| 1 | access_control_policy.pdf | 3 | 5  Access Revocation and Termination | For voluntary departures, access must be revoked no later than the last day of employment. Accounts belonging to term... |
| 2 | access_control_policy.pdf | 3 | 5  Access Revocation and Termination | Upon termination of employment, all logical and physical access must be revoked immediately. The Human Resources depa... |

---

## 12.1.1 — PCI DSS 12.1.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The control requires an established, published, maintained and disseminated overall information security policy which is currently missing in the organization's policy library.

---

## 12.1.2 — PCI DSS 12.1.2

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The organization's policy library lacks documentation that addresses the requirement for reviewing and updating the information security policy at least annually or as needed to reflect changes in business objectives or environmental risks. This gap means there is no formal process documented for ensuring continuous relevance of the security policies with respect to PCI DSS 12.1.2.

---

## 12.1.3 — PCI DSS 12.1.3

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The organization lacks a security policy that clearly defines information security roles and responsibilities for all personnel, as well as documentation showing that personnel are aware of and acknowledge their responsibilities.

---

## 12.1.4 — PCI DSS 12.1.4

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The organization lacks formal policy documentation that assigns responsibility for information security to a Chief Information Security Officer or another executive management member knowledgeable in information security as required by PCI DSS 12.1.4.

---

## 12.2.1 — PCI DSS 12.2.1

**Framework:** PCI-DSS | **Verdict:** ⚠️ Non-compliant (0.00)

**Rationale:** The organization lacks documented policies that cover explicit approval by authorized parties for end-user technologies, acceptable uses of these technologies, and a list of approved products including hardware and software as required by PCI DSS 12.2.1.

---

