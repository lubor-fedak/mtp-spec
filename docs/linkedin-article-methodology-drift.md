# The Invisible Tax on Enterprise AI: Why Your Best AI Work Disappears Between Platforms

*You just spent 45 minutes building a sophisticated data analysis methodology in Claude. Now you need to apply it to real data in your company's Azure OpenAI instance. So you open a new chat and start typing: "I need you to analyze this data by first normalizing the vendor names, then..."*

*And you realize you've already forgotten half the edge cases you discovered 20 minutes ago.*

---

## The Problem Nobody Is Talking About

Every enterprise AI deployment today runs into the same invisible wall. It's not about model quality. It's not about data access. It's not about prompting skills.

It's about **methodology drift** — the silent degradation of AI-developed work processes as they move between platforms, sessions, and security boundaries.

Here's what it looks like in practice:

Your data scientist develops a complex analytical pipeline in ChatGPT Pro — her personal subscription, because it's more capable. She discovers edge cases, refines decision logic, tests approaches that don't work, and arrives at a robust methodology. Then she needs to apply it to client data that can't leave the corporate network. She opens the enterprise Copilot and starts re-explaining everything from scratch.

What transfers: a rough summary of the steps.

What gets lost: the intent behind each decision, the edge cases she discovered, the three approaches she tried and abandoned (and *why*), the validation rules she built up through iteration, the exact thresholds she calibrated.

The enterprise Copilot produces a result. It looks reasonable. But it's subtly wrong in ways that won't be caught until someone notices the numbers don't match.

**This is methodology drift.** And it's happening thousands of times a day in every large organization.

## It's a Structural Problem, Not a Technology Gap

You might think this gets solved as AI platforms improve their memory and context capabilities. It doesn't — and here's why.

The problem isn't that AI systems forget. The problem is that **enterprise security policies create a permanent boundary** between where methodologies are developed and where they're applied.

No CISO will ever allow sensitive financial data to flow into a commercial AI subscription. And no enterprise AI deployment will match the capability of frontier commercial models. This creates a permanent split: capable AI on one side, real data on the other, and a human manually bridging the gap.

Even within a single platform, methodology drift occurs every time you start a new thread, hit a context limit, or hand work to a colleague who needs to continue where you left off.

The cost isn't theoretical. A large consultancy with 10,000 knowledge workers, each losing 30 minutes daily to re-explaining AI methodologies across platforms, loses over **2.5 million productive hours per year**. That's before counting the errors introduced by degraded methodology transfer.

## What Would a Solution Look Like?

Think about how software engineering solved a similar problem decades ago. Code doesn't degrade when you move it between machines because it's written in a structured, portable, executable format. The recipe (code) is completely separated from the ingredients (data).

AI-developed methodologies need the same treatment: a structured, portable format that captures not just *what* to do, but *why* — the intent, the decision logic, the edge cases, the dead ends, and the validation rules. Something that any AI system can interpret and execute mechanically, without needing to "understand" the original context.

This is what I've been working on. I'm calling it **MTP — Methodology Transfer Protocol**.

## MTP in 60 Seconds

An MTP Package is a structured YAML file that captures a complete methodology in seven sections:

1. **Intent** — what the methodology achieves and why specific approaches were chosen
2. **Input Specification** — what data the methodology expects and what assumptions it makes
3. **Methodology Steps** — ordered, reproducible steps with decision points and dependencies
4. **Edge Cases** — unusual situations discovered during development and their handling
5. **Dead Ends** — approaches that were tried and abandoned, with reasons (so the target system doesn't repeat them)
6. **Output Specification** — what the methodology produces and how to validate it
7. **Adaptation Notes** — what can be flexibly adjusted vs. what must remain fixed

An MTP Package contains zero data. It's the recipe, not the meal. You develop it in your capable commercial AI, extract it as a structured file, and hand it to your enterprise AI along with the actual data.

The target system doesn't need to be creative or reconstruct your reasoning. It follows the methodology step by step, validates each step, and reports any deviations.

## Why "Dead Ends" Is the Most Important Section

Every existing context transfer solution focuses on what you *did*. MTP also captures what you *tried and stopped doing* — and why.

This matters enormously. When a target AI system encounters a challenge during methodology application, its natural instinct is to improvise. Without dead ends documentation, it will often "discover" the same failed approaches you already explored and rejected. This wastes time at best and produces subtly wrong results at worst.

Dead ends are institutional memory for AI workflows. They're the experienced colleague who says "we tried that in Q2 — here's why it didn't work" before you spend a week rediscovering it.

## Where This Goes Next

MTP v0.1 is a specification and a YAML format. It requires manual extraction from conversations using prompt templates. That's intentional — it needs real-world validation before automation.

The roadmap includes extraction tooling, JSON Schema validation, and eventually automated extraction from conversation exports. But the bigger vision is this: as AI agents become autonomous and operate across systems, they will need to transfer not just data, but working methodology. MTP is designed for that future — agent-to-agent methodology transfer where the "recipe" travels independently of any platform.

The specification is open source under Apache 2.0.

**GitHub:** https://github.com/lubor-fedak/mtp-spec

If you've felt this pain — re-explaining your AI work across platforms, watching methodology degrade as it crosses security boundaries, losing edge cases between sessions — I'd like to hear from you. Open an issue, try extracting an MTP Package from your own workflow, or just tell me where the spec is wrong.

The problem is real. The cost is measurable. And right now, nobody is solving it.

---

*Lubor Fedák is an AI Evangelist and Business Leader at Kyndryl, focused on AI strategy across European markets. MTP was born from the daily frustration of transferring AI-developed methodologies across enterprise security boundaries.*

*#AI #EnterpriseAI #AIStrategy #MethodologyTransfer #OpenSource #MTP*
