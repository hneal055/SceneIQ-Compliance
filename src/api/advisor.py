"""
AI Advisor API â€” Anthropic-powered chat proxy with streaming and event summarization.
Falls back to scripted keyword-matched responses when no API key is configured,
preserving the full SSE streaming experience for demos.
"""
import asyncio
import json
import logging
import os
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/advisor", tags=["AI Advisor"])

SYSTEM_PROMPT = """You are SceneIQ AI Advisor, an expert in film and television production tax incentives. You help producers, production companies, and accountants maximize tax incentives across global jurisdictions.

Your expertise includes:
- Film tax credits and incentive programs across US states (Georgia, New York, California, Louisiana, Illinois, Michigan, New Jersey, Virginia, Colorado, Hawaii, Oregon, Montana, Mississippi, New Mexico, etc.)
- International programs (UK AVEC, Canadian provincial credits (BC, Ontario, Quebec), Australian offsets, Irish relief, French and Spanish tax rebates, New Zealand grants, etc.)
- Qualifying expense rules, minimum spend thresholds, and credit caps
- Federal incentives (Section 181, etc.) and stacking strategies
- Application documentation requirements and submission timelines
- Budget optimization strategies for maximum incentive yield

Always provide specific, actionable information. Include credit rates, thresholds, and program names when relevant. Format responses with markdown for readability. Note that tax laws change â€” recommend consulting a production accountant for final compliance decisions."""

SUMMARIZATION_SYSTEM = (
    "You are a regulatory intelligence analyst specializing in film and television "
    "production tax incentives. Summarize the following regulatory update in 2-3 concise "
    "sentences. Focus on: what changed, which jurisdictions are affected, and the impact "
    "on productions. Be factual and specific."
)


# â”€â”€ Pydantic models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    production_id: Optional[str] = None


# â”€â”€ Scripted demo responses (used when ANTHROPIC_API_KEY is not set) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_SCRIPTED: list[tuple[list[str], str]] = [
    (["georgia", "expens", "qualif"], (
        "**Georgia Qualifying Expenses**\n\n"
        "Georgia's Entertainment Industry Investment Act covers:\n\n"
        "**Eligible:** Below-the-line labor, equipment rentals, location fees, catering, "
        "post-production, and set construction.\n\n"
        "**Excluded:** Story rights, music rights, above-the-line compensation (unless resident).\n\n"
        "Minimum **$500k** qualified spend required. Georgia residents earn an additional "
        "**10% uplift** on their wages. The base credit is **20%**, rising to **30%** with "
        "the Georgia promotional logo included in end credits."
    )),
    (["california", " ca ", "ca film"], (
        "**California Film Tax Credit 3.0**\n\n"
        "California offers a **25% credit** on qualified expenditures.\n\n"
        "**Requirements:**\n"
        "- Minimum $1M qualified spend\n"
        "- 75% of principal photography must occur in California\n"
        "- Competitive allocation â€” projects are scored and ranked\n\n"
        "**Eligible:** Below-the-line labor, equipment, locations, post-production.\n\n"
        "**Max credit:** $25M per project. Apply through the California Film Commission."
    )),
    (["new york", " ny ", "new york film"], (
        "**New York Film Tax Credit**\n\n"
        "New York provides a **25â€“35% credit** on qualified below-the-line costs.\n\n"
        "**Base rate:** 25% statewide\n"
        "**Upstate bonus:** Additional 10% for productions outside NYC\n\n"
        "**Requirements:**\n"
        "- Minimum $1M qualified spend\n"
        "- 75% of shooting days in New York\n"
        "- Non-competitive â€” credits issued as earned\n\n"
        "**Max credit:** $7M per project. Applications accepted year-round."
    )),
    (["new mexico", " nm "], (
        "**New Mexico Film Production Tax Credit**\n\n"
        "New Mexico offers a **25â€“35% refundable credit** â€” one of the most competitive programs in the US:\n\n"
        "**Base credit:** 25% on all qualified production expenditures (QPF)\n"
        "**Rural uplift:** +5% for productions shooting 60+ miles outside Santa Fe or Albuquerque city limits\n"
        "**TV series uplift:** +5% for scripted series of 6+ consecutive episodes with significant NM spend\n\n"
        "**No minimum spend threshold** â€” accessible to indie and large-budget productions alike. "
        "Credits are fully **refundable** (the state pays the difference as cash even with no NM tax liability).\n\n"
        "Administered by the New Mexico Film Office (nmfilm.com)."
    )),
    (["louisiana", " la "], (
        "**Louisiana Entertainment Tax Credit**\n\n"
        "Louisiana offers a **25% base rebate** on total qualified production expenditures.\n\n"
        "**Stackable bonuses:**\n"
        "- **+15% resident payroll** uplift on wages paid to Louisiana residents\n"
        "- **+5% music content bonus** for productions with 50%+ Louisiana-sourced music\n"
        "- **VFX bonus:** additional incentive for qualifying visual effects work\n\n"
        "**Requirements:** Minimum $300k qualified spend.\n\n"
        "Credits are **fully transferable** and can be sold at 85â€“90 cents on the dollar for "
        "immediate cash â€” ideal for productions without significant Louisiana tax liability.\n\n"
        "Applications handled by the Louisiana Office of Entertainment Industry Development."
    )),
    (["texas", " tx "], (
        "**Texas Moving Image Industry Incentive Program**\n\n"
        "Texas offers a **grant program** (not a tax credit) on qualified in-state spend:\n\n"
        "**Grant rates:**\n"
        "- **15% base** on qualified Texas production expenditures\n"
        "- **+2.5%** for productions in underrepresented regions\n"
        "- **+2.5% workforce bonus** for 70%+ Texas-resident crew\n"
        "- **+2.5% TV bonus** for scripted series, 30+ minutes per episode\n\n"
        "**Minimum spend:** $250k for films; $100k for TV episodes.\n\n"
        "**Local stacking:** San Antonio offers an additional **14% local incentive**, bringing the "
        "combined maximum to **36.5%** on fully qualified spend. "
        "Houston and Austin have local film commissions with permit support."
    )),
    (["san antonio", "tx-sa", "sanantonio"], (
        "**San Antonio Local Production Incentive**\n\n"
        "The City of San Antonio offers a **14% local production incentive** through Film San Antonio (filmsanantonio.com).\n\n"
        "**Stacking with Texas state:**\n"
        "- Texas base grant: up to 22.5%\n"
        "- San Antonio local: 14%\n"
        "- **Combined maximum: 36.5%** on fully qualified spend\n\n"
        "*Note: filmsanantonio.com promotes \"up to 45% combined\" â€” the verified math is 14% + 22.5% = 36.5%. "
        "Always use the conservative figure for budgeting.*\n\n"
        "**Permit requirement:** Productions shooting on any of 250+ City of San Antonio-owned properties "
        "must obtain a film permit through the San Antonio Film Commission."
    )),
    (["uk", "united kingdom", "avec", "bfi"], (
        "**UK Audio-Visual Expenditure Credit (AVEC)**\n\n"
        "The UK replaced its old Film Tax Relief with AVEC in January 2024. The new rate is "
        "**34% on qualifying UK core expenditure** (QUCE) â€” up from the previous 25%.\n\n"
        "**Requirements:**\n"
        "- Pass the BFI Cultural Test (minimum 18/35 points)\n"
        "- At least 10% of core expenditure must be UK spend\n"
        "- No minimum spend threshold\n\n"
        "**Rates by category:**\n"
        "- Film & High-End TV (â‰¥ Â£1M/episode): **34%**\n"
        "- Animation & Children's TV: **39%**\n\n"
        "The credit is payable through HMRC and can be claimed during or after production."
    )),
    (["canada", "british columbia", " bc ", "ontario", "quebec", " qc "], (
        "**Canadian Provincial Film Incentives**\n\n"
        "Canada's three largest provinces offer some of the world's strongest credits:\n\n"
        "**British Columbia:** 28% basic production services tax credit + 6% distant location bonus\n"
        "**Ontario:** 21.5% OFTTC + 18% OPSTC for foreign productions â€” stackable\n"
        "**Quebec:** 20% QPSP on all eligible Quebec spend; 32% on Quebec resident labor\n\n"
        "All provinces offer additional bonuses for visual effects, animation, and regional shoots."
    )),
    (["australia", " au "], (
        "**Australian Screen Production Incentive**\n\n"
        "Australia offers two complementary programs:\n\n"
        "**Producer Offset:** 40% for Australian feature films; 20% for TV/SVOD\n"
        "**Location Offset:** 16.5% for large-budget foreign productions (min AUD $15M)\n"
        "**PDV Offset:** 30% for post, digital & VFX work (min AUD $500k)\n\n"
        "Offsets are refundable tax rebates administered by Screen Australia. "
        "The Location Offset can be stacked with state-level incentives."
    )),
    (["colorado", " co "], (
        "**Colorado Film Incentive Program**\n\n"
        "Colorado offers a **20% cash rebate** on qualified Colorado production expenditures.\n\n"
        "**Requirements:**\n"
        "- Minimum $100K qualified Colorado spend\n"
        "- Administered by the Colorado Office of Film, Television and Media (coloradofilm.org)\n"
        "- No annual program cap\n\n"
        "**Local support:** Denver Film Commission, Boulder, and Colorado Springs all have local film offices "
        "providing permits and location services. Colorado's mountain scenery, urban Denver, and diverse "
        "landscapes make it a versatile production destination."
    )),
    (["hawaii", " hi "], (
        "**Hawaii Film Production Tax Credit**\n\n"
        "Hawaii offers a **20â€“25% refundable tax credit** on qualified Hawaii expenditures.\n\n"
        "**Rates:**\n"
        "- **20%** for productions on Oahu (Honolulu)\n"
        "- **25%** for productions on neighbor islands (Maui, Big Island, Kauai) â€” +5% uplift\n\n"
        "**Requirements:**\n"
        "- No minimum spend threshold\n"
        "- Must be a qualified production (film, TV, commercial, digital media)\n"
        "- Credits are refundable â€” paid as cash if they exceed Hawaii tax liability\n\n"
        "Administered by the Hawaii Film Office (filmoffice.hawaii.gov)."
    )),
    (["illinois", " il "], (
        "**Illinois Film Services Tax Credit**\n\n"
        "Illinois offers a **30â€“45% refundable tax credit** â€” one of the highest rates in the US with **no credit cap**.\n\n"
        "**Base rate:** 30% on all Illinois qualified production expenditures\n"
        "**Bonuses (stackable):**\n"
        "- **+5%** Illinois Film Green Sustainability Plan compliance\n"
        "- **+5%** Relocation series bonus for productions relocating to Illinois\n\n"
        "**Requirements:** Minimum $50K qualified spend. Cook County (Chicago) has additional "
        "local production support through the Chicago Film Office.\n\n"
        "Administered by the Illinois Film Office (film.illinois.gov)."
    )),
    (["michigan", " mi "], (
        "**Michigan Film Production Incentive**\n\n"
        "Michigan offers a **30% rebate** on qualified Michigan production expenditures.\n\n"
        "**Requirements:**\n"
        "- Minimum $50K qualified Michigan spend\n"
        "- Rebate is refundable â€” paid as cash\n"
        "- Must register with the Michigan Film Office before principal photography\n\n"
        "**Detroit** has an active local film commission with studio infrastructure. "
        "Grand Rapids (Film GR) provides West Michigan production support.\n\n"
        "Administered by the Michigan Film Office (michiganfilmoffice.org)."
    )),
    (["mississippi", " ms "], (
        "**Mississippi Film Incentive**\n\n"
        "Mississippi offers a **25% base rebate + 10% resident payroll bonus** on qualified spend.\n\n"
        "**Combined maximum: 35%** on wages paid to Mississippi residents.\n\n"
        "**Requirements:**\n"
        "- Minimum $50K qualified Mississippi spend\n"
        "- Rebates are refundable\n\n"
        "Mississippi's historic locations (Natchez, Gulf Coast, Jackson) and low production costs "
        "make it an attractive destination for period dramas and indie features.\n\n"
        "Administered by Film Mississippi (filmmississippi.org)."
    )),
    (["montana", " mt "], (
        "**Montana Media Production Tax Credit**\n\n"
        "Montana offers a **35% labor-based tax credit** on qualified Montana wages and compensation.\n\n"
        "**Requirements:**\n"
        "- Minimum $50K qualified Montana labor spend\n"
        "- Credit applies to wages paid to Montana residents and non-residents working in Montana\n"
        "- Refundable credit\n\n"
        "Montana's vast wilderness, Glacier National Park adjacent locations, and low costs "
        "make it popular for westerns, outdoor adventures, and nature documentaries. "
        "Key hubs: Billings, Missoula, and Bozeman.\n\n"
        "Administered by the Montana Film Office (montanafilm.com)."
    )),
    (["new jersey", " nj "], (
        "**New Jersey Film Tax Credit**\n\n"
        "New Jersey offers a **30â€“35% refundable tax credit** on qualified New Jersey expenditures.\n\n"
        "**Base rate:** 30% on all qualified NJ production spend\n"
        "**Diversity bonus:** +5% for productions that meet NJ diversity and inclusion criteria\n\n"
        "**Requirements:**\n"
        "- Minimum $1M qualified NJ spend\n"
        "- 60% of principal photography must be in New Jersey\n\n"
        "**Key locations:** Jersey City (NYC skyline backdrop), Newark, Atlantic City, Pine Barrens. "
        "NJ is in proximity to NYC studios and has competitive rates relative to New York.\n\n"
        "Administered by the NJ Motion Picture Television Commission (njfilmoffice.com)."
    )),
    (["oregon", " or "], (
        "**Oregon Production Investment Fund (OPIF)**\n\n"
        "Oregon offers a **20% rebate** on qualified Oregon production expenditures.\n\n"
        "**Requirements:**\n"
        "- Minimum $75K qualified Oregon spend (reduced to $1K for Oregon-based companies)\n"
        "- Rebate paid after completion and audit\n"
        "- Program has an annual budget cap â€” apply early in the fiscal year\n\n"
        "Portland has an active film office (portland.gov/film) supporting urban and Pacific Northwest shoots. "
        "Oregon's diverse landscapes (coast, mountains, high desert, old-growth forest) support a wide range of productions.\n\n"
        "Administered by Oregon Film (oregonfilm.org)."
    )),
    (["pennsylvania", " pa "], (
        "**Pennsylvania Film Production Tax Credit**\n\n"
        "Pennsylvania offers a **25% transferable tax credit** on qualified Pennsylvania expenditures.\n\n"
        "**Requirements:**\n"
        "- Minimum $100K qualified PA spend\n"
        "- 60% of total production budget must be spent in Pennsylvania\n"
        "- Credits are transferable â€” can be sold to PA taxpayers\n\n"
        "**Key locations:** Philadelphia (PA-PHILADELPHIA film office), Pittsburgh, Lancaster County. "
        "Philadelphia's diverse architecture and proximity to New York make it a popular NYC stand-in.\n\n"
        "Administered by the Pennsylvania Film Office (filmpa.com)."
    )),
    (["virginia", " va "], (
        "**Virginia Film Tax Credit**\n\n"
        "Virginia offers a **20â€“30% refundable tax credit** on qualified Virginia expenditures.\n\n"
        "**Base rate:** 20% on all qualified Virginia production spend\n"
        "**Rural enhanced credit:** +10% for productions shooting in qualifying rural Virginia areas "
        "(Shenandoah Valley, Southwest Virginia, Eastern Shore)\n\n"
        "**Requirements:**\n"
        "- Minimum $250K qualified Virginia spend\n"
        "- No annual credit cap\n\n"
        "**Key locations:** Richmond (historic architecture), Virginia Beach (coast + military), "
        "Northern Virginia (DC proximity), Shenandoah Valley (Blue Ridge scenery).\n\n"
        "Administered by the Virginia Film Office (film.virginia.org)."
    )),
    (["highest", "best", "compare", "which jurisd", "top state", "most competitive"], (
        "**Top Film Incentive Jurisdictions â€” 2026**\n\n"
        "| Jurisdiction | Rate | Min Spend | Notes |\n"
        "|---|---|---|---|\n"
        "| New Mexico | 25â€“40% | None | Fully refundable; TV series bonus |\n"
        "| New Zealand | 40% | NZD $15M | NZSPG grant |\n"
        "| UK | 34% | None | AVEC â€” cultural test (raised from 25%) |\n"
        "| Montana | 35% | $50K | Labor-based credit |\n"
        "| Ireland | 32% | None | Section 481 |\n"
        "| Illinois | 30â€“45% | $50K | No credit cap |\n"
        "| Georgia | 20â€“30% | $500K | Logo bonus available |\n"
        "| Louisiana | 25%+15% | $300K | Transferable credits |\n"
        "| New York | 25â€“35% | $1M | Upstate bonus |\n"
        "| California | 25% | $1M | $330M annual allocation |\n\n"
        "The best jurisdiction depends on your budget, shooting locations, and crew residency. "
        "SceneIQ's calculator can run a side-by-side comparison for your specific production."
    )),
    (["stack", "federal", "section 181", "181 "], (
        "**Stacking Federal + State Incentives**\n\n"
        "**Section 181 (Federal):** Allows 100% first-year deduction for productions up to $15M "
        "($20M in qualifying low-income communities). No application required â€” taken on your federal return.\n\n"
        "**How stacking works:**\n"
        "1. Section 181 reduces your federal taxable income\n"
        "2. State tax credit directly offsets your state tax liability\n"
        "3. Both are claimed independently â€” they don't reduce each other\n\n"
        "**Example:** A $5M production in Georgia could claim 181 federally AND the 30% Georgia "
        "credit â€” effectively double-dipping on a legitimate, IRS-sanctioned basis."
    )),
    (["document", "application", "require", "checklist", "submit"], (
        "**Standard Application Requirements**\n\n"
        "**Pre-production (file before shooting):**\n"
        "- Production company registration in the state\n"
        "- Estimated budget with expense category breakdown\n"
        "- Shooting schedule with location-days by county\n"
        "- Proof of financing (bank letter or equity commitment)\n\n"
        "**Post-production (file after final delivery):**\n"
        "- Final cost report certified by a CPA\n"
        "- Payroll records with residency verification for each crew member\n"
        "- Vendor invoices for all qualified expenditures\n"
        "- SAG/AFTRA contracts (if applicable)\n\n"
        "Most states allow electronic filing. Allow 60â€“120 days for credit certification."
    )),
    (["ireland", " ie ", "section 481"], (
        "**Ireland Section 481 Film Tax Credit**\n\n"
        "Ireland offers a **32% credit** on eligible Irish expenditure â€” one of the highest rates in Europe.\n\n"
        "**Requirements:**\n"
        "- No minimum spend threshold\n"
        "- Production must have cultural or creative merit\n"
        "- At least some Irish-resident crew required\n\n"
        "The credit applies to features, animation, TV series, and documentaries. "
        "Ireland also offers additional regional incentives through regional uplift schemes."
    )),
    (["minimum spend", "threshold", "minimum budget"], (
        "**Minimum Spend Requirements by Jurisdiction**\n\n"
        "| Jurisdiction | Minimum Spend |\n"
        "|---|---|\n"
        "| New Mexico | None |\n"
        "| Ireland | None |\n"
        "| UK | 10% UK spend (no $ floor) |\n"
        "| Montana | $50K |\n"
        "| Illinois | $50K |\n"
        "| Louisiana | $300K |\n"
        "| Georgia | $500K |\n"
        "| New York | $1M |\n"
        "| California | $1M |\n"
        "| New Zealand | NZD $15M (NZSPG) / NZD $500K (PDV) |\n"
        "| Australia | AUD $15M (Location Offset) |\n\n"
        "Lower-budget productions should prioritize states with no minimums (NM, Ireland) "
        "or low thresholds (Montana $50K, Illinois $50K, Louisiana $300K, Georgia $500K)."
    )),
]

_DEFAULT_RESPONSE = (
    "**SceneIQ AI Advisor**\n\n"
    "I'm your expert guide to film and television tax incentives across 35+ jurisdictions.\n\n"
    "I can help you with:\n\n"
    "- **Jurisdiction comparisons** â€” credit rates, caps, and eligibility across US states and international programs\n"
    "- **Qualifying expenses** â€” exactly what counts toward your incentive base in each state\n"
    "- **Application requirements** â€” documentation, timelines, and pre-certification steps\n"
    "- **Incentive stacking** â€” combining Section 181 with state credits for maximum yield\n"
    "- **Budget optimization** â€” structuring your spend to maximize the credit\n\n"
    "Try asking about Georgia, New Mexico, California, New York, Louisiana, Texas, or the UK â€” "
    "or ask me to compare jurisdictions for your specific budget."
)


def _scripted_response(question: str) -> str:
    """Return the best keyword-matched canned response for a question."""
    q = question.lower()
    for keywords, response in _SCRIPTED:
        if any(kw in q for kw in keywords):
            return response
    return _DEFAULT_RESPONSE


async def _stream_scripted(text: str) -> AsyncGenerator[str, None]:
    """Stream a scripted response word-by-word to simulate AI typing."""
    words = text.split(" ")
    chunk = ""
    for i, word in enumerate(words):
        chunk += ("" if i == 0 else " ") + word
        # Flush every 3 words for smooth streaming feel
        if (i + 1) % 3 == 0 or i == len(words) - 1:
            yield f"data: {json.dumps({'delta': chunk})}\n\n"
            chunk = ""
            await asyncio.sleep(0.03)
    yield "data: [DONE]\n\n"


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_client():
    """Return an AsyncAnthropic client, or None to use scripted demo responses."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        return anthropic.AsyncAnthropic(api_key=api_key)
    except ImportError:
        logger.warning("anthropic package not installed â€” falling back to scripted responses")
        return None


async def _build_system_prompt(production_id: Optional[str]) -> str:
    """Extend base system prompt with production context if a production is selected."""
    if not production_id:
        return SYSTEM_PROMPT

    try:
        prod = await prisma.production.find_unique(
            where={"id": production_id},
            include={"jurisdiction": True},
        )
        if prod:
            ctx = (
                f"\n\nCurrent production context:\n"
                f"- Title: {prod.title}\n"
                f"- Type: {prod.productionType}\n"
                f"- Company: {prod.productionCompany}\n"
                f"- Total Budget: ${prod.budgetTotal:,.0f}\n"
            )
            if prod.budgetQualifying:
                ctx += f"- Qualifying Budget: ${prod.budgetQualifying:,.0f}\n"
            ctx += f"- Status: {prod.status}\n"
            if hasattr(prod, "jurisdiction") and prod.jurisdiction:
                ctx += (
                    f"- Primary Jurisdiction: {prod.jurisdiction.name} "
                    f"({prod.jurisdiction.code})\n"
                )
            ctx += "\nFactor this production context into your responses when relevant."
            return SYSTEM_PROMPT + ctx
    except Exception as e:
        logger.warning(f"Could not load production context for {production_id}: {e}")

    return SYSTEM_PROMPT


async def _stream_chunks(messages: list[dict], system: str) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted text chunks. Uses Anthropic when configured, scripted fallback otherwise."""
    client = _get_client()
    if client is None:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        logger.info("ANTHROPIC_API_KEY not set â€” using scripted demo response")
        async for chunk in _stream_scripted(_scripted_response(last_user)):
            yield chunk
        return
    try:
        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'delta': text})}\n\n"
        yield "data: [DONE]\n\n"
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Anthropic streaming error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


# â”€â”€ Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/chat", summary="Streaming AI advisor chat")
async def chat(req: ChatRequest):
    """
    Proxy chat messages to Anthropic with optional production context.
    Returns a server-sent events (SSE) stream of delta chunks.
    Each chunk: `data: {"delta": "..."}\\n\\n`
    Stream end: `data: [DONE]\\n\\n`
    """
    system = await _build_system_prompt(req.production_id)
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    return StreamingResponse(
        _stream_chunks(messages, system),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/summarize-event/{event_id}",
    summary="AI-summarize a monitoring event and persist the result",
)
async def summarize_event(event_id: str):
    """
    Fetch a MonitoringEvent, send its content to Claude Haiku for a structured
    2-3 sentence summary, and store the result in `MonitoringEvent.summary`.
    Returns the updated event record.
    """
    event = await prisma.monitoringEvent.find_unique(where={"id": event_id})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    client = _get_client()
    if client is None:
        summary_text = f"Regulatory update: {event.title}. Review the source for full details on jurisdictional impact and compliance requirements."
        updated = await prisma.monitoringEvent.update(where={"id": event_id}, data={"summary": summary_text})
        return updated

    content_parts = [f"Title: {event.title}"]
    if event.summary:
        content_parts.append(f"Content: {event.summary}")
    if event.url:
        content_parts.append(f"Source URL: {event.url}")

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=SUMMARIZATION_SYSTEM,
            messages=[{"role": "user", "content": "\n".join(content_parts)}],
        )
        summary_text = response.content[0].text

        updated = await prisma.monitoringEvent.update(
            where={"id": event_id},
            data={"summary": summary_text},
        )
        logger.info(f"Summarized monitoring event {event_id}")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Event summarization failed for {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Summarization failed: {str(e)}",
        )



