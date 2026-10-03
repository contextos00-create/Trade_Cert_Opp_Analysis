# Nationwide trade certification research: discovery findings

**Research date:** October 3, 2026

**Decision:** Use an authority-led inventory, then bounded Scrapy retrieval, candidate extraction, deterministic evidence checks, and human review. Keep national completion tied to every required credential and delegated locality, not to the number of pages crawled.

This note guides implementation of the [build document](../NATIONWIDE_US_TRADE_CERTIFICATION_BUILD_DOC.md). It records what was checked directly, what the current code can do, and what still needs source access. No licensing requirement is asserted here.

## Findings from live checks

| Check | Observed result | Design consequence |
| --- | --- | --- |
| [Ohio administrative code robots policy](https://codes.ohio.gov/robots.txt) | HTTP 200; `User-agent: * Disallow: /`. | Record this source as inaccessible to the crawler. Seek another authorized official route or arrange manual review. Do not bypass the policy or infer rules from search snippets. |
| [Ohio eLicense robots policy](https://elicense.ohio.gov/robots.txt) | HTTP 200; general `Allow: /`, with a password-reset path excluded. | Scrapy may request public pages under the allowed paths. |
| [Ohio eLicense home page](https://elicense.ohio.gov/) | Scrapy fetched a 567-byte HTML response whose visible extraction was empty. The HTML contains JavaScript navigation. Raw SHA-256: `fb120e41664038598836a721fcfbac1be0fb58a0193fb8e4479e6f8f3c183ca2`. | A successful HTTP request is not evidence that licensing text was captured. Inspect the underlying page/API requests first; use browser rendering only where the authorized data cannot be retrieved directly. |
| [USAGov state government directory](https://www.usa.gov/state-governments) and [EPA Section 608](https://www.epa.gov/section608) | The cloud egress proxy returned `CONNECT 403` for both. Their contents were not inspected. | Nationwide authority seeding and federal verification remain blocked until those domains are active in environment settings. |

The live Scrapy trial stored the Ohio response without making a regulatory claim. In this workspace's local database, the national queue contains **392 primary jurisdiction/trade inventories** (56 × 7) and **two pending EPA Section 608 overlay jobs** for HVAC and refrigeration. One Ohio inventory crawl is awaiting review; all remaining national jobs are queued. The local database and source bytes are not committed to Git. Credential-level and delegated-locality expansion has not yet happened, so 394 jobs are only the starting floor.

The checks used the public robots URLs above, a Scrapy fetch of the Ohio home page, and direct requests for the USAGov and EPA pages on October 3, 2026. The 56-jurisdiction/seven-trade scope comes from the repository's build document; it is a work manifest, not a verified count of licenses. The Scrapy documentation cited below was read from upstream commit `e204ad090690f91e421a4628f3e7787dbd784b6b`. HTTP outcomes reflect this cloud environment and should be retested from the eventual production network.

## Recommended discovery path

1. **Create a reviewed authority registry.** For each of the 56 primary jurisdictions and seven trades, identify the official regulator, governing law/rule, public license inventory, and any express delegation to local government. Store the official URL and the passage supporting each association. A search result proposes a URL; a regulator page or law establishes authority.
2. **Discover the actual credential taxonomy.** Preserve official titles and distinguish worker, contractor, qualifying-agent, and business credentials. Associate a credential with multiple covered trades where the law does so. Create documented not-applicable findings for common levels that the jurisdiction does not regulate. Do not pre-create the same credential list for all states.
3. **Expand delegated local scope.** Capture the delegation passage, obtain an official locality directory when available, enumerate affected authorities, and run local authority/credential inventories. If no authoritative licensing-locality list exists, use official geographic entities as candidates and leave uncertain localities in review. A set of major cities is insufficient for national completion.
4. **Retrieve each source with the appropriate method.** Use Scrapy for permitted public HTML/PDF and relevant same-site links. Record blocked robots/access responses. Inspect data endpoints behind dynamic pages; add a browser fallback for permitted pages that genuinely require rendering. Follow exam-vendor links only after an official board source establishes the relationship.
5. **Extract candidates and verify them.** A model may propose fields and short exact quotations. Verify stored bytes, SHA-256, passage location, date window, jurisdiction, trade, and credential before review. Keep obligation, eligibility, exam logistics, fees, renewal, reciprocity, and local scope as separate claims. A human resolves semantic support, conflicting official documents, and negative findings.
6. **Refresh without overwriting history.** Recheck HTTP metadata and content hashes. Preserve the old document and requirement versions; a changed page triggers review rather than an automatic declaration that the law changed.

This design uses Scrapy as the retrieval scheduler and PostgreSQL as the durable coverage/review record. A LangGraph run should process one jurisdiction/credential at a time, so retries and traces remain inspectable. The national parent should queue all primary inventories from the outset, expand child jobs only from reviewed findings, and resume without losing completed work.

## Why the crawler needs several retrieval modes

The Ohio observations show both a crawl prohibition and a page with no readable text despite a successful fetch. [Scrapy's dynamic-content guidance](https://github.com/scrapy/scrapy/blob/e204ad090690f91e421a4628f3e7787dbd784b6b/docs/topics/dynamic-content.rst) recommends finding the data source behind a page before using a headless browser. That should be the default escalation order: public HTML/PDF → documented page data endpoint → permitted browser rendering → blocked/manual source review.

Scrapy's [AutoThrottle documentation](https://github.com/scrapy/scrapy/blob/e204ad090690f91e421a4628f3e7787dbd784b6b/docs/topics/autothrottle.rst) explains why per-host adaptive delay handles fast error responses better than a small fixed delay alone. Current crawler settings use `ROBOTSTXT_OBEY`, AutoThrottle, two requests per domain, and a 25 MiB response cap. The [Scrapy settings reference](https://github.com/scrapy/scrapy/blob/e204ad090690f91e421a4628f3e7787dbd784b6b/docs/topics/settings.rst) documents those controls.

Scrapy supports persistent crawl queues through `JOBDIR`, with a separate directory for each spider run and a clean shutdown requirement; see its [job-resumption guide](https://github.com/scrapy/scrapy/blob/e204ad090690f91e421a4628f3e7787dbd784b6b/docs/topics/jobs.rst). The current national implementation resumes database jobs, but it does not yet resume requests inside an interrupted Scrapy crawl. Add per-batch Scrapy job directories before long national crawls.

## National scale and quality gate

The 392 primary inventories are a lower bound. Each inventory can yield several official credentials, and each delegation can yield many local authority/credential records. Search, document retrieval, model extraction, and expert review costs therefore scale with discovered scope. Bound global work and each host/provider separately; run in resumable batches and prioritize official sources.

The completion gate should require all of the following:

- Every jurisdiction/trade authority and credential inventory reviewed, including documented negative findings.
- Every discovered credential record `validated` or `validated_not_applicable`, with supported material claims and effective dates.
- Every delegated locality inventoried and audited, including unresolved candidates explicitly counted as incomplete.
- Federal overlays researched as separate linked records.
- No required record left `not_started`, `blocked_source`, or `partial_needs_review`; conflicts and reviewer actions retained.

Search snippets and model output never satisfy this gate. The current national audit deliberately reports `national_complete: false`.

## Immediate implementation decisions and open gaps

| Area | Decision or gap |
| --- | --- |
| Search | Keep provider adapters optional. The current Brave adapter discovers government-looking URLs but requires `TRADE_SEARCH_API_KEY`. Its government-domain filter will miss some officially linked exam vendors and non-`.gov` authorities; follow regulator links and maintain reviewed exceptions. |
| Extraction | The optional model adapter requires `TRADE_LLM_API_KEY`. Its output remains a candidate until citation and human support review pass. Long documents need page/topic chunking with explicit truncation reporting. |
| Authority seeds | Build a source-backed 56-jurisdiction authority registry. USAGov and EPA pages were inaccessible during this pass; recheck after environment access changes. |
| Local identity | Add stable locality type and official identifier to avoid conflating a city and county with the same name. Record why each locality entered or left the queue. |
| Review | Implement claim acceptance/rejection, conflict resolution, negative-scope checklist, and audit log before any record can become validated. |
| Evaluation | Manually label dated official-source cases across state-worker, state-contractor, local-delegation, territorial, and federal patterns. Ohio's sample crawl is not a gold case. |
| Observability | Add LangSmith traces/evaluations with source-text redaction and per-run counts once the extraction workflow is stable. |
| Retry behavior | The database queue survives separate batch runs, but automatic discovery currently selects queued jobs only. A blocked job can be retried with a supplied target file; add bounded automatic retry and an explicit source-access resolution path before unattended national operation. |

The environment configuration draft contains Ohio access plus proposed nationwide government domains and search/model secret requirements. Draft persistence does not establish that those changes are active. Until access and values are supplied, manual official target files can exercise the crawler, while automated nationwide discovery remains queued.
