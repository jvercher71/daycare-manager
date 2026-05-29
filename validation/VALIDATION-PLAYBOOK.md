# Daycare Software — Validation Playbook

**Goal of this phase:** Prove that small daycare centers will *pay* for what you're building — *before* you write another line of code. You are time-rich and cash-poor, which is a perfect fit for the manual, conversation-heavy work below. The build is the easy 30%. This is the hard 70%.

**Working product name:** "Sprout" *(placeholder — swap for your real name everywhere)*

---

## 1. Positioning (the one sentence)

> **Flat-price daycare management for small centers — parent app, billing, and compliance included, without Brightwheel's per-child fees.**

You are NOT trying to beat Brightwheel or Procare on features. You win one narrow segment by being **cheaper, simpler, and flat-priced**, and by **out-caring** the giants on support.

**Why this opening exists (from market research):**
- Brightwheel charges per child (~$200–350/mo for a 30–50 kid center); cost balloons as you grow.
- "$50/mo" tools turn into $200 once setup, training, and migration fees hit.
- Compliance features are gated behind higher tiers.
- Procare is built for large multi-site operations — oversized for a single small center.

---

## 2. Ideal Customer Profile (who you talk to)

Talk ONLY to people who match this. A "yes" from the wrong person is worse than a "no."

- **Type:** Licensed single-site daycare / preschool
- **Size:** ~10–50 children (too small for Procare, priced-out by Brightwheel)
- **Buyer:** Owner-operator or director who also does the admin themselves
- **Current state:** On paper/spreadsheets, OR using a competitor and grumbling about price
- **Geography:** Start with ONE state (compliance rules vary by state — pick yours). Expand later.

**Explicitly NOT your customer (for now):** large chains, multi-site franchises, nanny/in-home-only providers.

---

## 3. Where to find them (your time, ~$0)

In rough order of value:

1. **State childcare licensing directory.** Most US states publish a public, searchable list of every licensed center — usually with name, address, capacity, and phone. This is a free, complete prospect list. Search "[your state] licensed childcare provider search."
2. **In-person visits.** You have time. Walk in during nap/quiet hours (early afternoon), ask for the director, lead with a question — not a pitch. Highest conversion by far.
3. **Local childcare Facebook groups** for directors/providers. Lurk first, learn the language, then ask thoughtful questions.
4. **Local AEYC chapter / licensing association** meetings and events.
5. **Google Maps "daycare near me"** → call list.

---

## 4. The discovery conversation (Mom Test rules)

The single biggest mistake here is asking people if they'd buy your idea. They'll be nice and lie. Instead, **ask about their past and present behavior** — facts, not opinions about the future.

**Rules:**
- Don't pitch. Don't mention "Sprout" until the very end (if at all).
- Ask about what they do *today* and what *actually went wrong* recently.
- Talk about their life, not your idea.
- The best signal is a real commitment (time, email, intro, or money) — not "that sounds great."

**Questions to ask (adapt, don't read robotically):**
1. "Walk me through how you handle billing and tuition right now."
2. "What's the most frustrating part of the admin side of running the center?"
3. "What tools or software do you use today? What do you pay for them?"
4. "What made you pick that — and what annoys you about it?"
5. "Tell me about the last time a parent payment or attendance record got messed up. What happened?"
6. "Have you ever looked at switching tools? What stopped you?"
7. "How do you keep parents updated during the day — photos, notes, anything?"

**Never ask:** "Would you use an app that does X?" → hypothetical = useless.

---

## 5. Pricing to test

Float a **flat monthly price with no per-child fee** — that's the whole hook. A range to probe: **$39–$59/mo flat**.

Anchor it against reality by first asking what they pay now. If they're on Brightwheel at $250/mo, a $49 flat price is a screaming deal. If they're on paper at $0, your job is proving the time saved is worth $49.

Don't just state a price — ask: *"If a tool did [the painful thing they described] for $49 a month flat, no per-child charges, is that something you'd want to see when it's ready?"* Then watch what they actually do next.

---

## 6. Success & kill criteria

Set the bar before you start so you don't fool yourself.

**Target:** 15–20 real conversations with ICP-matched centers.

**Green light (build the billing module next) if:**
- A clear majority describe a *specific, current* pain around billing, compliance, or parent comms — unprompted.
- You collect **5+ "early access" email signups** from people who genuinely want it.
- At least **1–2 commit to a paid pilot** or sign a letter of intent.

**Yellow (iterate positioning) if:**
- People are interested but the pain you're solving isn't the one they feel most. → Pivot to the pain they keep naming.

**Red (rethink the niche) if:**
- After 20 conversations, almost nobody will give you 15 minutes or an email address. → The wedge is wrong; don't build more.

---

## 7. This week's concrete to-do

- [ ] Pick your launch state and pull the licensing directory into a simple list (aim for 50+ centers).
- [ ] Put the landing page live (see `landing-page.html`) and wire up the email form.
- [ ] Have **5 discovery conversations** (call or in-person). Take notes against the questions above.
- [ ] Log every conversation: center name, size, current tool, top pain, commitment signal (email / pilot / nothing).
- [ ] Review after 5 — are you hearing the same pain? Adjust before the next 5.

**The number that matters this phase is not lines of code. It's number of real conversations and number of email signups.**
