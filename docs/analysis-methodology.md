# Analysis methodology

## What the system evaluates

VeritasAgent evaluates statements, reasoning, and supplied evidence. It does not assign honesty, intent, or character to a speaker. A disagreement is not proof that either participant lied.

## Verification statuses

| Status | Meaning |
| --- | --- |
| `VERIFIED` | A sufficiently reliable source supports the claim. |
| `SUPPORTED` | Available evidence supports the claim, but may be incomplete or not independently audited. |
| `UNVERIFIED` | No adequate evidence was available. This does not mean the claim is false. |
| `CONTRADICTED` | Available evidence conflicts with the claim. A conflict alone does not establish which statement is true. |
| `FALSE` | Reliable evidence directly refutes the claim. Offline checks do not assign this status. |
| `MISLEADING` | The wording has an observable misleading pattern, such as an unsupported universal generalization. Intent is not inferred. |
| `NOT_APPLICABLE` | The finding concerns reasoning or context rather than truth verification. |

## Severity and confidence

Severity is an integer from 0 to 5 describing the potential importance of a review item. Confidence is a separate number from 0 to 100 describing how strongly the available evidence supports that finding. Neither value is a probability that a speaker intended to deceive. Low confidence and explicit limitations should be retained for ambiguous or weakly supported findings.

## Distinct analysis categories

- **Factual verification** compares a factual claim with available evidence. Without an evidence source, the result stays `UNVERIFIED`.
- **Contradiction detection** looks for incompatible statements about the same subject and period. Corrections, clarifications, different times, and differing preferences should not become contradiction findings.
- **Logical coherence** examines whether a conclusion follows from its stated reasons. It explains the missing premise or unsupported inference rather than returning a label alone.
- **Nonsense and absurdity** focuses on semantic incoherence, category errors, or implausible causal conclusions. An unusual but interpretable factual assertion is sent for verification instead.
- **Misrepresentation** describes an observable communication pattern, such as an unsupported absolute claim. It does not claim that a speaker acted deliberately.
- **Context analysis** checks the full conversation for time references, corrections, ambiguity, and other plausible interpretations.

## Evidence discipline

Evidence objects preserve source type, reference, content, and a reliability note. Conversation statements can establish what was said and reveal a conflict, but they are not independent confirmation of the underlying fact. External sources are used only when supplied or when a configured evidence adapter is enabled. Missing sources are not fabricated.
