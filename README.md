# Assignment 07 — Property Rental & Maintenance

## The scenario

Picture a small property management company handling a portfolio of a few dozen rental units on
behalf of several landlords — collecting monthly rent, keeping units occupied, and sending someone
out whenever a tenant reports something broken. Rent arrives by bank transfer or check and gets
checked off against a spreadsheet by hand, and repair requests come in over the phone and get
written on whatever notepad is nearest the desk that day.

The result is predictable. A payment gets marked received against the wrong unit, or not marked at
all, and nobody notices until a tenant who has actually paid gets a late notice. A maintenance
request scrawled on a sticky note goes missing along with the sticky note, so the same leaking
faucet gets reported three times by an increasingly irritated tenant before anyone sends a
contractor. Asking which units are behind on rent, or which repairs have sat untouched for two
weeks, means paging through paper by hand and hoping nothing was missed.

They want one system: managers see the whole portfolio, tenants' rent payments get recorded against
the right unit and month, and every maintenance request is tracked from the first report to the
contractor closing it out. Anyone should be able to tell which units are behind on rent, and which
repairs have gone unattended, without digging through paper. Build the system that replaces the
notebook and the sticky notes.

## What it must do

Everything below is required. Several of the ten spell out exact rules — what happens on an illegal
move, what a bulk action must report back, when a dismissed alert is allowed to reappear — and those
specifics are the actual ask, not just the bold headline in front of them.

1. **Accounts and roles.** People sign in with an email and password, and there are at least two
roles — a property manager role and a maintenance contractor role. Property managers create and
archive units, log new maintenance requests, assign contractors to them, and record rent payments;
they see the whole portfolio. Maintenance contractors can only see and update maintenance requests
assigned to them, and cannot create units, assign other contractors, or see rent data. The
difference must be enforced on the server, not just hidden in the interface.

2. **Units.** Property managers create units with a unit number, an address, a monthly rent amount,
and the current tenant's name, and can edit them later. Rent is due on the first of each month, with
a short grace period before an unpaid month counts as overdue. Property managers also record rent
payments against a unit, each with an amount and the month it covers. Units can be archived and
restored; archiving removes a unit from the default portfolio view without destroying its history or
its maintenance requests.

3. **Maintenance requests.** Every maintenance request belongs to exactly one unit and carries a
description and a priority, plus which contractors are currently assigned to it. Requests can be
created by a property manager or a maintenance contractor; either can edit the description and
priority, but not the assigned-contractors list. Opening a unit shows its maintenance requests.

4. **A maintenance request lifecycle with rules.** A maintenance request moves through *Reported →
Triaged → Scheduled → Resolved*. It cannot move into Scheduled unless a contractor is already
assigned to it — the server rejects the attempt otherwise. A Resolved request can be reopened, which
returns it to Triaged rather than to Reported. Any other move must be rejected by the server with a
message explaining why.

5. **Assignment.** Any number of contractors can be assigned to a maintenance request, and a single
contractor can be assigned to any number of requests at once. Only a property manager can add or
remove a contractor's assignment to a request. Every contractor can see one list of every request
assigned to them, across every unit.

6. **Finding requests.** One list shows maintenance requests across every unit the viewer can see,
with a text search over descriptions, filters for unit, status, contractor and priority, sorting by
created date, priority or status, and pagination showing the total number of matches. All of this
must happen on the server — do not load every request into the browser and filter there.

7. **Acting on rent for many units at once.** Property managers can bulk-record the rent payments
received for a given month — a batch of unit identifiers and amounts — in one action. The result is
a per-unit report classifying each row as matched (the amount received equals that unit's monthly
rent), underpaid (the amount received falls short of it), overpaid (the amount received exceeds
it), or unmatched (the identifier given does not correspond to any unit). Separately, export the
current rent roll — every unit with its monthly rent, its tenant, and its current payment status —
as a CSV file.

8. **A dashboard.** A landing view shows headline numbers — open maintenance requests, units with
rent overdue this month, requests resolved this week, and total rent collected this month. It also
breaks maintenance requests down by status and by contractor, and charts requests resolved per week
over the last eight weeks.

9. **History you cannot rewrite.** Every maintenance request has a timeline showing when it was
created, every status change with the old and new value and who made it, every contractor assignment
and unassignment, and any notes left on it. Nothing in this timeline can be edited or deleted after
the fact, including by property managers.

10. **Rent alerts.** A unit whose rent has not been matched by a full payment once its grace period
passes appears in an alerts area, with a count badge visible in the navigation. A property manager
can dismiss the alert for that unit. If the unit's rent is still unmatched after the grace period in
a later month, the alert returns.

## Stretch ideas (optional)

None of these are required, and none substitute for a goal above. If you finish all ten with time
left over, pick whichever of these sounds most useful and build it:

- An online tenant portal for submitting requests and viewing rent history.
- Lease renewal reminders before a lease term ends.
- Photo attachments on maintenance requests.
- A contractor rating or review system.
- Recurring preventive-maintenance schedules.
- Support for multiple property owners or portfolios.
- Automatic late-fee calculation on overdue rent.
- Utility billing alongside rent.
- Move-in and move-out inspection checklists.


---

## What we are assessing

A working application is table stakes. Almost every serious candidate will produce something that runs, has a login, and roughly does what was asked. That's the floor, not the differentiator.

What actually separates submissions is the record of thinking behind the app: the decisions you made and why, the trade-offs you weighed, what you built first and what you deliberately left out, and whether you can explain any part of your own system when asked. We are hiring for judgement. The app is the evidence for that judgement, not the deliverable in itself.

We also read the code itself for structure and readability, which counts for a small share of the overall score.

## Time budget

Budget about 12 hours total, spent roughly 2 hours a day across a week.

This is not a race. We are not timing you against other candidates, and submitting early scores nothing extra. Twelve hours is a size guide so you know how much to attempt — pace yourself, stop when you're tired, and spend some of that time thinking and documenting, not only typing code.

## Pick any stack you like

Use any language, any framework, any UI library, any ORM, and any database access approach you want. We have no house stack, and no stack scores better than another — this round is not a test of whether you know particular tools.

Use whatever you are fastest and most confident in. Time spent learning something new to impress us is time not spent on the ten goals above, and it will show.

## Using AI is allowed and encouraged

Use AI tools however you want — to scaffold code, debug a stuck problem, write tests, draft documentation, or anything else that helps you move faster. A few things to know about how we treat it:

- We do not penalise AI use, and we make no attempt to detect it.
- We care about whether you understood, directed and verified the output — not about who or what produced the first draft of it.
- `docs/ai-prompts.md` must contain the prompts you actually used, including the ones that produced bad output and what you changed afterwards. If you used no AI at all, say so here and describe how you worked instead — that is assessed the same way.
- Submitting generated code you cannot explain is the single most common way candidates fail this round.

You are accountable for everything in your submission. If a reviewer points at a piece of code and asks why it's there, or why it works the way it does, "the AI wrote it" is not an answer.

## Use git properly

Publish to a public GitHub repository, and commit incrementally as the work actually happens — after each meaningful step, not in one pass at the end.

A repository whose entire history is a single "initial commit" containing a finished app scores zero on git history, and it colours how we read everything else in your submission, however good the app itself is. Your history is how we see the order you built in, where you got stuck, and how the design changed along the way. If it isn't there, we can't assess it, and we won't assume the best.

## What you must commit

Alongside your code, commit these five files under `docs/`. Your zip includes a stub for each with the questions it needs to answer — fill them in as you go, not from memory at the end.

| File | What it must answer |
|------|----------------------|
| `docs/architecture.md` | What the moving pieces are, how they talk to each other, where each one runs, the request path for one representative user action end to end, and what you decided not to build. |
| `docs/schema.md` | Every table's columns and types, which relationships are one-to-many versus many-to-many, which constraints live in the database versus the application, what you deliberately denormalised, and what would break first at 100x the data. |
| `docs/plan.md` | How you split the work into sessions, what order you built in and why, what you estimated versus what it actually took, and what you cut when you ran short. |
| `docs/decisions.md` | At least five real decisions — what you chose, what you rejected, and why — including at least one you later reversed. |
| `docs/ai-prompts.md` | The prompts you actually used, in order, grouped by what you were trying to do, including at least one that produced something wrong and what you did about it. |

## Host it for free

Deploy the whole thing somewhere reachable by URL, using free tiers only.

One combination that works, if you would rather not decide:

- **Database** — a managed service such as Supabase.
- **Server-side code** — Render.
- **Browser-side code** — Vercel.

Deploy in that order: create the database first, give the server its connection details as environment variables, then point the browser-side part at the server's public URL.

This is one option, not a requirement. Any free host is equally acceptable — everything on a single provider, one virtual machine, a container platform, a static host with serverless functions. The choice earns and loses nothing.

Requirements:

- A working live URL.
- Seeded with enough demo data to show the system doing something, not an empty shell.
- Demo credentials for every role recorded in `SUBMISSION.md`.
- Connection strings, keys and passwords kept in environment variables, never in the repository.
- Free tiers often sleep when idle and can take a minute or more to wake. Note it in `SUBMISSION.md` if yours does, so a slow first load is not read as a broken deployment.
- If you cannot get it hosted, submit anyway and record in `SUBMISSION.md` what you tried and where it broke.

## How to submit

Send us:

- The URL of your public GitHub repository.
- The URL of your live, deployed application.
- Your completed `SUBMISSION.md`, committed to the repository.

That's the whole submission. Nothing else to prepare, no separate form.

## What happens next

If your submission clears the bar, we'll set up a short call. We will ask about specific decisions we can see in your repository and its history — why you modelled something a particular way, what a certain commit was fixing, what you'd change if you kept going.

We're telling you this now because it should change how carefully you document as you go. Write `docs/decisions.md` for a version of yourself who has to explain it three weeks from now.

## Scope

The 10 goals stated in this brief are the cutoff. Meet all 10, solidly, and you have a complete submission.

Stretch ideas are optional. They exist for candidates who finish the 10 with time left and want to keep building — they are never required, and they do not make up for a goal you didn't hit. Doing 8 goals well beats doing 10 goals badly. If time is short, finish fewer goals properly rather than leaving all ten half-done.
