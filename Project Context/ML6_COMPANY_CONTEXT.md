# ML6 — Company Context

**Document Type:** Background Intelligence File  
**Purpose:** AI agent context for the World Analyst project — understanding who ML6 is, what they build, and how they think  
**Last Updated:** April 2026  
**Source:** ml6.eu, jobs.ml6.eu, public blog content

---

## Identity

**Full name:** ML6  
**Website:** https://www.ml6.eu  
**Tagline:** "We guide the AI revolution towards positive impact."  
**Mission:** Use the full potential of artificial intelligence to spark innovation, increase efficiency, accelerate growth, and create lasting impact — not just for businesses, but for humanity.

ML6 is a European AI consultancy and product company headquartered in Ghent, Belgium. They are not a traditional software agency; they position themselves as an AI-first company that builds real, production-grade AI systems for enterprise clients while simultaneously living AI-native practices internally.

---

## History — The Four Waves

ML6's CEO Nicolas Deruytter describes the company's evolution through four waves:

**2012 — Big Data**  
ML6 founded in Ghent. Focus on big data infrastructure while competitors focused on cloud. Early-mover advantage in data engineering.

**2015 — The Pivot to AI**  
Deliberate decision to lean into the rising AI wave. Built out custom vision models, foundational ML capabilities, and first SaaS spin-offs. Developed a reputation for technical excellence and measurable ROI delivery.

**2020–2024 — Digital Twins, GenAI, Agentic AI**  
Consistent early investment in each successive wave. Built an agent-based voice platform for a major bank. Delivered AI vision quality control systems for manufacturing clients. Four consecutive Deloitte Fast 50 recognitions.

**2025 — Superintelligence**  
Current strategic direction. ML6 believes this is "the final wave." The company is building Unum — their Enterprise Superintelligence platform — as the north star of this phase.

---

## Leadership

**Nicolas Deruytter** — CEO & Co-Founder  
Described as being "at the intersection of business, technology, and society." Sought-after speaker on entrepreneurship, innovation, and the practical value of AI. Drove ML6 through 10x growth and four Deloitte Fast 50 appearances. His public writing frames ML6's ambitions around building unified enterprise intelligence rather than fragmented point solutions.

**Georges Lorré** — Senior Data Engineer  
Author of the AI Native WoW engineering blog (Feb 2026). Specialises in robust data solutions and team workflow optimisation. Active in mentoring junior developers.

**Julie Plusquin** — Talent Lead (Talent & Culture)  
Point of contact for the AI Automation Engineer hiring process.

---

## Offices

| Location | Country |
|---|---|
| Ghent | Belgium (HQ) |
| Amsterdam | Netherlands |
| Berlin | Germany |
| Munich | Germany |
| London | United Kingdom |

GCP region for this project: `europe-west1` (Belgium) — aligns with ML6's home market and Benelux client base.

---

## Products — What ML6 Actually Builds

### Unum — Enterprise Superintelligence Platform

Unum is ML6's flagship product. Launched publicly in late 2025 alongside OpenAI at Belgium's first in-person OpenAI event.

**Core concept:** A unified, enterprise-wide AI operating system that generates its own agents to solve business problems. Not another standalone tool — a living system that learns from teams, absorbs proprietary knowledge, and automates processes across the entire organisation.

**Key positioning:** "Stop buying solutions, generate them, and own them."

**What makes Unum different from traditional AI:**
- Traditional AI: point solutions (one chatbot, one vision model, one automation)
- Unum: one cohesive intelligence that integrates all of these into a proactive autonomous workforce

**Architecture principles:**
- Deployed on-premises or cloud (customer's choice — sovereign deployment)
- Full observability and override capability retained by the client
- Human-in-the-loop approval mechanisms built in
- GDPR, CRA, ISO 27001, SOC 2, NIS2 compliance baked into the design

**Unum's self-description (ML6's own language):**
> "It flows through your organisation like a wave of stem cells — identifying issues, adapting to context, and providing a healing fix. Every interaction makes it sharper. Every approval makes it stronger."

### Intelligence Modules

Unum is built on modular AI capabilities that can be deployed independently or as part of the full platform:

| Module | Description |
|---|---|
| Vision AI | Computer vision for quality control, detection, and monitoring |
| Physical AI & Robotics | Humanoid robots and physical automation integrated into enterprise workflows |
| Voice AI | Agent-based voice systems (deployed for Actief; major bank use case) |
| Computer Use AI | AI that operates desktop interfaces autonomously |
| Integration AI | Connects fragmented enterprise systems into a unified intelligence layer |

### Agentic AI Solutions

Vertical-specific agentic applications built on the Unum platform:

- Marketing automation agents
- Product Innovation agents
- Recruiting agents
- Customer Service agents

### Services (Advisory Side)

Beyond product, ML6 offers consulting services:

- **AI Advisory** — strategy and roadmap design
- **AI Governance** — responsible deployment frameworks
- **CAICO Certification** — AI officer training programme
- **AI Literacy Training** — workforce upskilling

---

## Technology Partners

ML6 explicitly partners with all major AI and cloud providers — a deliberately agnostic stance:

| Partner | Relationship |
|---|---|
| Google | Primary cloud partner; GCP is ML6's default platform; Vertex AI integration |
| OpenAI | Joint events; OpenAI models used in client work; OpenAI Belgium launch partner |
| NVIDIA | Featured at NVIDIA GTC Paris 2025; Physical AI and GPU infrastructure |
| Microsoft | Azure AI Foundry and Microsoft ecosystem integrations |
| AWS | Cloud engineering across AWS stack |

**Implication for the challenge:** GCP + OpenAI (or Vertex AI Gemini) are ML6's most natural combination. Using `europe-west1` on GCP aligns directly with their primary cloud partner relationship.

---

## Industries Served

ML6 operates across eight vertical sectors:

- Communication, Media & Technology
- Energy & Utilities (won Elia "Hack The Grid 2025" — grid congestion ML challenge)
- Financial Services
- FMCG (fast-moving consumer goods)
- Government & Public Services
- Healthcare & Life Sciences
- Industrial / Manufacturing
- Retail & E-commerce

**Implication for World Analyst:** The dashboard includes countries from across these sectors' home markets — including Belgium, Netherlands, Germany, UK — which are ML6's core geographies.

---

## Branding & Visual Identity

### Colour System

| Role | Value | Usage |
|---|---|---|
| Primary brand colour | `#E8400C` (ML6 orange-red) | Logo, CTAs, hero accents |
| White / Off-white | `#FFFFFF` / `#F5F5F5` | Body, light backgrounds |
| Dark grey | `#1A1A1A` / `#0E0E0E` | Dark UI surfaces |
| Neutral grey | `#737373` | Supporting text |

ML6's logo is "ML6" rendered in bold, uppercase weight using their orange-red against white or dark backgrounds.

**Note:** The World Analyst design system uses `#FF4500` as the accent orange — a deliberate visual echo of ML6's brand colour. This is intentional and worth mentioning in the presentation.

### Typography

ML6's public-facing site uses clean, modern sans-serif typography (Inter family or equivalent). Headlines are bold and impactful. No decorative fonts. The visual language is technical but not cold — confident and human.

### Design Language

ML6's web presence is clean, high-contrast, and product-led. They use structured grid layouts, large headline statements, and minimal visual noise. The aesthetic reflects their engineering culture: deliberate, precise, enterprise-grade. Not startup flashy. Not corporate stiff.

---

## AI for Good — Responsible AI Commitments

ML6 has formal commitments to responsible AI that are publicly documented:

- **Safe & Secure AI** — security frameworks, observability, and governance built into every deployment
- **Responsible AI** — transparency, bias mitigation, and alignment with societal values
- **ML6 for Good** — explicit acknowledgement that AI may displace jobs; commitment to act "proactively and responsibly"
- Formal whistleblower channel for reporting serious misconduct (hosted on sdwhistle.com)

**Implication for World Analyst:** The AI disclaimer in the dashboard footer ("AI-generated content may contain inaccuracies. Verify before acting.") directly reflects ML6's public responsible AI stance. This is not a generic warning — it is a deliberate product decision that mirrors their company values.

---

## Key Cultural Signals

These phrases and concepts appear repeatedly in ML6's public communications. They reflect real internal values, not just marketing:

- **"People first"** — their culture page's opening statement
- **"Substance before hype"** — repeated in CEO letter; they invest in waves early, before they peak
- **"Seamless access"** — from the challenge brief; they value things that work without friction
- **"Living and breathing AI-native"** — they don't just advise clients on AI; they use it internally
- **"Stable, safe, and enterprise-grade"** — their definition of quality; not just working, but defensible
- **"If you can't explain it and defend it, you can't ship it"** — Absolute Ownership principle

---

## Notable Work (Public)

- Built an agent-based **voice platform** for a major Belgian bank
- Delivered **AI vision quality control** systems for manufacturing clients
- Won the **Elia "Hack The Grid 2025"** hackathon with an ML model that safely maximises existing power grid infrastructure
- Launched **Unum** publicly at the first OpenAI in-person event in Belgium (Ghent, late 2025)
- Participated in **NVIDIA GTC Paris 2025** — featured in European AI infrastructure discussions

---

*This file is a living reference. It is background intelligence for the World Analyst build and presentation — not a repeat of the challenge brief.*  
*Source URLs: ml6.eu, jobs.ml6.eu, blog.ml6.eu, edtechinnovationhub.com*
