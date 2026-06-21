# Design Documentation

The core design philosophy of AVIS (Automated Violation Intelligence System) addresses a fundamental flaw in many automated traffic systems: claiming absolute accuracy on complex temporal or spatial violations from a single static image. AVIS wins by being rigorous about what evidence a single image can provide.

## 1. The Core Philosophy

1. **Evidence Sufficiency First**: The system explicitly tags every violation with what evidence a single image can truly provide. It does not blindly auto-confirm things it cannot prove.
2. **Deterministic CV for Detection; AI for Judgement**: Fast, open computer vision models handle raw detection. A Vision-Language Model (VLM) is only invoked to *verify* ambiguous edge cases or explain the reasoning, keeping the pipeline fast and predictable.
3. **Explainable and Accountable by Construction**: Every decision is supported by an `EvidenceGraph`. The system outputs an explainable reason, a confidence score, the legal grounding, and a tamper-evident hash.
4. **Abstention as a Feature**: If an image is too blurry, overexposed, or lacks sufficient geometry to make a call, the system *abstains*. This prevents false positives.

## 2. The Violation Detectability Matrix

This matrix is the intellectual core of the system and dictates how the Rule Engine processes detections. Violations are categorized into four tiers based on their provability.

| Violation | Tier | What a Single Image Proves | Handling Strategy |
| :--- | :---: | :--- | :--- |
| **Helmet non-compliance** | **A (Appearance)** | Reliable: Head/helmet is clearly visible. | Auto-confirm if confidence is high. Else, send to VLM. |
| **Triple riding** | **A (Appearance)** | Reliable: Count of people on a motorcycle. | Auto-confirm if count is clear. Else, send to VLM. |
| **Seatbelt non-compliance**| **B (Hard appearance)** | Weak: Often obscured by windshield glare. | Never auto-confirm. VLM verify, label as low confidence. |
| **Stop-line violation** | **C (Spatial)** | Strong candidate: IF camera calibration exists. | VLM-verify with calibration polygon. Human review if none. |
| **Red-light running** | **C/D (Spatial + Temporal)** | Candidate only: Light is red, car is past line. | VLM-verify. Flag as needing sequence confirmation. |
| **Illegal parking** | **C/D (Spatial + Temporal)** | Candidate only: Needs to prove dwell time. | Generate candidate. Flag "needs dwell-time confirmation." |
| **Wrong-side driving** | **D (Temporal)** | Unprovable: Direction requires motion. | Emits low-confidence candidate. Recommends video review. |

## 3. Confidence Fusion and Routing

The system calculates a single "fused" confidence score using a weighted average:
```text
fused = (w1 * detection_conf) + (w2 * attribute_conf) + (w3 * rule_evidence)
```

Based on the fused score and the violation Tier, the **Router** chooses one of four paths:
1. **Auto-confirm**: Fast lane. Bypasses human review and VLM. Applicable mostly to strong Tier A.
2. **VLM-verify**: Intermediate path. The VLM is sent the cropped image and asked a strict yes/no question.
3. **Human Review**: Sent to the dashboard queue for manual inspection. Used when confidence is low or VLM is unsure.
4. **Abstain**: Dropped entirely due to failed quality gate or `insufficient_evidence` response from the VLM.

## 4. The VLM Verification Layer

AVIS uses the Gemini Flash API on the free tier. Because API calls are rate-limited, the system only invokes the VLM when necessary (the `VLM-verify` route).
- It asks a strict JSON-contract question: `{"verified": bool, "confidence": float, "reason": str}`.
- To conserve quota, results are hashed based on the cropped image bounding box and cached.
