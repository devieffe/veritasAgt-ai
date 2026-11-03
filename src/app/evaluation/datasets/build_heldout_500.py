"""Build the 500-case frozen synthetic holdout from explicit scenario families."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).parent
BASE = HERE / "heldout.jsonl"
OUTPUT = HERE / "heldout_500.jsonl"

CLAIM = "claim_extraction"
CONTRADICTION = "contradiction_detection"
FACTUAL = "factual_verification"
MISREPRESENTATION = "misrepresentation_detection"
NONSENSE = "nonsense_detection"
LOGIC = "logical_coherence"
SEMANTIC = "semantic_coherence"
CONTEXT = "context_awareness"
GROUNDING = "evidence_grounding"
UNCERTAINTY = "uncertainty_calibration"


def build() -> list[dict[str, object]]:
    cases = [json.loads(line) for line in BASE.read_text(encoding="utf-8").splitlines() if line.strip()]

    def add(case_id: str, conversation: str, expected: tuple[str, ...], note: str) -> None:
        cases.append(
            {
                "id": f"expanded-{case_id}",
                "conversation": conversation,
                "expected_categories": list(expected),
                "notes": note,
            }
        )

    # 80 individually testable claims without external evidence.
    materials = [
        "amber", "birch", "cobalt", "denim", "elm", "frosted", "granite", "hazel",
        "indigo", "jade", "khaki", "linen", "maple", "nickel", "opal", "pewter",
        "quartz", "russet", "silver", "teal",
    ]
    objects = [
        "access log", "battery case", "cable spool", "dispatch folder", "engine panel",
        "filter tray", "gauge cover", "hinge assembly", "inspection card", "junction box",
        "key register", "loading cradle", "meter housing", "nozzle cap", "outlet valve",
        "pressure gauge", "quality ledger", "relay module", "safety seal", "test fixture",
    ]
    values = [11, 14, 17, 19]
    claim_subjects = [(material, obj) for material in materials for obj in objects]
    for index, (material, obj) in enumerate(claim_subjects[:80], start=1):
        value = values[(index - 1) % len(values)]
        add(
            f"unsupported-fact-{index:03}",
            f"Speaker A: The {material} {obj} contains {value} labeled units.",
            (CLAIM, FACTUAL, UNCERTAINTY),
            "A concrete, unsupported factual assertion; absent independent evidence it remains unverified.",
        )

    # 50 negative controls: opinions, questions, hypotheticals, speculation, and metaphor.
    colors = ["blue", "green", "violet", "copper", "white", "black", "silver", "gold", "coral", "indigo"]
    items = ["binder", "cable", "drawer", "envelope", "folder", "glove", "handle", "inbox", "jacket", "label"]
    for index, (color, item) in enumerate(zip(colors, items, strict=True), start=1):
        add(f"opinion-control-{index:02}", f"Speaker A: I prefer the {color} {item}.", (), "A preference is not a factual assertion.")
        add(f"question-control-{index:02}", f"Speaker A: Is the {color} {item} in the cabinet?", (), "A question is not an asserted fact.")
        add(
            f"hypothetical-control-{index:02}",
            f"Speaker A: If the {color} {item} were in the cabinet, the inventory would change.",
            (),
            "A conditional is not an assertion that the condition is true.",
        )
        add(
            f"speculation-control-{index:02}",
            f"Speaker A: Perhaps the {color} {item} is in the cabinet.",
            (),
            "Explicit speculation is not presented as an established claim.",
        )
        metaphor = ["blanket", "ocean", "river", "wall", "storm"][index % 5]
        add(
            f"metaphor-control-{index:02}",
            f"Speaker A: The {color} {item} is a {metaphor} in this poem.",
            (),
            "Interpretable creative language should not be treated as a literal factual claim or nonsense.",
        )

    # 80 direct conflicts with evidence grounded in the conversation itself.
    conflict_objects = [f"test-{index:02} assembly" for index in range(1, 81)]
    for index, obj in enumerate(conflict_objects[:30], start=1):
        first, second = 20 + index, 60 + index
        add(
            f"direct-numeric-conflict-{index:02}",
            f"Speaker A: The {obj} weighs {first} kilograms.\nSpeaker B: The {obj} weighs {second} kilograms.",
            (CLAIM, CONTRADICTION, FACTUAL, GROUNDING),
            "Two speakers give incompatible numerical values for the same object; neither value is independently verified.",
        )
    for index, obj in enumerate(conflict_objects[30:55], start=1):
        add(
            f"direct-negation-conflict-{index:02}",
            f"Speaker A: The {obj} is operational.\nSpeaker B: The {obj} is not operational.",
            (CLAIM, CONTRADICTION, FACTUAL, GROUNDING),
            "A direct polarity conflict about the same proposition, supported by both transcript statements.",
        )
    opposite_pairs = [("open", "closed"), ("full", "empty"), ("on", "off"), ("present", "absent"), ("alive", "dead")]
    for index, obj in enumerate(conflict_objects[55:], start=1):
        left, right = opposite_pairs[(index - 1) % len(opposite_pairs)]
        add(
            f"direct-opposite-state-conflict-{index:02}",
            f"Speaker A: The {obj} is {left}.\nSpeaker B: The {obj} is {right}.",
            (CLAIM, CONTRADICTION, FACTUAL, GROUNDING),
            "Opposite descriptions conflict about the same object; the transcript is evidence of disagreement, not independent fact-checking.",
        )

    # 60 explicit self-corrections and 60 changes across distinct time periods.
    state_pairs = [("active", "inactive"), ("locked", "unlocked"), ("connected", "disconnected"), ("open", "closed"), ("full", "empty")]
    context_objects = [f"calibration station {index:02}" for index in range(1, 61)]
    for index, obj in enumerate(context_objects, start=1):
        first, second = state_pairs[(index - 1) % len(state_pairs)]
        add(
            f"correction-context-{index:02}",
            f"Speaker A: The {obj} is {first}.\nSpeaker A: Correction: the {obj} is {second}.",
            (CLAIM, FACTUAL, CONTEXT, UNCERTAINTY),
            "An explicit same-speaker correction; preserve it as an unverified correction, not a contradiction.",
        )
    time_objects = [f"service counter {index:02}" for index in range(1, 61)]
    periods = [("yesterday", "today"), ("last week", "this week"), ("last year", "this year"), ("formerly", "currently"), ("in 2022", "in 2025")]
    for index, obj in enumerate(time_objects, start=1):
        first, second = state_pairs[(index - 1) % len(state_pairs)]
        earlier, later = periods[(index - 1) % len(periods)]
        add(
            f"time-change-context-{index:02}",
            f"Speaker A: The {obj} was {first} {earlier}.\nSpeaker B: The {obj} is {second} {later}.",
            (CLAIM, FACTUAL, CONTEXT, UNCERTAINTY),
            "The states refer to different explicit periods; this is a time change, not a same-time contradiction.",
        )

    # 70 observable communication patterns, without attributing intent.
    groups = [f"sample group {index:02}" for index in range(1, 31)]
    for index, group in enumerate(groups, start=1):
        quality = ["complete", "approved", "ready", "accurate", "secure"][index % 5]
        add(
            f"unsupported-universal-{index:02}",
            f"Speaker A: Every member of the {group} is {quality}.",
            (CLAIM, FACTUAL, MISREPRESENTATION, UNCERTAINTY),
            "An unsupported universal statement is an observable scope issue; the transcript does not establish intent or the universal claim.",
        )
    for index in range(1, 21):
        subject = f"trial batch {index:02}"
        add(
            f"selective-presentation-{index:02}",
            f"Speaker A: The summary for {subject} is selective because it includes only the positive trials and left out the failed ones.",
            (CLAIM, FACTUAL, MISREPRESENTATION, UNCERTAINTY),
            "The speaker explicitly describes omission of failed cases; label the observable selective presentation without inferring motive.",
        )
    for index in range(1, 21):
        subject = f"inspection rule {index:02}"
        add(
            f"goalpost-shift-{index:02}",
            f"Speaker A: Now the {subject} has changed; that does not count.",
            (CLAIM, FACTUAL, MISREPRESENTATION, UNCERTAINTY),
            "The wording signals a changed criterion; flag the observable move without deciding whether it was justified.",
        )

    # 30 reasoning probes: invalid arguments and valid inference controls.
    dilemma_subjects = [f"archive set {index:02}" for index in range(1, 7)]
    for index, subject in enumerate(dilemma_subjects, start=1):
        add(
            f"false-dilemma-{index:02}",
            f"Speaker A: Either the {subject} is completely searchable or it is worthless.",
            (CLAIM, FACTUAL, LOGIC, UNCERTAINTY),
            "The conclusion presents two options as exhaustive without establishing that no alternatives exist.",
        )
    names = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    for index, name in enumerate(names, start=1):
        event = f"single report {name}"
        population = f"sensor family {name}"
        add(
            f"hasty-generalization-{index:02}",
            f"Speaker A: This one {event} proves every unit in the {population} fails.",
            (LOGIC, MISREPRESENTATION, GROUNDING),
            "A single example is used to assert a universal conclusion; both findings should cite the transcript.",
        )
    for index in range(1, 7):
        first, second = f"signal {index:02}", f"module {index:02} update"
        add(
            f"post-hoc-cause-{index:02}",
            f"Speaker A: The {first} occurred after the {second}, therefore the {second} caused the {first}.",
            (CLAIM, FACTUAL, LOGIC, UNCERTAINTY),
            "Temporal sequence alone does not establish the asserted causal link; the claim has no independent evidence.",
        )
    for index in range(1, 7):
        subject = f"routing rule {index:02}"
        add(
            f"circular-reasoning-{index:02}",
            f"Speaker A: The {subject} is reliable because the {subject} is reliable.",
            (CLAIM, FACTUAL, LOGIC, UNCERTAINTY),
            "The stated reason repeats the conclusion instead of giving independent support.",
        )
    for index in range(1, 7):
        subject = f"sensor {index:02}"
        add(
            f"valid-inference-control-{index:02}",
            f"Speaker A: If the {subject} is active, it sends a signal. The {subject} is active. The {subject} sends a signal.",
            (CLAIM, FACTUAL, UNCERTAINTY),
            "The stated conclusion follows from the conditional and premise; the underlying factual claims remain unverified offline.",
        )

    # 20 semantic absurdity probes; unlikely but coherent claims are covered elsewhere.
    causes = [
        "the quiet hallway", "a closed cabinet", "the blue label", "the empty tray", "a short delay",
        "a missing signature", "the dry fountain", "a folded map", "an unpowered motor", "a dropped pencil",
    ]
    for index in range(1, 11):
        cause = causes[index - 1]
        add(
            f"absurd-cause-{index:02}",
            f"Speaker A: Because {cause}, the moon will cease to exist.",
            (CLAIM, FACTUAL, NONSENSE, SEMANTIC, UNCERTAINTY),
            "The stated cause is not a plausible mechanism for the asserted destruction; absent external evidence the claim also remains unverified.",
        )
    categories = ["Monday", "Tuesday", "the color blue", "a melody", "the number seven"]
    for index in range(1, 11):
        category = categories[(index - 1) % len(categories)]
        add(
            f"category-error-{index:02}",
            f"Speaker A: The square root of {category} weighs exactly {index + 12} kilograms.",
            (CLAIM, FACTUAL, NONSENSE, SEMANTIC, UNCERTAINTY),
            "The wording applies mathematical and physical properties to incompatible categories.",
        )

    # 9 bounded factual claims and 8 additional no-finding controls.
    for index in range(1, 10):
        add(
            f"bounded-count-control-{index:02}",
            f"Speaker A: The inspected tray {index:02} contains {index + 2} labeled units; the report covers this tray only.",
            (CLAIM, FACTUAL, UNCERTAINTY),
            "A bounded, explicitly scoped factual claim is not an unsupported universal statement.",
        )
    for index in range(1, 5):
        add(
            f"neutral-opinion-control-{index:02}",
            f"Speaker A: I like the textured cover {index:02}.",
            (),
            "A subjective preference is not a factual review finding.",
        )
    for index in range(1, 5):
        add(
            f"neutral-question-control-{index:02}",
            f"Speaker A: Did the sealed package {index:02} arrive before noon?",
            (),
            "A question does not assert that the package arrived.",
        )

    ids = [str(case["id"]) for case in cases]
    conversations = [str(case["conversation"]) for case in cases]
    if len(cases) != 500:
        raise ValueError(f"Expected 500 cases, found {len(cases)}")
    if len(ids) != len(set(ids)):
        raise ValueError("Case ids are not unique")
    if len(conversations) != len(set(conversations)):
        duplicates = sorted({text for text in conversations if conversations.count(text) > 1})
        raise ValueError(f"Conversation texts are not unique: {duplicates}")
    return cases


def main() -> None:
    cases = build()
    OUTPUT.write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases),
        encoding="utf-8",
    )
    print(f"wrote {len(cases)} unique cases to {OUTPUT}")


if __name__ == "__main__":
    main()
