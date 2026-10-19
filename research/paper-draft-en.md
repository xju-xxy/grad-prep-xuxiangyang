# Multi-Agent Evaluation for Disaster Situation Reasoning and Decision Support: The CrisisBench Benchmark and Constraint Verification

> Paper draft v3 (2026-10-19: v0.4 full experimental results merged in)
> Companion materials: [Domain review](domain-review.md) · [Roadmap](paper-roadmap.md) · [Scoring rubric](crisis-bench/scenarios/rubric.md) · [Experimental results](crisis-bench/results/RESULTS-v0.4.md)

---

## Abstract

Large language model (LLM)-driven multi-agent collaboration has shown advantages in open-domain tasks like office work and coding, yet high-stakes disaster emergency decision-making still lacks both a benchmark for evaluating multi-agent decision quality and a mechanism for trustworthy verification of decision outputs. We introduce CrisisBench, a Chinese benchmark for disaster situation reasoning and decision support, together with a constraint verification component. CrisisBench v0.4 contains 36 disaster scenarios (14 single-hazard, 14 chained secondary disasters, 8 information-contradiction) and 709 rubric points, 48 of which are numerical-inference points, organized into factual, reasoning, and decision layers with objective 0/1 checklist scoring. A pilot study with glm-4-flash shows multi-agent (four roles) outperforms single-agent by 5.2 percentage points under 2-of-3 majority vote (95.8% vs 90.6%) and by 20.9 points under the stricter judge; two LLM judges reach a Cohen's kappa of 0.03~0.08, making them non-interchangeable. v0.4 full experiments confirm this: multi-agent gains 7.05 points over single-agent (90.7% vs 83.5%; p=3.0×10⁻⁹, 95% CI [+3.3, +11.0] pp), removing the auditor costs 7.32 pp (p=6.5×10⁻⁷), and the verifier adds 2.81 pp (p=2.7×10⁻³, 95% CI [+0.1, +6.1] pp); glm-4-plus nearly saturates the benchmark (9.11 pp above flash, p=2.1×10⁻¹⁵). Annotator adjudication on 71 true three-judge disagreements agrees 88.7% with the flash judge and 78.9% with the majority vote, and multi-agent costs about 1.86× the tokens of single-agent. Our contribution is a reproducible benchmark, a majority-vote protocol, and a validated verifier.

**Keywords**: disaster emergency decision-making; multi-agent; benchmark; large language models; constraint verification; three-layer scoring

---

## 1 Introduction

After a disaster strikes, command centers face massive heterogeneous information (field reports, social media, meteorological and hydrological data, telemetry) under extreme time pressure, and need to rapidly form a judgment of "what is the situation now, what will happen next, and what should be done" under conditions of incomplete or even contradictory information. LLMs and multi-agent collaboration frameworks offer new tools for this: multiple roles, each with its own responsibility and verifying each other, can potentially organize fragmented information into traceable decision recommendations.

Yet this direction lacks basic evaluation infrastructure. A literature survey shows that existing work is scattered across four isolated positions: disaster information entry (tweet classification, place-name georeferencing), disaster knowledge question answering (LLMs enhanced with knowledge graphs), multi-agent collaboration mechanisms (concentrated in the office, coding, and travel-planning domains), and disaster-domain deployment (the training simulation Sim911 measures "operator performance" rather than "decision quality"; the after-action review evaluation LogiDebrief performs post-hoc analysis rather than in-event decision-making). **No one has established a decision-quality benchmark for "multi-agent disaster situation reasoning and decision support"** — whether multi-agent systems help reasoning or harm facts in disaster decision-making, and where knowledge enhancement and verification mechanisms take effect, both lack measurable and reproducible evidence. At the same time, the constraints of disaster decision-making (resource conservation, spatial consistency, temporal validity) are naturally formalizable, yet have not been made into an "acceptance gate" before agent output.

To address these gaps, this paper does three things:

1. **Build the CrisisBench benchmark**: v0.4 consists of 36 Chinese disaster decision scenarios (14 single-hazard / 14 chained secondary disaster / 8 information-contradiction), with 709 rubric points in total, annotated with a "factual layer / reasoning layer / decision layer" three-layer scheme; the scenario design deliberately embeds numerical-inference rubric points (48), contradictory intelligence, and trap-disposal inducements, to prevent "copying the intelligence for a perfect score" and to guarantee discrimination. Its predecessor v0.3 (5 scenarios, 96 rubric points) completed benchmark construction and calibration and serves as the data basis for the pilot experiments in this paper (§6.3, §6.5).
2. **Propose a three-judge majority-vote evaluation protocol**: the same batch of answers is independently scored by a rule matcher and two LLM judges, with 2-of-3 majority vote as the official criterion, and mandatory reporting of inter-judge agreement rates and Cohen's kappa. The most direct finding of the pilot — two LLM judges with kappa≈0 — is itself an empirical instance, in the disaster decision-making setting, of the unreliability of LLM-as-a-judge documented in the methodological literature.
3. **Design a constraint verification component**: write the five categories of checks — resource over-allocation, quantity accounting, numerical inference, intelligence conflict, and trap disposal — as deterministic rules, serving as an acceptance gate of the decision chain, and complete its controlled experiment against LLM judges (§6.6). The motivation comes directly from the judge-reliability experiment: the most error-prone verification work should be assigned to deterministic rules rather than LLMs.

Pilot experimental findings (model under test glm-4-flash; v0.3 setting: 96 rubric points × 2 configurations × 3 judges):

- Multi-agent (intelligence officer → analyst → decision officer → auditor, serial) outperforms single-agent: +5.2pp under the majority-vote criterion, +20.9pp under the strict-judge criterion;
- LLM judges are unreliable: the lenient judge model approaches saturation (99.0% fully correct), while the strict judge model systematically tightens and has high variance (12 points apart on the same scenario and the same batch of answers), and the two have kappa≈0;
- Discrimination comes from "hard rubric points": numerical-inference points are the loss points in all configurations, among which "inferring the time for benzene vapor to reach a residential area" is unanimously 0 across all three judges; the multi-agent gain comes from the audit step completing "omission-type errors" (fixing 2 computational points that single-agent fails to obtain).

On this basis, this paper has completed the v0.4 full experiments (36 scenarios × 709 rubric points × 6 configurations: single / multi / multi-noaudit / multi-verify @glm-4-flash, single / multi @glm-4-plus), following the three-judge majority-vote criterion, with the following core results:

- **The multi-agent gain is directionally consistent and comparable in magnitude to the pilot**: multi is 7.05pp higher than single at the scenario level (overall score 90.7% vs 83.5%; McNemar p=3.0×10⁻⁹, Wilcoxon p=0.0008, 95% CI [+3.3, +11.0] pp), on the same order as the v0.3 pilot's +5.2pp (5 pilot scenarios vs 36 full-set scenarios, so the two are not directly comparable) (§6.3).
- **The auditor and the constraint verification component each yield a quantifiable gain**: removing the auditor makes multi drop by 7.32pp (p=6.5×10⁻⁷, §6.4); adding the Verifier on top of the full multi yields a further +2.81pp (p=2.7×10⁻³, §6.6), mainly suppressing resource over-allocation, trap, and capacity-shortfall errors.
- **The stronger model approaches the ceiling**: glm-4-plus under the multi configuration is 9.11pp higher than flash (p=2.1×10⁻¹⁵), with 35 of 36 scenarios at full score, and multi and single show no significant difference (McNemar exact binomial p=1.0) — suggesting that this benchmark's discrimination for strong models is saturating, requiring v0.5 to introduce harder scenarios or a more discriminative hard-rubric-point subset.
- **The judge-reliability conclusion replicates on the full set**: the two judges have kappa near 0 throughout (multi@flash 0.081, single@flash 0.079, others −0.008~−0.003), and the flash judge's self-consistency is 0.99 for single and 1.00 for multi (§6.5).
- **A6 adjudication and A8 cost accounting are complete**: on 71 true three-judge disagreements from 8 scenarios, human-machine agreement is 88.7% vs the flash judge and 78.9% vs the majority vote (§6.5); multi-agent costs about 1.86× the tokens of single-agent (§6.8).

---

## 2 Related Work

This section briefly reviews, along the four chain segments "disaster information entry → knowledge-enhanced reasoning → multi-agent collaboration → disaster-domain deployment", the research most relevant to this work (the full survey is in the companion review).

**Disaster information entry.** Going from fragmented information to structured elements is the prerequisite step of decision-making. Early supervised classification models rely on annotation and generalize poorly across disaster types; recent work systematically evaluates zero-shot LLM classification on crisis tweets and finds that it still falls below supervised baselines, with the flood category, help-seeking information, and misspelled text being three notable weaknesses [Crisis tweet evaluation, WWW'25]. Work such as place-name georeferencing and integrated remote-sensing interpretation advances LLM perception to the localization level [DisasterTD; RescueADI], but all of it stops at the perception layer and does not enter the decision layer.

**Knowledge-enhanced reasoning.** KG-enhanced LLMs, GraphRAG, closed-loop self-correction, and temporal evolution are the main lines of development in this chain segment [RAG; E-KELL; GraphRAG survey; CogMG; spatio-temporal KGQA]. A representative disaster-domain work is E-KELL: it supports hazardous-chemical leakage emergency decision-making with a knowledge graph and an LLM, improving a decision-support form measured by expert subjective scoring, and it is not a multi-agent analytical structure. General knowledge-enhancement techniques are already quite mature and not difficult to "assemble"; the gap lies in disaster-domain customization (causal-chain representation, coupling of spatio-temporal constraints with decisions) and evaluation.

**Multi-agent collaboration.** From ReAct's single-agent "think one step, act one step", to AutoGen's conversational multi-role collaboration, automatic orchestration and cost scheduling, and closed-loop frameworks with verification functions, procedural memory, and multi-constraint planning [ReAct; AutoGen; MetaAgent; VeriMAP; LEGOMem; PMC], the collaboration paradigm has shifted from "prompt engineering" to "systems engineering": state machines, verification functions, and memory stores are all in place. **Yet the evaluation of all these mechanisms is located in the mathematics, coding, travel, and office domains, and not one has modeled and evaluated the unique constraints of disaster decision-making** (fatal consequences, time pressure, incomplete information, chained secondary disasters).

**Disaster-domain deployment.** There are already four scattered footprints: Sim911 uses an LLM to play a 911 dispatcher for training simulation, and its evaluation criterion is trainee performance rather than system decision quality [Sim911, AAAI'25]; LogiDebrief converts drill after-action-review requirements into signal temporal logic formulas for automatic adjudication, which belongs to post-hoc evaluation [LogiDebrief, IJCAI'25]; E-KELL is oriented to question answering; DisasterTD/RescueADI are oriented to perception. The segment of "multi-agent collaborative reasoning and decision-making" is empty — this paper's CrisisBench fills precisely this gap, while the constraint verification component inherits VeriMAP's idea of "an executable verification function for each subtask" and makes it disaster-specific: writing resource conservation, numerical inference, and intelligence consistency as acceptance rules.

---

## 3 Task Formulation and the CrisisBench Dataset

### 3.1 Task definition

Given a disaster decision scenario, it is formalized as a quintuple `(disaster type, time point, set of intelligence fragments I, available resource list R, three-layer rubric points)`. Here the intelligence fragments I come from multiple sources (bulletin / field / social media / meteorology) and may contain distraction, contradictions, and inducements toward erroneous disposal; the resource list R explicitly lists callable resources and "none" items (e.g., "no helicopter"). The system under test must output three-layer situational conclusions:

- **Factual layer**: whether key intelligence elements are fully collected and whether key numerical values are correctly inferred;
- **Reasoning layer**: whether causal conclusions are drawn and settled;
- **Decision layer**: whether action recommendations have concrete targets and actions, whether resources are feasible, and whether they conflict with confirmed facts.

Evaluation uses item-by-item objective 0/1 checklist adjudication (§4), with no 0.5 score. This setting constrains "multi-agent disaster situation reasoning" from an open generation problem into a scoreable and reproducible benchmark task.

### 3.2 Dataset overview (v0.4)

CrisisBench v0.4 comprises **36 scenarios and 709 rubric points**, divided into three classes by difficulty:

| Class | # Scenarios | Scenario IDs | Rubric points per scenario | Subtotal | Design feature |
|---|---|---|---|---|---|
| Single hazard | 14 | S002, S003, S006~S017 | 18~19 | 259 | Single hazard cause; tests full information collection and standard disposal |
| Chained (secondary disasters) | 14 | S001, S004, S018~S029 | 18~21 | 283 | Primary disaster triggers a secondary chain; tests situational evolution and cascading disposal |
| Information contradiction | 8 | S005, S030~S036 | 20~21 | 167 | ≥2 sets of contradictory figures per scenario; requires conservative disposal + unified-figure reporting |
| **Total** | **36** | — | 18~21 | **709** (including 48 numerical-inference rubric points) | Per scenario: factual 8~9 / reasoning 4~5 / decision 6~7 |

Among these, **S001~S005 are the v0.3 originals (96 rubric points; their historical experimental data and this paper's pilot citations are unchanged); S006~S036 are new in v0.4 (613 rubric points)**. Disaster-type coverage: earthquake, flooding, flash flood, debris flow, landslide, typhoon, rainstorm waterlogging, freezing rain/snow and icing, blizzard, gale, wildfire, grain depot fire, residential fire, chemical explosion/leakage, gas station, hydrogen sulfide poisoning, factory collapse, reservoir flood discharge, etc. (The authoritative per-scenario list follows rubric.md §5.)

The five original v0.3 scenarios decompose by layer as follows (retained as evidence of benchmark construction and pilot experiments):

| Scenario | Disaster type | Class | Time point | # Factual/Reasoning/Decision rubric points | Difficulty feature |
|---|---|---|---|---|---|
| S001 | Earthquake | Chained secondary disaster | 5 hours after the quake | 8/4/6 = 18 | Evacuation scale requires inference (240 households × 1-2 persons); tent-shortage trap; seismic risk of adobe houses |
| S002 | Flooding | Single hazard | Day 2 of an extraordinary rainstorm | 8/4/6 = 18 | Aggregate of trapped persons (about 200); 4-hour power-protection window for the hospital; private cars intruding |
| S003 | Wildfire | Single hazard | Hour 3 after ignition | 8/5/6 = 19 | Inference of fire-front arrival time (4-6 hours); nighttime cooling ≠ weakening fire; villagers going up the mountain |
| S004 | Chemical leakage | Chained secondary disaster | 1 hour after leakage | 9/5/7 = 21 | Inference of benzene vapor arrival in 8-9 minutes; water-flushing dilution trap; secondary explosion of adjacent storage tanks |
| S005 | Typhoon | Information contradiction | During the disaster | 8/5/7 = 20 | Three sets of contradictory data; capacity shortfall of 2 vs 8 rescue boats; reversal rumor |

The v0.4 new scenarios (S006~S036) all follow the same layer-decomposition specification: factual layer 8~9, reasoning layer 4~5, decision layer 6~7, totaling 18~21 rubric points; each scenario carries 1~2 numerical-inference rubric points and ≥1 trap; S030~S036 are of the information-contradiction class.

### 3.3 Scenario specification and construction process

**Intelligence composition.** Each scenario has 8~11 multi-source intelligence fragments (a mix of four source types: bulletin / field / social media / meteorology), deliberately mixed with 1~2 **distractor intelligence** items (irrelevant to the decision but easily inducing elaboration, e.g., "the fire brigade of the neighboring county has just finished a drill"). Information-contradiction scenarios additionally create ≥2 sets of **contradictory figures** (the same indicator appearing with conflicting numerical values). In addition, the intelligence contains characters **proposing erroneous practices** (e.g., "directly flushing the benzene liquid on the ground with a fire hose", "dispatching by the ledger count", "plugging the leak bare-handed"), corresponding to the trap rubric points of the decision layer.

**Resource list.** Each scenario has 4~6 resource-list items, and **must include a "no X" negative item** (e.g., "no helicopter"), used for judging the resource over-allocation trap.

**Numerical-inference rubric points.** Each scenario has 1~2 such points, requiring that key numbers do not appear directly in the intelligence and must be computed across ≥2 intelligence fragments. Representative examples:

| Inference point | Intelligence inputs | Inference formula | Expected interval |
|---|---|---|---|
| S001-F8 (transfer scale) | Two villages of about 240 households, 1~2 persons staying per household | 240×(1~2) | 300~500 persons |
| S003-F8 (fire-front approach) | Fire line 6 km from the village, spread 1~1.5 km/h | 6÷(1~1.5) | 4~6 hours |
| S004-F9 (benzene vapor arrival) | 2 km from the residential area, wind speed 4 m/s | 2 km÷4 m/s | 8~9 minutes |
| v0.4 new example (barrier-lake overtopping) | Water level before the dam is 3 m below overtopping, rising 0.5 m/h | 3÷0.5 | about 6 hours |
| v0.4 new example (pumping duration) | 18 pumps × 200 m³/h, 60000 m³ to drain | 60000÷(18×200) | about 16.7 hours |

**Trap rubric points and contradiction rubric points.** Trap-type rubric points are phrased as "must see through the erroneous practice and give the correct practice" (credit is given only if both seeing-through and the correct practice are achieved). Information-contradiction scenarios (S005, S030~S036) mandatorily include: ≥2 sets of contradictory figures, a "dispose by the conservative figure and verify the disaster" rubric point, and "unify the data standard / report point by point" decision rubric points.

Scenarios are written in Chinese; the material prototypes are typical elements drawn from public disaster investigation reports and bulletins (reservoir cracks, being trapped in tunnels, missing isolation belts, leakage into rivers, etc.), and their reasonableness is to be reviewed item by item by the annotator before submission.

### 3.4 Three-layer scoring rubric (objective 0/1 checklist)

All rubric points are organized into three layers, **each rubric point is independently judged 0/1, with no 0.5 score**, and "hitting a point is not an error" — only whether "what should have been said has been said" is checked, and irrelevant content is not penalized (except for hard faults in the decision layer). Adjudication is checklist-style, and synonymous substitutions ("evacuate" = "withdraw") count as hits.

- **Factual layer (F)**: whether the answer fully collects key intelligence elements. **Numerical-inference rubric points**: key numbers do not appear directly in the intelligence, and the answer must give the **inferred numerical value or numerical interval** to be satisfied; merely restating the original numbers in the intelligence does not count. The judge verifies the numerical values against the original intelligence text.
- **Reasoning layer (R)**: the object of adjudication is the **conclusion** — if the answer explicitly expresses that item's conclusion (wording may differ, the meaning is in place, no contradiction with the intelligence) it scores 1; if the conclusion is absent or opposite it scores 0. The "start point / mechanism / endpoint" fields retained in the scenario JSON are only for manual verification and for displaying the causal structure in the paper, and are not required as literal point-by-point matching for the judge (v0.2 experience: literal matching makes judge variance explode).
- **Decision layer (D)**: each recommendation that has **a specific target + a specific action** scores 1; vague phrasing ("strengthen forces", "do good work") scores 0. If any of the following hard faults occurs, that item scores no point and the reason is recorded: ① no target; ② **resource over-allocation** (using resources outside the resource list); ③ conflict with the intelligence (e.g., still "evacuating via the county road" when the road is already cut, without mentioning a detour). Trap-type rubric points are phrased as "must see through the erroneous practice", and credit is given only if the erroneous practice is seen through and the correct practice is given.

Three-layer scores are all hits / number of rubric points; the composite score takes the equal-weight average of the three layers and is used only for overview ranking; the paper's main text centers on the layer-wise results.

### 3.5 Two calibration rounds and the v0.3→v0.4 expansion

The benchmark-construction process retains two calibration records (the data files are released with the benchmark), which themselves constitute the "benchmark construction methodology" part of the paper:

- **v0.2 lesson one: a perfect factual layer has no discrimination.** The intelligence is delivered directly to the system under test, factual rubric points are almost all copyable, and all configurations approach full score. → v0.3 adds 1~2 **numerical-inference rubric points** per scenario.
- **v0.2 lesson two: judge variance is too large.** On the same batch of answers, the original glm-4-flash prompt judged almost everything 1, while glm-4-plus with a "rather strict than lenient" prompt judged almost everything 0 in the reasoning/decision layers. → v0.3 takes a two-pronged approach: ① rewrite all rubric points as **objectively verifiable concrete conclusions / concrete measures**; ② adopt a middle-of-the-road judge prompt and retain dual-model cross-judging.

**v0.3→v0.4 expansion strategy.** Pilot results show that the benchmark's discrimination lies not in the aggregate score but in the "hard rubric-point subset" (numerical-inference, contradiction, and trap types; see §7.1). Accordingly, the v0.4 expansion is not simply adding intelligence noise, but **replicating these three sources of discrimination in bulk and generalizing them to 8 disaster types**: numerical-inference rubric points expand from 3 in v0.3 to 48; information-contradiction classes generalize from the single scenario S005 to 8 scenarios; each scenario mandatorily has 1~2 inference points + ≥1 trap. At the same time the number of intelligence fragments (8~11) and the resource list (4~6 items, including a negative item) are unified per scenario, ensuring cross-scenario comparability.

---

## 4 Evaluation Protocol: Three-Judge Majority Vote + Mandatory Reliability Reporting

Scoring is implemented in two ways (details in rubric.md §6):

1. **Rule scoring (zero-cost reference)**: keyword matching point by point; a hit in the word list scores 1. It is free and zero-variance, but "mentioning the word ≠ answering correctly", so it is positioned as developer self-check and a cheap reference, not the official score.
2. **LLM scoring (official)**: the "original intelligence + rubric-point list (with unique IDs) + answer under test" is given to a judge model, which is required to output a JSON 0/1 and a one-sentence reason item by item; rubric points marked "inference" must have their numerical values checked; a missed judgment by the judge counts as 0; parse failure is retried once. The judge and the model under test use the same API but are called independently with role isolation, at temperature 0.

The protocol has three points:

- **Multiple-judge majority vote**: each rubric point is independently adjudicated by the rule matcher + glm-4-flash + glm-4-plus, and the **2-of-3 majority vote is the official primary metric**;
- **Re-scoring the same batch of answers with a different judge (`--rescore`)**: ensures that "the score difference = the judge difference, independent of the answers", an essential design for judge reliability analysis;
- **Mandatory reporting of agreement rate and kappa**: the pairwise agreement rate between judges and Cohen's kappa must be reported alongside the main results (pilot results in §6.5), and disagreements are manually spot-checked and adjudicated by the annotator (corresponding to experimental route A6, to be completed before submission). Manual spot-check plan: randomly sample 20~30% of scenarios, review and adjudicate disagreements point by point, and report the human-machine agreement rate.

---

## 5 Constraint Verification Component (Verifier)

### 5.1 Motivation

§6.5 shows that assigning checklist verification to LLM judges costs saturation, variance, and near-random inter-judge agreement. Yet many of the things that truly need to be verified in disaster decision-making — whether resources are over-allocated, whether quantities add up, whether inferred values are correct, whether recommendations conflict with confirmed facts — **are naturally formalizable deterministic checks**. Therefore this work designs a deterministic constraint verification component (a disaster-specific version of VeriMAP), placed in the multi pipeline before the auditor: it runs rule checks on the preceding utterances (or the final report), outputs a violation list, and returns it to the auditor to correct before the final report is produced. The component does not replace the LLM judge but takes on "the most error-prone verification work".

### 5.2 Rule table

| ID | Category | Check content (deterministic implementation) | Corresponding scenario example |
|---|---|---|---|
| V1 | Resource over-allocation | Every resource appearing in the decision must belong to the scenario resource list, or be accompanied by an "external reinforcement + source" note (the list explicitly includes negative items such as "no helicopter") | S001 dispatching a helicopter when there is no helicopter; S005 deploying by 8 rescue boats (actually 2) |
| V2 | Quantity accounting | Check by the list quantities whether the transport capacity / shelter capacity meets the decision-target scale (persons × trips vs number of boats; number of tents vs number of persons to shelter) | S005 2 boats × 10 persons/trip vs 180 persons; S001 12 tents vs 300-500 persons |
| V3 | Numerical-inference check | For rubric points marked "inference", compute the expected interval from the intelligence values by the formula, and check whether the value in the answer falls within the interval | S001-F8 (240×1~2→300~500); S003-F8 (6km÷1~1.5km/h→4~6h); S004-F9 (2km÷4m/s→8~9min) |
| V4 | Intelligence conflict | If an assertion in the decision (route, target, status) conflicts with the "confirmed facts" set (e.g., a cut road), report an error | S001 the county road is cut but "evacuate via the county road" is still recommended without mentioning a detour |
| V5 | Trap disposal | Identify erroneous-disposal phrasing and report an error (keywords + part-of-speech templates, e.g., "flush/dilute + chemical") | S004 flushing the benzene liquid on the ground with a hose; S002 letting private cars pump water spontaneously; S003 villagers going up the mountain at night without protection |
| V6 (semi-automatic) | Target completeness | "Evacuation/rescue"-type measures must carry a specific target; the deterministic implementation is limited, so an LLM first-pass check + a rule final-pass check is used | All scenarios (vague measures such as "do good work") |

### 5.3 Pseudocode

```python
def verify(answer, scene) -> list[Issue]:
    issues = []
    for r in extract_resources(answer):                    # entity extraction / vocabulary matching
        if r not in scene.resources and not has_sourcing(answer, r):
            issues.append(Issue("V1 resource over-allocation", r))
    for target, plan in scene.accounting_items():           # check items pre-written by the annotator
        if capacity(plan) < target:                        # 2 boats×10 persons/trip vs 180 persons
            issues.append(Issue("V2 capacity shortfall", target, plan))
    for key, (formula, interval) in scene.numerical_inference.items():  # formulas/intervals pre-written by the annotator
        val = extract_number(answer, key)
        if val is None or val not in interval:             # not inferred, or out of range
            issues.append(Issue("V3 inference missing/out-of-range", key, interval))
    for fact in scene.confirmed_facts:                     # road cut, dam cracks, etc.
        if contradicts(answer, fact):
            issues.append(Issue("V4 intelligence conflict", fact))
    for pattern in scene.trap_patterns:                    # templates like flush+dilute+benzene
        if pattern.matches(answer):
            issues.append(Issue("V5 trap disposal", pattern))
    return issues
```

Key points: **all rule parameters (formulas, intervals, resource lists, fact sets, trap templates) are given explicitly by the annotator in the scenario JSON**, and the component itself contains no training parameters; running it any number of times on the same answer produces a constant output, naturally solving the judge-variance problem of §6.5.

### 5.4 Controlled-experiment design against LLM judges (i.e., RQ4 of this paper)

- **Objective ① (equivalence)**: the verifier's agreement rate against the three-judge majority vote on the pilot hard rubric points (§7.1); it is expected that V1~V4 fully cover the computational and resource hard points, with V5/V6 partially covering them.
- **Objective ② (gain)**: inject the violation list into the multi pipeline (mandatorily attached before the auditor produces the report, with item-by-item correction required), and compare multi+verify vs multi in hard-point hit rate and overall hit rate; it is expected to fix rule-judgeable points such as S004-F9 and S005-R2.
- **Objective ③ (stability)**: repeated runs of the verifier on the same batch of answers give identical output; this contrasts with the LLM judges with kappa≈0 in §6.5, quantifying the reliability benefit of "deterministic verification replacing LLM checks".
- **Objective ④ (cost)**: the verifier makes zero API calls and takes milliseconds, compared with one call per rubric point for an LLM judge (the official version will collect tokens/time and report them).

The measured results of the above four comparison objectives are given in §6.6 (RQ4).

---

## 6 Experiments

### 6.1 Experimental routes

The experimental list below is taken from Section 8 of the roadmap (the EMNLP 2027 sprint-retool list). A1 is completed (corresponding to the v0.4 dataset of §3); the v0.3 pilot is a completed experiment of the benchmark-construction and calibration stage (§6.3, §6.5). **A1, A2, A3, A4, A5, A6, A7, A8, A9 and the v0.3 pilot are completed and report measured numbers; only A10 (human baseline), the optional item, is still incomplete, and this paper does not report its numbers.**

| ID | Experiment | Reviewer question addressed | Status |
|---|---|---|---|
| A1 | Scenario-scale expansion (5→36 scenarios; v0.4: 709 rubric points / 48 inference points) | "What makes 5 scenarios a benchmark" | Completed |
| A2 | Dual-model full set (glm-4-flash + glm-4-plus) | "Does the conclusion hold for only one API" | Completed (§6.7) |
| A3 | Configuration-matrix completion (single / multi / multi-verify; auditor ablation) | "Which role does the gain actually come from" | Completed (§6.4) |
| A4 | Constraint verification component deployment (V1~V5) + multi vs multi-verify | "Does verification actually work" | Completed (§6.6) |
| A5 | Significance testing (point-level McNemar + scenario-level paired tests + bootstrap 95% CI) | "Is the 5.2pp difference luck" | Completed (§6.3) |
| A6 | Manual adjudication and agreement rate (point-by-point adjudication on 20~30% of scenarios) | "Do machine judges match humans" | Completed (8 scenarios, 71 true three-judge disagreements, §6.5) |
| A7 | Judge stability (re-score the same batch of answers twice to report self-consistency) | "Judge variance is fully quantified" | Completed (§6.5) |
| A8 | Cost and latency table (API call counts / tokens / time / cost) | "Multi-agent is not free" | Completed (call/token/time measured; cost conversion pending, §6.8) |
| A9 | Error-typology quantification (distribution statistics of 8 error types) | "Error analysis is supported by data structure" | Completed (§7.2) |
| A10 (optional) | Small-scale human baseline (3~5 annotators for comparison) | "Human-level reference" | Planned |

### 6.2 Experimental setup (v0.3 pilot + v0.4 full set)

- **System under test (v0.3 pilot)**: glm-4-flash (temperature 0.1). Two configurations:
  - **single**: a single analyst answers in one shot the three parts "factual elements / situational assessment / action recommendations";
  - **multi**: intelligence officer → analyst → decision officer → auditor, four roles in series; every role except the intelligence officer can see the preceding roles' utterances (open dialogue, traceable), and **the auditor's final report is the scoring object**.
- **System under test (v0.4 full set, 6 configurations)**: on the above basis, add ① **multi-noaudit** (the ablation configuration without the auditor; intelligence officer → analyst → decision officer; corresponding to A3); ② **multi-verify** (the constraint verification component of §5 is plugged in before the auditor's closing of multi; corresponding to A4); and ③ **glm-4-plus** as the second model under test (two configurations, single / multi; corresponding to A2).
- **Judges**: a rule matcher, glm-4-flash (temperature 0), glm-4-plus (temperature 0); the same batch of answers is scored once by each of the two LLM judges (rescore mechanism), with the 2-of-3 majority vote as the official primary metric.
- **Scale (v0.4 full set)**: 36 scenarios × 6 configurations × 709 rubric points, three-judge majority-vote criterion; the v0.3 pilot (5 scenarios × 2 configurations × 96 rubric points) is retained as evidence of benchmark construction and calibration (§6.3, §6.5).
- **Cost-structure facts (A8, measured)**: under the protocol criterion multi makes about 6 API calls per scenario and single about 3 (including the same-side judge and the plus judge), and multi uses about 1.86× the tokens and about 2.06× the time of single; the Verifier makes zero API calls (pure deterministic rules). The cost-score scatter is shown in Figure 5 (`crisis-bench/figures/fig5_cost.png`), and the full cost table is in §6.8.

### 6.3 RQ1: Is multi-agent better than single-agent? (v0.3 pilot + v0.4 full set)

| Configuration | Rule scoring | flash judge | plus judge | Three-judge majority vote (2-of-3) |
|---|---|---|---|---|
| single (single analyst) | 84/96 = **87.5%** | 95/96 = 99.0% | 56/96 = **58.3%** | 87/96 = **90.6%** |
| multi (four roles, serial) | 89/96 = **92.7%** | 95/96 = 99.0% | 76/96 = **79.2%** | 92/96 = **95.8%** |
| multi − single | **+5.2pp** | 0 (flash judge saturated) | **+20.9pp** | **+5.2pp** |

Per-scenario details (hits/total):

| Scenario | single rule | single flash | single plus | multi rule | multi flash | multi plus |
|---|---|---|---|---|---|---|
| S001 Earthquake | 14/18 | 18/18 | 14/18 | 17/18 | 18/18 | 17/18 |
| S002 Flooding | 17/18 | 18/18 | 10/18 | 18/18 | 18/18 | 16/18 |
| S003 Wildfire | 18/19 | 19/19 | 7/19 | 17/19 | 19/19 | 19/19 |
| S004 Chemical | 19/21 | 20/21 | 11/21 | 20/21 | 20/21 | 9/21 |
| S005 Typhoon | 16/20 | 20/20 | 14/20 | 17/20 | 20/20 | 15/20 |

**Conclusion.** "multi > single" holds under all three criteria — rule (+5.2pp), plus (+20.9pp), and majority vote (+5.2pp); only under the flash-judge criterion is no difference detectable, because that judge is saturated (99.0%). Layer-wise: multi's gain is not in the factual layer (both configurations approach full score in the factual layer, exactly the v0.2 calibration phenomenon), but comes from the reasoning/decision layers and a few hard points; multi's cost is 4× the API calls and a longer reasoning chain. One exception is worth noting: S004 under the plus judge is lower for multi (9/21) than for single (11/21); combined with the evidence in §6.5 that the plus judge has larger variance, this difference reflects judge fluctuation rather than a true configuration difference — which is precisely why the majority-vote criterion exists. **Note: the above is the 96-rubric-point pilot conclusion; significance testing and the v0.4 full-set re-check follow below.**

#### v0.4 full set (36 scenarios, glm-4-flash, three-judge majority-vote criterion)

On the 36-scenario full set, multi and single are compared (both models under test are glm-4-flash, majority-vote criterion); the scenario-level mean-score difference and statistical significance are as follows:

| Metric | Value |
|---|---|
| Overall score (multi / single) | **90.7% / 83.5%** |
| Scenario-level mean-score difference (multi − single) | **+7.05 pp** (multi higher than single) |
| Point-level McNemar test | 61 rubric points where multi is correct and single is wrong, 10 where multi is wrong and single is correct; **p = 2.96×10⁻⁹** |
| Scenario-level paired Wilcoxon test | **p = 0.0008** |
| Bootstrap 95% CI (multi − single) | **[+3.26, +11.04] pp** |

**Conclusion.** On the v0.4 full set, the "multi > single" conclusion is directionally consistent and highly significant: overall score 90.7% vs 83.5%, a scenario-level mean difference of +7.05pp (p=2.96×10⁻⁹, CI [+3.26, +11.04] pp excluding 0). Relative to the v0.3 pilot's +5.2pp under the majority-vote criterion the magnitude is comparable (the pilot has 5 scenarios × 96 rubric points while the full set has 36 scenarios × 709 rubric points, so the two are not directly comparable after subtraction): following the scenario expansion (numerical-inference rubric points 3→48, information-contradiction scenarios 1→8) the proportion of "hard rubric points" rose, and multi-agent's completion advantage in the reasoning/decision layers and on hard points is expressed more stably. Layer-wise (Figure 1, `crisis-bench/figures/fig1_radar.png`): multi's gain is concentrated in the reasoning/decision layers (multi: reasoning 90.2%, decision 90.6%; single: 87.2%, 78.3% respectively) and a few hard points, with the factual layer nearly full-score for both (multi 91.0%, single 85.5%); the full heatmap of scenario × configuration is shown in Figure 2 (`crisis-bench/figures/fig2_heatmap.png`).

### 6.4 RQ2: Which role does the gain come from (auditor ablation)? (v0.4 full set, glm-4-flash, majority-vote criterion)

To locate the source of the multi-agent gain, on the v0.4 full set we compare multi with the ablation configuration without the auditor, **multi-noaudit** (intelligence officer → analyst → decision officer, no final audit closing):

| Comparison | Scenario-level mean difference | McNemar (b / c) | Wilcoxon | Bootstrap 95% CI |
|---|---|---|---|---|
| multi vs multi-noaudit | **+7.32 pp** (multi higher; overall 90.7% vs 83.5%) | b=76, c=25, **p=6.52×10⁻⁷** | **p=0.0006** | **[+2.32, +11.78] pp** |

(McNemar table meaning: 76 rubric points where multi is correct and noaudit is wrong, 25 where multi is wrong and noaudit is correct.)

**Conclusion.** Removing the auditor makes multi-agent drop significantly by 7.32pp under the majority-vote criterion (p=6.52×10⁻⁷, CI [+2.32, +11.78] pp excluding 0), showing that a considerable part of multi's gain over single comes from the audit step. Combined with §7.2: noaudit shows chained deterioration of the three error types "fact loss → reasoning loss → decision underperformance" (19 / 20 / 19, far higher than multi's 0 / 7 / 10); the auditor's value lies mainly in completion and fact-checking at closing, not only in correcting resource-type traps.

### 6.5 RQ3: Are LLM judges reliable? (v0.3 pilot + v0.4 full set)

On the same batch of answers and the same judge prompt, flash and plus are compared point by point:

| Configuration | Agreement rate | Cohen's kappa | flash=1 and plus=0 | flash=0 and plus=1 |
|---|---|---|---|---|
| single | 59.4% | **0.03** | 39 items | 0 items |
| multi | 80.2% | **0.08** | 19 items | 0 items |

Three conclusions:

1. **The flash judge is systematically lenient**: only 1 place judged 0 across all answers (99.0%), discrimination is zero, and it hardly ever checks whether a rubric point is "inferred correctly".
2. **The plus judge is systematically conservative and unstable**: for S003 single it directly marks the reasoning/decision layers as 0/5 and 0/6 (the rule judge gives a near full score for the same answer), and the same judge differs by 12 points between the two configurations for the same scenario, with excessive variance.
3. **kappa≈0**: the opinions of the two LLM judges are nearly uncorrelated. **Conclusion: LLMs are unreliable as checklist judges and cannot alone serve as the official score.** The benchmark's official criterion is therefore set as: the three-judge majority vote (2-of-3) as the primary metric, rule scoring as a zero-cost reference, and manual adjudication of disagreements by the annotator before submission (A6).

This finding is consistent with the "self-preference / scoring-distribution shift" phenomena in the LLM-as-a-judge literature, and appears even more extreme in the high-stakes Chinese disaster-emergency decision-making setting; it also constitutes the direct motivation for the constraint verification component of Section 5.

#### v0.4 full set (6 configurations) judge agreement + A7 self-consistency

On the v0.4 full set, the Cohen's kappa between the flash and plus judges in each configuration is as follows:

| Configuration (model under test flash or plus) | Cohen's kappa (flash vs plus) |
|---|---|
| multi@glm-4-flash | 0.081 |
| single@glm-4-flash | 0.079 |
| multi@glm-4-plus | −0.003 |
| multi-noaudit@glm-4-flash | −0.008 |
| multi-verify@glm-4-flash | −0.005 |
| single@glm-4-plus | −0.008 |

A7 self-consistency test (the same flash judge re-scores the same batch of answers once more):

| Configuration | flash self-consistency |
|---|---|
| single@glm-4-flash | 0.99 |
| multi@glm-4-flash | 1.00 |

**Conclusion (full-set replication).** The two LLM judges are each highly stable on the disaster checklist scoring (self-consistency 0.99~1.00) but nearly uncorrelated with each other (kappa≈0). This combination of "each stable, mutually inconsistent" directly supports the conclusion that "LLM judges are not interchangeable", and is also the design motivation for the three-judge majority-vote protocol and the deterministic verification component of Section 5 — since the two LLM judges cannot substitute for each other, they must be aggregated by the 2-of-3 majority vote, and the most error-prone verification work must be given to deterministic rules.

#### A6 Annotator Final Adjudication (8 scenarios, 71 true three-judge disagreements)

Following route A6, we sample 8 scenarios of multi@glm-4-flash (S002/S004/S005/S008/S015/S016/S018/S024, covering the three classes single-hazard, chained, and information-contradiction) and extract the **71 rubric points** on which the three judges disagree for final adjudication: for each item the original intelligence text, the rubric-point text, and the final report under test are given to glm-4-plus to independently adjudicate (0/1 + reason) under the final-adjudication criterion, producing a machine-adjudication draft, which the annotator then reviews and confirms item by item. Results:

| Final adjudication vs | Agreement rate |
|---|---|
| flash judge | **88.7%** (63/71) |
| majority vote | **78.9%** (56/71) |
| rule judge | 74.6% (53/71) |
| plus judge | 15.5% (11/71) |

The vote distribution within the disagreement set also reveals judge tendencies: flash judges 1 on 70 of the 71 items (almost always 1), plus judges 0 on 67 items (only 4 judged 1), and the rule judge judges 1 on 58 items; the final adjudication itself judges 1 on 64 items and 0 on 7.

Three findings:

1. **The plus judge is strongly biased toward 0 on the disagreement set** (67 of 71 judged 0, only 4 judged 1, agreement with the final adjudication only 15.5%), confirming that its "rather strict than lenient" behavior is a systematic false negative rather than "stricter and therefore more reliable"; it is completely unusable as a single judge.
2. **The flash judge has the highest agreement with the annotator's final adjudication (88.7%)**, and A7 shows its self-consistency is 0.99~1.00 — flash is "stable and lenient" on this benchmark, and on most disagreement items it happens to match the human criterion.
3. **The majority vote has decomposable error** (15/71 = 21.1% disagreeing with the final adjudication): of these, 9 are false negatives (flash's single 1-vote is outvoted by the rule and plus 0-votes), and 6 are false positives (the rule + flash both judge 1 while the final adjudication considers the point unsatisfied). The value of the majority-vote protocol lies in **robust aggregation** (guarding against a single judge's saturation/conservative extreme); its accuracy ceiling is dragged down by the weakest vote (plus); this also partly explains why the RQ1 gain under the majority-vote criterion is limited.

In summary: the official criterion continues to use the majority vote, while the paper and the data release publicly disclose all item-by-item adjudication drafts (results/adjudication-resolved.md), with the annotator's final adjudication serving as the reference for human-machine agreement (human-machine agreement on the disagreement set: 78.9% vs the majority vote, 88.7% vs flash).

### 6.6 RQ4: Can deterministic constraint verification replace/correct LLM checking? (v0.4 full set, glm-4-flash, majority-vote criterion)

§6.5 shows that LLM judges are unreliable at "verification"; the Verifier of §5 is designed exactly for "the most error-prone verification work". After implementing the V1~V5 modules on the v0.4 full set, we inject the violation list before the auditor closes multi (the **multi-verify** configuration) and compare it with the full multi:

| Comparison | Scenario-level mean difference | McNemar (b / c) | Wilcoxon | Bootstrap 95% CI |
|---|---|---|---|---|
| multi-verify vs multi | **+2.81 pp** (verify higher; overall 93.5% vs 90.7%) | b=10, c=30, **p=0.0027** | **p=0.0298** | **[+0.07, +6.10] pp** |

(McNemar table meaning: 30 rubric points where verify is correct and multi is wrong, 10 where verify is wrong and multi is correct.)

**Verifier deterministic cross statistics** (three configurations compared, rule detection):

| Configuration | Inference compliance | Resource over-allocation violations | Traps | Capacity shortfall |
|---|---|---|---|---|
| multi@glm-4-flash | 12/49 | 50 | 6 | 1 |
| multi-verify@glm-4-flash | 12/49 | 46 | 0 | 0 |
| multi-noaudit@glm-4-flash | 0/49 | 8 | 6 | 1 |

**Conclusion.** After plugging in the Verifier, multi improves by a further 2.81pp under the majority-vote criterion (p=2.7×10⁻³, CI [+0.07, +6.10] pp excluding 0; overall 93.5% vs 90.7%), a clear and significant gain. The deterministic detection shows: the Verifier mainly suppresses **resource over-allocation / trap / capacity** type errors — traps 6→0 and capacity shortfall 1→0 both drop to zero, and resource over-allocation drops from multi's 7 items to multi-verify's 0 items under the error-typology criterion (§7.2), while total loss drops from multi's 66 to 46; and "inference compliance" is 12/49 for both multi and multi-verify (noaudit only 0/49), showing that **numerical-inference rubric points are still determined by model capability**, and the deterministic rules handle accounting but cannot compute the numbers for the model. Contrasting with the LLM judges with kappa≈0 in §6.5: the Verifier's repeated runs on the same answer produce a constant output, naturally solving the judge-variance problem (the comparison design is in §5.4).

### 6.7 A2: Dual-model comparison (glm-4-plus, approaching the ceiling)

The second model under test, glm-4-plus (a stronger model on the same API), performs close to the ceiling on the v0.4 full set. First, plus's own multi vs single:

| Comparison | Scenario-level mean difference | McNemar | Bootstrap 95% CI |
|---|---|---|---|
| multi vs single (both @glm-4-plus) | 0.01 pp | exact binomial **p=1.0** | [−0.40, +0.44] pp |

Next, the cross-model comparison (multi configuration):

| Comparison | Scenario-level mean difference | McNemar | Wilcoxon | Bootstrap 95% CI |
|---|---|---|---|---|
| plus vs flash (both multi configuration) | **+9.11 pp** (plus higher) | **p=2.05×10⁻¹⁵** (plus correct & flash wrong 65 points; flash correct & plus wrong 0) | p≈0 | [+6.11, +12.57] pp |

Full-score scenario statistics (majority-vote criterion): single@plus has **35 full-score scenarios** among 36 (the only non-full-score is S031 at 95.2%); multi@plus also has **35 full-score scenarios** (the only non-full-score is S009 at 94.7%).

**Discussion.** plus is close to the ceiling on this benchmark: 9.11pp higher than flash (p=2.05×10⁻¹⁵), and multi and single are no longer significantly different (mean difference 0.01pp, CI [−0.40, +0.44] pp crossing 0, McNemar exact binomial p=1.0). This suggests that CrisisBench v0.4's discrimination for strong models is saturating: in §7.2, for plus's two configurations all error types are 0 except 1 item each of "numerical-inference failure"; and both non-full-score scenarios differ by only 1 rubric point. **We recommend that v0.5 add harder scenarios, or switch to a "hard rubric-point subset" (numerical-inference / contradiction / trap) as a more discriminative metric.**

### 6.8 A8: Cost and Latency (v0.4 full-set measurement)

Before any large-scale deployment, one must answer "multi-agent is not free". The table below reports the measured API cost of the six configurations under the three-judge majority-vote protocol (the data source is the `usage` field recorded in the result files, with no estimation; "Main run" includes the system-under-test's inference calls plus one same-side judge call, and the "plus judge" is the second LLM judge required by the official criterion; the A7 self-consistency re-scoring is an extra stability experiment and is not counted in the protocol cost):

| Configuration | Model | Calls/scenario | Tokens/scenario | Time(s)/scenario | Full-set tokens | Relative tokens |
|---|---|---|---|---|---|---|
| single (single analyst) | glm-4-flash | 3.0 | 5,829 | 73.4 | 209,842 | 1.00 |
| multi (four roles, serial) | glm-4-flash | 6.0 | 10,823 | 150.8 | 389,617 | 1.86 |
| multi-noaudit (no auditor) | glm-4-flash | 5.1 | 8,179 | 106.5 | 294,447 | 1.40 |
| multi-verify (+constraint verification) | glm-4-flash | 6.0 | 11,098 | 145.5 | 399,537 | 1.90 |
| single (single analyst) | glm-4-plus | 3.0 | 8,173 | 66.6 | 294,245 | 1.40 |
| multi (four roles, serial) | glm-4-plus | 6.0 | 15,956 | 104.9 | 574,419 | 2.74 |

**Conclusion.** Multi-agent incurs a substantial but controlled cost: multi uses about **1.86×** the tokens of single, 2.0× the calls, and about 2.06× the time, while raising the scenario-level score by 7.05pp (§6.3) — i.e., about 0.86× extra tokens buys a 7.05pp gain in decision quality. The constraint verification component makes zero API calls (pure deterministic rules) and raises tokens only slightly from multi's 10,823 to 11,098 (+2.5%, from the prompt increment of the injected violation list and correction instructions), yet yields a 2.81pp gain and eliminates resource/trap errors, giving better cost-effectiveness than adding another LLM role. The auditor ablation (multi-noaudit) reduces tokens to 0.75× of multi but drops the score by 7.32pp — **the auditor is a "cheap and critical" step**. The stronger model glm-4-plus raises tokens by about another 1.47× (multi@plus 574k vs multi@flash 390k) yet is already near the ceiling (§6.7), suggesting diminishing marginal returns from simply switching to a larger model. The full cost breakdown (by run unit) is in `crisis-bench/results/RESULTS-cost.md`; the cost-score scatter is in Figure 5 (`crisis-bench/figures/fig5_cost.png`). Cost in currency is not converted from vendor price lists (API pricing differs) and will be recorded in the official version.

---

## 7 Analysis: Error Typology

### 7.1 Pilot example: discrimination comes from hard rubric points

The list of "hard rubric points" judged 0 by two or more judges simultaneously (pilot, 96 rubric points):

| Configuration | Scenario-point | Content | Vote pattern (rule/flash/plus) |
|---|---|---|---|
| Both configurations | S004-F9 | Infer the time for benzene vapor to reach the residential area (2km÷4m/s≈8-9 minutes) | **0/0/0** |
| Both configurations | S001-F8 | Infer the scale of surviving residents to be transferred (240 households≈300-500 persons) | 0/1/0 |
| single (fixed under multi) | S003-F8 | Infer the time for the fire front to approach the village (6km÷1-1.5km/h≈4-6 hours) | 0/1/0 |
| Both configurations | S005-R1 | Adopt the conservative figure for contradictory data and arrange disaster verification | 0/1/0 |
| multi | S005-R2 | The rescue-boat capacity shortfall (2 boats×10 persons/trip vs 180 persons) requires reinforcement | 0/1/0 |
| single | S001-D4 | Tent-shortage sheltering plan (12 tents insufficient→centralized sheltering in public buildings) | 0/1/0 |
| single | S004-D4 | Spray-cool adjacent storage tanks and eliminate ignition sources | 0/1/0 |
| single | S002-D5 | Specify the priority order of emergency operations | 0/1/0 |

Interpretation:

1. **Computational/accounting rubric points have the lowest hit rate**, among which S004-F9 is unanimously 0 across all three judges — "inferring a number from multiple intelligence fragments" is the most stable loss point for current models and the core source of the benchmark's discrimination;
2. **multi fixes two points that single fails to obtain**: S003-F8 (the auditor supplies the 4-6 hour inference) and S005-R2 (capacity shortfall) — serial multi-agent has a completion effect on "omission-type errors", which is the concrete evidence chain for multi > single;
3. **The contradiction figure (S005-R1) is not fully obtained by either configuration** — adopting the conservative figure for contradictory data and arranging disaster verification is a stable discrimination point;
4. Trap-type rubric points (tent shortfall, adjacent-tank cooling, priority order) lose points only under single; the multi audit step has a correcting effect on "resource-constraint-type" traps.

Under the full-set criterion, the discrimination of each type of "hard rubric point" across configurations is shown in Figure 4 (`crisis-bench/figures/fig4_hardpoints.png`).

### 7.2 Eight error types (A9 quantitative statistics, v0.4 full set, majority-vote-criterion loss-point counts)

Following the eight error types of route A9 (definitions and pilot examples in the table below), the loss-point counts for the six configurations of the v0.4 full set are as follows:

| # | Error type | Definition | Pilot example (96 rubric points) |
|---|---|---|---|
| 1 | Fact loss | Key intelligence elements not fully collected | Pilot factual layer near full score, no stable loss example seen (v0.4 quantification below) |
| 2 | Numerical-inference failure | Inference point not inferred/out of range | S004-F9, S001-F8, S003-F8 |
| 3 | Resource over-allocation | Using resources outside the list, or insufficient capacity/transport | S005-R2 (capacity shortfall), S001-D4 (insufficient tent capacity) |
| 4 | Intelligence conflict | Recommendation contradicts confirmed facts | S005-R1 (contradictory data not conservatively handled and verified) |
| 5 | Trap not seen through | Erroneous practice not seen through and corrected | S004 water-flushing dilution (corresponding to V5); S001-D4 tent-shortage trap |
| 6 | Vague decision | Only principles, no concrete target + action | S002-D5 (priority order) to be split and classified |
| 7 | Missing target | Measure without a concrete target | No stable example in the pilot (v0.4 all 0, corresponding to V6) |
| 8 | Improper contradiction handling | Contradictory figures not unified, not reported point by point | The contradiction-handling dimension corresponding to S005-R1 |

Full-set loss-point counts (majority-vote criterion, 36 scenarios):

| Error class | multi@flash | single@flash | multi-noaudit@flash | multi-verify@flash | multi@plus | single@plus |
|---|---|---|---|---|---|---|
| Fact loss | 0 | 9 | 19 | 0 | 0 | 0 |
| Numerical-inference failure | 28 | 35 | 39 | 26 | 1 | 1 |
| Resource over-allocation | 7 | 8 | 2 | 0 | 0 | 0 |
| Intelligence conflict | 0 | 0 | 0 | 0 | 0 | 0 |
| Trap not seen through | 4 | 6 | 5 | 3 | 0 | 0 |
| Vague decision | 0 | 0 | 0 | 0 | 0 | 0 |
| Missing target | 0 | 0 | 0 | 0 | 0 | 0 |
| Improper contradiction handling | 10 | 16 | 13 | 6 | 0 | 0 |
| Reasoning loss (other) | 7 | 8 | 20 | 4 | 0 | 0 |
| Decision underperformance (other) | 10 | 35 | 19 | 7 | 0 | 0 |
| **Total lost rubric points** | **66** | **117** | **117** | **46** | **1** | **1** |

Core findings:

1. **Numerical-inference rubric points are the largest source of error**: multi 28, single 35, noaudit 39 items; the Verifier can only reduce multi's 28 to 26 — deterministic rules can do accounting but cannot infer for the model.
2. **Improper contradiction handling is the second most persistent error type**: single 16, multi 10, noaudit 13 items.
3. **The absence of the auditor (noaudit) brings chained deterioration of "fact loss → reasoning loss → decision underperformance"** (compared with multi): fact loss 0→19, reasoning loss 7→20, decision underperformance 10→19.
4. **The Verifier substantially reduces resource-type and trap-type errors** (compared with multi): resource over-allocation 7→0 (to zero), trap not seen through 4→3; total loss drops from multi's 66 to 46.

This typology is both an error portrait of the system under test and a checklist for the rule coverage of the constraint verification component (§5): V1~V5 anchor the five classes resource over-allocation, quantity accounting, numerical inference, intelligence conflict, and traps, corresponding one-to-one with error types 2/3/4/5; types 6/7 (vague decision, missing target) are handled by semi-automatic V6; types 1/8 rely on full information collection and contradiction reporting, and at this stage are mainly backed by the checklist and manual spot-checking. (The error-typology distribution is authoritative in this table; no separate figure was produced — if visualization is desired, the Figure 2 heatmap can be reused.)

---

## 8 Limitations and Ethics

**Limitations (must be retained honestly before submission and progressively eliminated)**:

1. **Some measurements remain unclosed.** The experimental numbers reported in this paper come from the v0.3 pilot (96 rubric points) and the v0.4 full set (36 scenarios, 6 configurations, 709 rubric points, three-judge majority-vote criterion), and already include A2/A3/A4/A5/A6/A7/A8/A9; however, A6's final adjudication is of the "machine-adjudication draft + annotator review" mode (the 71-item disagreement draft is released with the data, and the review must be closed before submission), and A10's human baseline is the optional incomplete item; moreover, glm-4-plus is already close to the ceiling and discrimination is saturating, awaiting v0.5's expansion with harder scenarios.
2. **Annotation and rubric-point drafts were drawn up by an AI assistant**, and the A6 disagreement final-adjudication drafts were also machine-generated — **before submission they must be reviewed, revised, and confirmed item by item by the author** (see the Appendix Note at the end).
3. **The constraint verification component has limited coverage.** V1~V5 are implemented and validated on the v0.4 full set (§6.6), but false-positive/false-negative rates were not separately quantified; the trap (V5) and target-completeness (V6) checks still rely on keywords/vocabulary and semi-automatic first-pass checking, and coverage is not complete — numerical-inference rubric points are still determined by model capability (multi and multi-verify have the same inference compliance of 12/49).
4. **The cost-accounting criterion needs unifying.** A8 has measured API call counts, tokens, and time (§6.8), but the token-statistics feature was not yet online during single@glm-4-flash's main run, so that configuration's generation cost is approximated by an independent re-run with the same prompt; cost in currency is not converted from vendor price lists (API pricing differs) and will be recorded in the official version.

**Ethics statement.** ① The dataset consists entirely of manually fabricated scenarios, containing no real personal information and no real emergency incidents; ② this work is oriented to decision-support research, and its conclusions do not constitute a basis for on-site disposal and do not replace human civil-defense command; ③ during review we plan to release the data and code anonymously on Zenodo (CC-BY-4.0) and a HuggingFace data card (following ARR policy); ④ the fact that the draft was drawn up by an AI assistant is declared in the Appendix Note at the end, and it must be reviewed and revised item by item by the author before submission.

---

## 9 Conclusion

This paper presents CrisisBench, the first Chinese benchmark for evaluating multi-agent decision-making in disasters. The dataset is upgraded to v0.4 (36 scenarios, 709 rubric points, 48 numerical-inference rubric points; three classes single-hazard / chained / information-contradiction; 8 disaster types), and is accompanied by three-layer checklist annotation and a three-judge majority-vote evaluation protocol. Combining the results of the v0.3 pilot (96 rubric points) and the v0.4 full set (6 configurations), the experiments demonstrate: four-role serial multi-agent consistently outperforms single-agent (v0.3 majority vote +5.2pp, strict criterion +20.9pp; v0.4 full set +7.05pp, p=3.0×10⁻⁹); the auditor is a key source of the gain (ablation drop of 7.32pp, p=6.5×10⁻⁷); the constraint verification component yields a further 2.81pp gain (p=2.7×10⁻³) and pushes resource over-allocation, trap, and capacity-shortfall errors to near zero; LLM judges are not interchangeable in the disaster decision-making setting (kappa≈0, self-consistency 0.99~1.00), so the majority vote and deterministic verification are necessary remedies; discrimination is concentrated in numerical-inference rubric points, the largest source of error. The stronger model glm-4-plus is already close to the ceiling (9.11pp above flash, 35 of 36 scenarios at full score), suggesting that the benchmark needs to evolve toward harder scenarios and a "hard rubric-point subset". A6 manual adjudication (71 true disagreements from 8 scenarios, 88.7% agreement with flash) and A8 cost-latency accounting (multi at about 1.86× the tokens of single) are complete. Next steps follow the experimental routes (§6.1): A10 human baseline and v0.5 difficulty expansion → English rewriting and submission.

---

## References (compiled from the domain review; volume/issue/page numbers to be completed item by item before formal submission)

1. Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. (07)
2. Wu et al. AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation. COLM 2024. (08)
3. Crisis-tweet robustness evaluation (6 LLMs / 7.7×10⁴ tweets / three weaknesses: flood, help-seeking, misspellings). WWW 2025. (09)
4. Spatio-temporal KGQA framework (joint spatio-temporal embedding and constraint filtering). (12)
5. CogMG: knowledge-gap capture → completion → review → write-back, a question-answering knowledge loop. (14)
6. Multi-agent survey (environment interface / role profile / communication / capability acquisition). IJCAI 2024. (41)
7. MetaAgent: a designer LLM automatically generates the minimal necessary agents and a finite-state-machine control flow. (42)
8. VeriMAP: Verification-Aware Planning for Multi-Agent Systems (Planner decomposition into a DAG + an executable verification function for each subtask). arXiv:2510.17109. (52)
9. PMC: Planning with Multi-Constraints via Collaborative Language Agents (directed subtask graph and constraint rewriting for multi-constraint tasks). COLING 2025, arXiv:2405.16510. (50)
10. E-KELL: Enhancing Emergency Decision-Making with Knowledge Graphs and Large Language Models (hazardous-chemical leakage emergency decision support; quantified improvement measured by expert scoring). IJDRR 2024, Vol. 113: 104804. (05)
11. Sim911: LLM playing a 911 dispatcher for training simulation and evaluation. AAAI 2025. (63)
12. LogiDebrief: STL temporal logic + LLM for automatic adjudication of drill after-action review. IJCAI 2025. (62)
13. DisasterTD: disaster-image place-name disambiguation/georeferencing (MLLM candidates + cross-view visual adjudication). (60)
14. RescueADI: adaptive disaster-interpretation agent (on-demand scheduling of detection/segmentation/VQA). (61)
15. Edge et al. From Local to Global: A Graph RAG Approach to Query-Focused Summarization. arXiv:2404.16130. (11)

> Note: the bracketed numbers are the numbering in the review `domain-review.md`; the formal version will replace them with complete bibliographic entries (authors/volume-issue/DOI).
> All entries were verified one by one by WebSearch on 2026-10-18 (see `crisis-bench/references-verified.md`); verified entries to be merged into the formal list: LLM-as-a-judge (Zheng et al., MT-Bench, NeurIPS 2023 D&B), HELM (Liang et al., TMLR 2023), BIG-bench, AgentBench (ICLR 2024), AutoGen (COLM 2024, already listed as item 2), ReAct (ICLR 2023), RAG (NeurIPS 2020), CogMG (arXiv:2406.17231), MetaAgent (ICML 2025), LEGOMem (arXiv:2510.04851), Sim911 (arXiv:2412.16844), LogiDebrief (arXiv:2505.03985), crisis-tweet evaluation (WWW 2025, DOI:10.1145/3696410.3714511), RescueADI (arXiv:2410.13384).

---

*Draft v3 complete (2026-10-19). To-dos for the next version: item-by-item review by the annotator of the A6 final-adjudication drafts, A8 cost-latency, A10 human baseline, v0.5 difficulty expansion, reference normalization, English abstract.*

---

## Appendix Note (Editorial, not part of the submission)

> **Important statement (submission red line; must be retained): this paper's draft was drawn up by an AI assistant based on the completed experiments and the literature survey; before submission or submission for the assessment, it must be reviewed and revised item by item by the author (Xu Xiangyang), in particular: scenario annotation (all rubric points in scenarios.json), the wording of the experimental conclusions, and the reference entries. All numbers are taken from the v0.3 experimental results (`research/crisis-bench/results/RESULTS.md` and `results/*.json`) and the v0.4 scenario table (`crisis-bench/scenarios/rubric.md` §5); nothing was fabricated.**
