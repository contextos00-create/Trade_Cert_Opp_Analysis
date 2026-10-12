# Plumbing exam data acquisition: an iterative workflow that produces usable content

Prepared October 11, 2026. Proposed process, not an implemented or executed pipeline.

Read alongside [the findings and feasibility report](PLUMBING_EXAM_DATA_ACCESS_ANALYSIS.md). This plan supplements the repository's [nationwide research design](https://github.com/contextos00-create/Trade_Cert_Opp_Analysis/blob/c9fad3b34545337d2401a913de5dd76415edd149/NATIONWIDE_US_TRADE_CERTIFICATION_BUILD_DOC.md); it narrows the next execution to plumbing and adds content acquisition, commercial rights, and question validation.

## 1. What the process is trying to obtain

**Goal:** assemble a verified, maintainable package for each specific plumbing exam, with enough lawfully usable material to produce original, jurisdiction-appropriate practice questions and mock exams.

Each package needs three independently tracked results:

1. **An exam specification:** the exact credential, regulator, exam owner, delivery provider, sections, timing, scoring, tested references and editions, topic distribution, and practical requirements.
2. **A usable content route:** original commissioned questions, licensed practice content, expressly reusable official samples, or an appropriate combination. Code text, tables, figures, and AI uses need their own rights review.
3. **A reviewed practice product:** questions with correct answers, explanations, exact source references, applicable jurisdiction/version, and reviewer approval.

A discovered URL does not satisfy any of these results by itself. A public guide is not a commercial redistribution license. A mock-test score is not yet a validated prediction of passing the official exam.

## 2. Use one exam package as the unit of work

Do not assign one agent “research ten states” and expect one complete dataset. Start with the ten-state inventory, then dispatch a separate job for each real credential and exam component.

**Required inputs**

- State and, when the credential is local, city/county or other licensing jurisdiction.
- Intended work/licensing location; residence can suggest a starting location but does not determine the exam.
- Official credential sought, or an instruction to discover the credential taxonomy first.
- Expected exam date and research cutoff date.
- Intended product uses: metadata summaries, question delivery, excerpts, diagrams, AI-assisted drafting/retrieval, translation, or other uses actually needed.
- Existing source ledger, accepted records, unresolved conflicts, and prior request outcomes.

**Identity:** jurisdiction + official credential + exam ID + component + reference/edition set + effective period. Keep titles such as contractor, journeyman, master, and qualifying party distinct. Keep a law's adopted code edition separate from the edition named by the exam owner.

## 3. Stages, outputs, and decision gates

| Stage | Work | Required output | Gate or next route |
|---|---|---|---|
| A. Inventory credentials | Establish state/local scope from official law and licensing pages; discover official levels and equivalent titles. | Credential inventory with evidence and unresolved local coverage. | If geography/credential remains ambiguous, queue that specific question before extracting an exam. |
| B. Resolve the exam | Follow the regulator's links to the owner and provider; distinguish written, business/law, practical, and specialty tests. | Exact exam/component IDs and authoritative source links. | Never substitute a national ICC exam or another state's bulletin without explicit acceptance evidence. |
| C. Retrieve source documents | Read already-discovered authoritative leads before making new broad searches; download permitted bulletins, outlines and reference lists. | Source ledger, document version/hash, extracted text, passage/page citations and retrieval outcome. | A search snippet, unread lead, or expired reference list remains unverified. |
| D. Extract exam facts | Extract section/topic weights, item counts, durations, score rules, reference editions, supplied tables, and practical expectations. | Structured exam specification; unknown fields remain null. | Material conflicts or missing tested editions prevent claiming exact simulation. |
| E. Map usable content | Classify every asset as metadata, sample, codebook/table/figure, practice bank, practical guidance, or performance data. | Content inventory with owner, access method and rights status. | Public visibility alone never produces “licensed for app use.” |
| F. Pursue acquisition | In parallel, prepare targeted board clarification, publisher licensing, prep-provider partnership, and original-authoring routes. | Request drafts, relevant contacts, requested uses, responses/agreements when received. | Unsent drafts and unanswered inquiries stay pending; a refusal moves to alternatives. |
| G. Build the topic map | Translate the official outline into learning objectives; link each objective to the applicable authoritative reference. | Coverage map with supported weights and missing sources. | Where weights are not published, mark the distribution as editorial; do not call it an official blueprint. |
| H. Author and review | Commission original items or import licensed items; independently verify answers, wording, calculations, diagrams and version scope. | Approved item bank plus revision/review history. | No unreviewed generation goes directly into scored mocks. |
| I. Assemble and test | Create forms following supported section weights and timing; test answer keys, scoring and version selection. | Form manifest, coverage reconciliation and test/review results. | Missing practical instruction or companion exams must be visible in scope. |
| J. Pilot and maintain | Observe usability, error reports and learning progress; later collect voluntary exam outcomes and refresh changed sources. | Pilot evidence, correction queue, new source versions and affected-item lists. | Expand only after the package passes its applicable gates. |

Stages E–F can advance while other exam facts are being resolved. Content production for a disputed edition waits for that dispute to be closed. A failure for one package must not discard accepted work elsewhere.

## 4. Targeted research loops

Use a proposed budget of **at most three total research passes per unresolved topic: the initial pass and up to two targeted retries**. This makes the existing nationwide document's three-round ceiling explicit. Each retry must try something different and record what changed.

1. **First pass:** fetch the regulator's exam page, linked provider bulletin, and exact reference list. Prioritize authoritative unread leads from the October 11 run.
2. **Second pass:** follow internal links, official archives and document indexes. Use an official vendor's alternate download or browser rendering when ordinary retrieval fails.
3. **Third pass:** compare authoritative versions and prepare a question for the responsible program office, or a narrowly scoped records request for publicly releasable material.

After the budget is exhausted, persist the package as partial and queue the smallest unresolved question. Resume when a new document, agency response, licensing offer, or scope decision arrives. Repeating a broad web search does not reset the budget.

Each gap record should contain: package ID, missing field, why it affects the app, attempted sources, competing values, next action, responsible organization, retrieval/access limitation, and evidence that would close it. A nonresponse means `awaiting_response`, not “data does not exist.”

Apply the runtime deadline in the controller as well as the prompt, checkpoint between tool calls, and report elapsed time and stop reason. Keep source-discovery count, documents actually read, supported fields, rights decisions, and accepted packages as separate measures.

## 5. Four acquisition routes to run in parallel

### Route 1: public exam specifications and expressly released samples

Start with the licensing agency and its named exam owner. Ask for the current exam ID, outline, topic distribution, reference list with editions, format rules, publicly releasable examples, and change notices. Ask whether samples can be reused in a paid app and who can authorize that use.

If public records procedures are useful, request nonconfidential blueprints, existing reference lists, releasable retired examples, and existing aggregate exam statistics. Do not assume active items are disclosable. An official Texas Attorney General decision explains the test-item exemption in Texas; other jurisdictions require their own assessment. [Texas Open Records Decision 626](https://www.texasattorneygeneral.gov/sites/default/files/ord-files/ord/2020/ord19940626.pdf).

**Success:** facts are verified, and sample reuse is authorized or samples remain external links. **Fallback:** original questions mapped to the verified outline.

### Route 2: code publishers and content licenses

ICC offers Code Connect, an integration route that requires implementation and content licensing agreements. Confirm the exact title/edition coverage and whether a consumer exam-prep app is an eligible use; published availability is not an offer accepted by this project. [ICC Code Connect](https://solutions.iccsafe.org/codeconnect).

Use ICC's published licensing contact (`license@iccsafe.org`) for the proposed uses; use its Code Connect contact for integration scope. For IAPMO, start with its official contact channel and request routing to the person responsible for UPC/state-code content permissions. Its website terms reserve content rights; an IAPMO membership or book purchase is not evidence of app redistribution permission. [ICC terms](https://www.iccsafe.org/about/terms-of-use/), [IAPMO terms](https://iapmo.org/terms-of-use).

Request decisions on the uses actually planned: commercial display, section excerpts, tables/figures, copying/storage, API/cache use, explanatory derivatives, translations, AI retrieval, AI model training, attribution, user limits, updates, and termination. Treat retrieval for drafting and training a model as distinct permissions.

**Success:** written terms cover the product's necessary uses at acceptable cost. **Fallback:** narrower excerpts if authorized, original explanations and diagrams, and links directing learners to their own reference materials; review the remaining uses as needed.

### Route 3: existing practice-content providers

Identify prep publishers, instructors, apprenticeship training programs, community colleges and trade associations that actually create relevant practice material. Ask whether they own it and can license it for digital delivery, editing, explanations and the selected jurisdiction/version. Do not infer that a provider owns official exam items because it sells a prep course.

Request an evaluation sample, coverage map, author/reviewer provenance, update policy, accessibility/translation terms, delivery format, commercial terms, and evidence of rights. Record a provider's refusal as a result, not a reason to scrape its paid course.

**Success:** an evaluated bank plus a suitable agreement. **Fallback:** commission original content from qualified instructors.

### Route 4: original question development

Recruit a qualified plumbing instructor or experienced licensed practitioner for the target jurisdiction. Contract for original writing, diagrams, review and the necessary rights. Exclude recalled live exam questions and material the author cannot license.

Use the verified topic map to draft a small formative set first—an illustrative 25–50 questions can test the authoring/review process, but does not establish full exam coverage. AI may assist with permitted source material and drafting; a qualified reviewer must verify each scored item.

For full mocks, ensure every scored topic has enough approved items to meet each form's allocation. A larger reserve bank helps reduce repetition; a possible planning target is four times the number of questions served in a full mock, allocated by topic. That is an editorial capacity target, not an official or psychometric requirement, and should be costed with the content team.

**Success:** a reviewed, original bank with complete applicable coverage. **Fallback:** release clearly scoped topic practice while closing remaining content gaps.

## 6. The next ten-state research queue

This queue reflects the supplemental checks described in the companion report. It is a starting order, not a claim that all exams in a state have been inventoried.

| Jurisdiction | Next concrete work | Evidence that closes the step |
|---|---|---|
| California | Package C-36 separately from worker credentials; collect the companion Law and Business specification if offering contractor prep. | Matching current guides, tested reference scope, and a rights/original-authoring route. |
| Texas | Replace the PSI written-exam attribution; reconcile the current Pearson handbook with older board prep guides and proposed code changes. | Dated exam-component specification or written TSBPE clarification on unresolved conflicts. |
| Florida | Retrieve the exact plumbing specialty outline, current reference list and Business and Finance specification; preserve drawing/session scope. | Current DBPR documents tied to the chosen exam date. |
| New York City | Package Master Plumber written and practical preparation; treat journeyman registration separately. | DOB/CPS HR current requirements and each component's scope. |
| Illinois | Turn the IDPH application and administrative rule into a written/practical specification. | Current code and administration details plus clarification of unpublished topic distribution. |
| Pennsylvania | Create separate Philadelphia and Allegheny packages; reconcile Philadelphia's exam references with its July 2026 code adoption; route Pittsburgh plumbing research to the county authority. | Written exam-edition transition confirmation and current local format evidence; no statewide generalization. |
| Ohio | Package the state plumbing contractor exam and Business and Law separately; discover local worker credentials in a separate lane. | Current board-linked PSI bulletin and the specific locality's evidence. |
| Georgia | Use the retrieved PSI 2026 appendix instead of the board's stale 2025 download; confirm the named Georgia amendments and obtain the next annual list before extending coverage beyond December 31, 2026. | The exact 2024 code/amendment package applicable on or after May 1, 2026 and the selected credential's book rules. |
| Washington | Confirm the exam page's 2015 UPC reference against the 2026 bulletin for the chosen classification. | Program confirmation or an updated authoritative edition statement; retain section-level sizing requirements. |
| Arizona | Select the actual ROC classification and its trade and Statutes and Rules training/exam components, plus solar where required; separately verify the Phoenix journeyman exam/version if targeting individual workers. | Matching ROC references or currently accepted local exam IDs, editions and vendor acceptance evidence. |

**Priority:** repair vendor/edition conflicts and consume authoritative unread leads first. Then obtain one complete worker-credential package and, if useful to the product, one separate contractor package. Carry the ten-state inventory forward without making the first pilot depend on nationwide completion.

## 7. Data contracts to add or revise

Reuse the nationwide build document's source, claim, evidence, conflict and coverage models. Extend them with these separate records; do not flatten everything into one state row.

- **Exam specification:** credential ID, licensing geography, component/exam ID, regulator, owner, provider, publication/effective dates, topic weights/counts, scored/unscored status if known, timing, score rule, tested editions, adopted-law editions, allowed/supplied references, practical scope, supported fields and unresolved conflicts.
- **Content asset:** owner, title/version, asset type, source/provenance, acquisition route, access status, rights status, permitted uses, restrictions, attribution, term/expiry, agreement reference and refresh policy. Unknown permissions stay unknown.
- **Practice item:** original/licensed provenance, topic/objective, applicable exam versions, prompt/options/answer, rationale, source section, author, reviewer/date, review status, calculations/diagram provenance, revision history and retirement reason.
- **Gap/request:** missing field, attempted sources, target organization, request draft, sent date only when actually sent, response date, result, next action and closure evidence.
- **Form manifest:** approved item IDs and versions, topic allocation, timing/scoring settings, intended exam package, generation date and checks performed.

Keep performance and content-rights data separate from public regulatory metadata. Agreements, personal learner data and restricted content need an appropriate private store; a public GitHub report should contain only safe summaries and links.

## 8. Separate status from confidence

Track at least three independent statuses:

1. **Specification:** discovered → retrieved → extracted → verified, with partial/blocked/conflicted branches.
2. **Content rights:** unknown → inquiry drafted → awaiting response → permitted/licensed/original-owned, or declined/restricted.
3. **Practice content:** planned → drafted → reviewed → approved → retired.

A highly supported exam fact does not improve a question bank's licensing status. A signed content license does not verify an exam edition. A source count does not prove coverage.

Use the source hierarchy and deterministic citation checks already specified in the nationwide document. Route publication-critical uncertainty to review. Never fill absent scores, question counts, code cycles or difficulty estimates with defaults.

## 9. Completion gates and recurring process

An **exam specification is complete** only when the selected exam's necessary identity, components, format, references/editions, topic scope and date applicability are verified, or a genuinely unpublished field has a documented disposition. If weights are unpublished, the product cannot present editorial weights as official.

A **package is ready for scored mocks** only when its necessary specification is accepted, all included assets have a suitable use basis, every item is reviewed, the planned forms satisfy the coverage map, scoring has been checked, and material scope limitations are stated. This is a proposed product gate, not a certification authority's approval.

After launch, periodically check authoritative pages and licensed updates according to source volatility and provider terms. Detect changed hashes/versions; compare affected fields; review the change; identify affected questions/forms; replace or retire them; preserve historical exam versions for earlier users. A changed website alone is not proof that an exam changed.

Use voluntary official exam outcomes, when available and appropriately consented, to assess later whether practice results predict outcomes. Record exam version, first versus repeat attempts, practice exposure and sample size. Until that analysis supports prediction, display topic mastery and practice scores without a claimed probability of passing.

## 10. Reusable research-job prompt

> Research one plumbing credential/exam package for [jurisdiction], [official credential or discover first], [locality if applicable], for an intended exam date of [date], using evidence available as of [cutoff]. Start from the existing source ledger and fetch authoritative unread leads before broad discovery. Establish state/local scope and keep contractor, journeyman, master and registration credentials distinct. Follow the regulator to the exact exam owner/provider and component IDs. Read current official bulletins, outlines and reference lists. Extract tested editions separately from adopted-law editions; record publication/effective dates, exam sections, counts, duration, score rules, topic weights, permitted/supplied materials and practical requirements. Cite each material field to a retrieved document and page/section; unsupported facts are null. Preserve conflicts and future proposals as such. Classify public metadata, samples, code content, commercial practice banks and live confidential items separately. Identify content owners and documented reuse rights; no public page or purchase is presumed to authorize app redistribution or AI use. Propose licensed or original-authoring routes when reusable content is unavailable. Use at most three total research passes per gap, including the initial pass and up to two targeted retries, then persist a specific unresolved question and next action. Return an exam specification, evidence ledger, asset/rights inventory, conflicts, prioritized gaps and acquisition-request drafts. Do not send requests, purchase licenses, reconstruct confidential items, or claim production readiness merely because sources were found.

## 11. What the next execution should hand back

- A discovered credential inventory for the ten states and explicitly scoped local examples.
- One record per selected exam/component, with exact sources and verification status.
- A list of retrieved official bulletins/reference lists and remaining retrieval failures.
- A content-and-rights ledger showing which route can supply each required asset.
- Concrete clarification/licensing drafts for unresolved cases, ready for the user to authorize and send.
- One small reviewed original-content sample for a selected package if the authoring stage is authorized and qualified reviewers are available.
- An updated gap queue that makes the next pass narrower and more useful.

Progress is measured by closed questions and usable, verified packages. The process continues when new evidence or responses arrive; it does not equate a capped research run with either success or impossibility.

