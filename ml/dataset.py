"""Training data for the note classifier.

The bundled ``SEED_EXAMPLES`` are hand-labeled example notes used to train a
baseline model so the endpoint works out of the box. Retrain on real data with::

    python -m ml.train                      # seed data
    python -m ml.train --notes              # train on the app's notes table
    python -m ml.train --data dataset.json  # train on a JSON file

JSON format: ``[{"text": "...", "category": "work"}, ...]``
"""

import json
import os

CATEGORIES = [
    "work",
    "personal",
    "ideas",
    "tasks",
    "meetings",
    "research",
]

SEED_EXAMPLES = [
    # --- work ------------------------------------------------------------
    ("Sprint planning: finish authentication this week, review PRs Tuesday, demo Thursday.", "work"),
    ("Update the deployment checklist and write release notes for v0.4 before Friday.", "work"),
    ("Client asked for the new pricing proposal; include the support tier and send by EOD.", "work"),
    ("Blocked on the API rate limit for the billing service. Escalated to backend team.", "work"),
    ("Standup notes: merged the search fix, need to refactor the queue worker next.", "work"),
    ("Draft performance review self-assessment: shipped 3 features, mentored two juniors.", "work"),
    ("Sync with marketing about the Q3 campaign and the landing page redesign.", "work"),
    ("Document the new onboarding flow and update the internal wiki.", "work"),
    ("Quarterly OKRs: grow activation 20%, cut p95 latency, hire one platform engineer.", "work"),
    ("Fix the flaky integration test in CI that fails on Monday mornings.", "work"),
    ("Prepare the sales deck for the enterprise prospect and schedule the follow-up call.", "work"),
    ("Refactor the payment webhook handler and add retries with exponential backoff.", "work"),
    ("Write the feature spec for search filtering: roles, priorities, and edge cases.", "work"),
    ("Approved vacation policy update: two remote weeks per quarter, same team coverage.", "work"),
    ("Onboarding checklist for the new hire: laptop, repos, keys, intro meetings.", "work"),
    ("Migrate the reporting dashboard queries to the new warehouse before month end.", "work"),
    ("Coordinate with legal on the data-processing addendum and sign-off timeline.", "work"),
    ("Triaged prod alert: database connections exhausted during the night batch.", "work"),
    ("Quarterly planning: budget, headcount, roadmap priorities for the sales team.", "work"),
    ("The compliance audit needs updated access logs for all production services.", "work"),
    # --- personal --------------------------------------------------------
    ("Remember to renew the passport and book the dentist for next month.", "personal"),
    ("Mom's birthday is March 14. Get her the cookbook she mentioned and call early.", "personal"),
    ("Weekly meal plan: lentils, roasted vegetables, salmon on Friday night.", "personal"),
    ("My reading list: finish the novel, start the running plan, meditate daily.", "personal"),
    ("Trip to Porto in October: flights, apartment by the river, the wineries tour.", "personal"),
    ("Car needs an oil change and the tires checked before the long drive.", "personal"),
    ("Save for the trip to Japan; skip the new laptop for now.", "personal"),
    ("Gym 3x this week: legs, push, pull. Rest on Sunday.", "personal"),
    ("Call grandma Sunday morning and water the plants before leaving.", "personal"),
    ("Buy moving boxes and change the address for the bills this weekend.", "personal"),
    ("Book a haircut and pick up the dry cleaning on Saturday.", "personal"),
    ("Renew the gym membership and freeze it during the summer break.", "personal"),
    ("Plan the anniversary dinner: the new Italian place downtown, 7pm.", "personal"),
    ("Water the balcony plants, change the cat litter, and do the laundry.", "personal"),
    ("Check blood pressure numbers this week and book a checkup with Dr. Lee.", "personal"),
    ("Sister's graduation is in June - arrange travel and a gift.", "personal"),
    ("Save up for the new bike; budget 200 a month from the fun account.", "personal"),
    ("Rest day today - long walk in the park and early sleep.", "personal"),
    ("Add basil and rosemary to the windowsill garden on Saturday.", "personal"),
    ("Call the bank about the new card and update the autopay for rent.", "personal"),
    # --- ideas -----------------------------------------------------------
    ("Idea: a browser extension that summarizes any tab into an AI note.", "ideas"),
    ("What if notes could auto-link to related notes like a personal wiki?", "ideas"),
    ("Brainstorm: offline-first note app with end-to-end encryption and local AI.", "ideas"),
    ("Product idea: a tiny daily planner that turns voice memos into tasks.", "ideas"),
    ("Name for the side project: 'Lumen', a focus timer with ambient sound.", "ideas"),
    ("Feature sketch: swipe gestures to organize inbox into folders faster.", "ideas"),
    ("Idea: mood tracking inline with journal entries, visualized weekly.", "ideas"),
    ("Concept: share read-only note links with a short expiry for teams.", "ideas"),
    ("Idea: TTS reading of notes with speed control for commutes.", "ideas"),
    ("Rough idea for a newsletter: one algorithm-free tool tip every Sunday.", "ideas"),
    ("Crazy idea: notes that suggest related recipes when you journal about cooking.", "ideas"),
    ("What if the app highlighted stale notes and proposed archiving them?", "ideas"),
    ("Service idea: turn meeting transcripts into a searchable knowledge base.", "ideas"),
    ("Doodle: a minimal OSD timer widget with a tiny canvas for interruptions.", "ideas"),
    ("Name candidates for the design tool: Vellum, Paperlane, Noteboard.", "ideas"),
    ("Idea: local-first sync over a tiny edge server to keep data private.", "ideas"),
    ("Might be fun: weekly 'note sparks' prompt shipped as a micro-feature.", "ideas"),
    ("Video idea: 60-second product teardowns of note apps on YouTube.", "ideas"),
    ("Idea: collaborative live notes with presence cursors, like Figma for text.", "ideas"),
    ("Concept: generate a morning brief from your last week of notes.", "ideas"),
    # --- tasks -----------------------------------------------------------
    ("TODO: deploy the migration, restart workers, tag v1.2, notify the channel.", "tasks"),
    ("Groceries: eggs, oats, spinach, coffee, olive oil, lemons.", "tasks"),
    ("Errands: dry cleaning, pharmacy, post office for the package.", "tasks"),
    ("Today: ship the invoice pagination, reply to Sarah, file the taxes.", "tasks"),
    ("Checklist before launch: enable SSL, backup script, error tracking, status page.", "tasks"),
    ("Home tasks: fix the kitchen faucet, replace the smoke detector battery.", "tasks"),
    ("Review list: pull requests #301, #302, security patch, upgrade dependencies.", "tasks"),
    ("Don't forget: submit the expense report and renew the subscription.", "tasks"),
    ("Pack for trip: charger, adapter, documents, one warm jacket.", "tasks"),
    ("Chores: take out recycling, vacuum, water plants, wash the car.", "tasks"),
    ("To-do before Friday: update resume, renew passport, return library books.", "tasks"),
    ("Shopping list: toothpaste, batteries, notebook, 4K hdmi cable.", "tasks"),
    ("Call the plumber about the leaking sink and quote two companies.", "tasks"),
    ("Sign up for the conference workshop and register for the evening mixer.", "tasks"),
    ("Register the new domain and point the DNS before the site redesign.", "tasks"),
    ("Backlog to clear: unread emails, old browser tabs, and the Downloads folder.", "tasks"),
    ("Evening checklist: log workouts, meal prep Monday and Tuesday, charge devices.", "tasks"),
    ("Pay the electricity and internet bills today, set reminders for the rest.", "tasks"),
    ("Hand over to-do: share the runbooks, transfer file ownership, update docs.", "tasks"),
    ("Plan chores for Sunday: deep kitchen clean, handle the recycling.", "tasks"),
    # --- meetings ----------------------------------------------------------
    ("1:1 with Alex: discuss the promotion timeline and the project he owns.", "meetings"),
    ("Town hall Thursday 4pm: quarterly numbers and new benefits.", "meetings"),
    ("Product review: walk through the new editor mockups with design.", "meetings"),
    ("Retro notes: too many interrupts, agree on deep-work mornings.", "meetings"),
    ("Kickoff with Acme: scope the integration, decide ownership, set the demo date.", "meetings"),
    ("Interview Wednesday 2pm: backend engineer, focus on systems design.", "meetings"),
    ("Planning session: estimate next sprint, slice the payment epic.", "meetings"),
    ("Design critique Friday: present the dashboard redesign early.", "meetings"),
    ("Client sync about the API contract, request a signed NDA first.", "meetings"),
    ("Offsite agenda draft: roadmap talk, team activities, dinner at 7.", "meetings"),
    ("Weekly sync with the design team to review the new component library.", "meetings"),
    ("Vendor call: walk through their updated security questionnaire.", "meetings"),
    ("Standup tomorrow: yesterday's progress, today's plan, blockers.", "meetings"),
    ("Board meeting prep: pull the metrics pack and rehearse the update.", "meetings"),
    ("Accessibility review session with QA to audit the new form flows.", "meetings"),
    ("Partner workshop on joint roadmap, then a working lunch at 1pm.", "meetings"),
    ("Sprint demo to stakeholders: show search, export, and the new editor.", "meetings"),
    ("Morning huddle: confirm the demo environment and who presents what.", "meetings"),
    ("Onboarding intro call with the new product manager.", "meetings"),
    ("All-hands agenda: security roadmap, team awards, Q&A.", "meetings"),
    # --- research -----------------------------------------------------------
    ("Research: vector embeddings vs BM25 for retrieval quality on support docs.", "research"),
    ("Compare Postgres and SQLite configurations for a high-write notes sync.", "research"),
    ("Paper notes: transformer architectures, attention is all you need highlights.", "research"),
    ("Look up open-source licences before shipping the SDK.", "research"),
    ("Research grant sources for the open-source project and deadlines.", "research"),
    ("Survey note apps: pricing, export format, offline behavior for the comparison post.", "research"),
    ("Compare auth libraries: cost, maintenance, adoption for our stack.", "research"),
    ("Study the new WebGPU API and whether it helps the editor renderer.", "research"),
    ("Check whether serverless functions fit the background job requirements.", "research"),
    ("Research email deliverability: SPF, DKIM, DMARC and our sending volume.", "research"),
    ("Read up on hypertables and time-series indexing for the analytics feature.", "research"),
    ("Benchmark session reuse and connection pooling for the Python worker.", "research"),
    ("Summarize the quantization paper and note the accuracy trade-offs.", "research"),
    ("Investigate edge cases in timezone handling across library versions.", "research"),
    ("Compare Prisma versus raw SQL for the migration project milestones.", "research"),
    ("Research pricing models for the new tier and competitor feature sets.", "research"),
    ("Study accessibility heuristics and WCAG 2.2 changes for the audit.", "research"),
    ("Dive into the docs for the new streaming API and note the throttles.", "research"),
    ("Literature scan: retrieval-augmented generation for personal knowledge bases.", "research"),
    ("Look into on-device models that run in the browser for offline features.", "research"),
]


def load_dataset(path):
    path = os.path.abspath(path)
    with open(path, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    data = []
    for row in rows:
        text = (row.get("text") or row.get("content") or "").strip()
        category = (row.get("category") or "").strip().lower()
        if text and category in CATEGORIES:
            data.append((text, category))
    return data


def examples_from_notes(db):
    """Pull (text, category) pairs from the app's notes table.

    Uses the note's ``category`` column when present, falling back to the
    first matching tag (lowercased) when a ``tag`` column exists, otherwise
    defaults to ``personal``.
    """
    columns = [row[1].lower() for row in db.execute("PRAGMA table_info(notes)").fetchall()]
    select = []
    for col in ("title", "content", "category", "tag"):
        if col in columns:
            select.append(col)
    if "content" not in columns:
        return []
    if "title" not in select:
        select.insert(0, "title")

    rows = db.execute(
        "SELECT %s FROM notes WHERE content IS NOT NULL AND TRIM(content) != ''"
        % ", ".join(select)
    ).fetchall()

    data = []
    for row in rows:
        text = ("%s\n%s" % (row["title"] or "", row["content"] or "")).strip()
        if not text:
            continue
        category = row["category"] if "category" in row.keys() else None
        category = (category or "").strip().lower()
        if category not in CATEGORIES:
            category = (row["tag"] or "") if "tag" in row.keys() else ""
            category = (category or "personal").strip().lower()
        if category not in CATEGORIES:
            category = "personal"
        data.append((text, category))
    return data