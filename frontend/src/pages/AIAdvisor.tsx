import { useState, useRef, useEffect } from 'react';
import { Send, Zap, RotateCcw } from 'lucide-react';
import api from '../api';
import type { Production } from '../types';

const SUGGESTED_PROMPTS = [
  'Which jurisdiction offers the highest credit rate?',
  'What expenses qualify for the Georgia film tax credit?',
  'Compare New York vs. California incentives for a TV series.',
  'How do I stack federal and state incentives?',
  'What is the minimum spend for UK production incentives?',
  'What documentation is required for Louisiana credit applications?',
  'Compare Texas vs. New Mexico for a $5M feature film.',
  'What is the San Antonio local incentive and how does it stack with Texas state?',
  'Explain the New Mexico rural uplift zone bonus.',
  'What makes Louisiana credits transferable and how do I sell them?',
];

function getContextualPrompts(prod: Production): string[] {
  const budget = prod.budgetTotal ?? 0;
  const budgetStr = budget >= 1_000_000 ? `$${(budget / 1_000_000).toFixed(1)}M` : budget > 0 ? `$${(budget / 1_000).toFixed(0)}K` : '';
  const title = prod.title;
  const prompts: string[] = [];

  if (budgetStr) {
    prompts.push(`What is the maximum incentive available for "${title}" with a ${budgetStr} budget?`);
    prompts.push(`Which jurisdictions does "${title}" qualify for at ${budgetStr}?`);
  } else {
    prompts.push(`What incentive programs are available for "${title}"?`);
  }

  if (prod.status === 'planning') {
    prompts.push(`What should I do now to prepare "${title}" for incentive applications?`);
  } else if (prod.status === 'pre_production') {
    prompts.push(`What pre-certification steps are required for "${title}" before shooting starts?`);
  } else if (prod.status === 'production') {
    prompts.push(`What documentation should I be capturing on set for "${title}"'s incentive claim?`);
  } else if (prod.status === 'post_production') {
    prompts.push(`What is the post-production incentive filing timeline for "${title}"?`);
  }

  if (budget >= 1_000_000) {
    prompts.push(`Compare Georgia vs. New Mexico vs. Louisiana for "${title}" at ${budgetStr}.`);
  } else if (budget > 0) {
    prompts.push(`Which states have no minimum spend threshold that "${title}" would qualify for?`);
  }

  return prompts.slice(0, 4);
}

const WELCOME = `Welcome to **SceneIQ AI Advisor**. I can help you maximize tax incentives for your productions.\n\nAsk me about jurisdiction comparisons, qualifying expenses, application requirements, or incentive stacking strategies. For more targeted analysis, select a production context in the left panel.`;

const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000') as string;
const API_VERSION = (import.meta.env.VITE_API_VERSION || '0.1.0') as string;
const TOKEN_KEY = 'sceneiq_token';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  ts: Date;
}

function renderMarkdown(text: string) {
  return text.split('\n').map((line, i, arr) => {
    const isLast = i === arr.length - 1;
    const parts = line.split(/\*\*(.*?)\*\*/g);
    const bold = parts.map((p, j) => j % 2 === 1 ? <strong key={j}>{p}</strong> : p);
    return <span key={i}>{bold}{!isLast && <br />}</span>;
  });
}

function getFallbackResponse(question: string): string {
  const q = question.toLowerCase();
  if (q.includes('georgia') && (q.includes('expens') || q.includes('qualif')))
    return "**Georgia Qualifying Expenses**\n\nGeorgia's Entertainment Industry Investment Act covers:\n\n**Eligible:** Below-the-line labor, equipment rentals, location fees, catering, post-production, and set construction.\n\n**Excluded:** Story rights, music rights, above-the-line compensation (unless resident).\n\nMinimum $500k qualified spend. Georgia residents earn an additional 10% uplift on their wages. The base credit is 20%, rising to 30% with the Georgia promotional logo.";
  if (q.includes('california') || q.includes(' ca ') || q.includes('ca film'))
    return "**California Film Tax Credit 3.0**\n\nCalifornia offers a **competitive 25% credit** on qualified expenditures.\n\n**Requirements:**\n- Minimum $1M qualified spend\n- 75% of shooting days must be in California\n- Competitive application — credits are allocated by scoring\n\n**Eligible expenses:** Below-the-line labor, equipment, locations, post-production.\n\n**Max credit:** $25M per project.";
  if (q.includes('new york') || q.includes(' ny '))
    return "**New York Film Tax Credit**\n\nNew York provides a **25-35% credit** on qualified below-the-line costs.\n\n**Base rate:** 25% statewide\n**Upstate bonus:** Additional 10% for productions outside NYC\n\n**Requirements:**\n- Minimum $1M qualified spend\n- 75% of shooting days in New York\n- Non-competitive — credits issued as earned\n\n**Max credit:** $7M per project.";
  if (q.includes('highest') || q.includes('best') || q.includes('compare') || q.includes('which'))
    return "**Top US Film Incentive Jurisdictions**\n\n**Georgia:** 20-30% · Min $500k · Best for horror/indie\n**New Mexico:** 25-40% · No minimum · Best for large features\n**Louisiana:** 25% rebate · Min $300k · Transferable credits\n**New York:** 25-35% · Min $1M · Best for TV series\n**California:** 25% · Min $1M · Competitive allocation";
  if (q.includes('new mexico') || q.includes(' nm '))
    return "**New Mexico Film Production Tax Credit**\n\nNew Mexico offers a **25–35% refundable credit** — one of the most competitive programs in the US.\n\n**Base credit:** 25% on all qualified production expenditures (QPF)\n**Rural uplift:** +5% for productions shooting 60+ miles outside Santa Fe or Albuquerque city limits\n**TV series uplift:** +5% for scripted series of 6+ consecutive episodes with significant NM spend\n\n**No minimum spend threshold** — accessible to indie and large-budget productions alike.\n\nCredits are **refundable** (paid as cash if they exceed your tax liability). Administered by the New Mexico Film Office.";
  if (q.includes('louisiana') || q.includes(' la '))
    return "**Louisiana Entertainment Tax Credit**\n\nLouisiana offers a **25% base rebate** on total qualified production expenditures.\n\n**Stackable bonuses:**\n- **+15% resident payroll** uplift on wages paid to Louisiana residents\n- **+5% music content bonus** for productions with 50%+ Louisiana-sourced music\n- **VFX bonus:** additional incentive available for qualifying visual effects work\n\n**Requirements:** Minimum $300k qualified spend.\n\n**Transferability:** Credits are fully transferable and can be sold at 85–90 cents on the dollar for immediate cash — attractive for productions without significant Louisiana tax liability.";
  if (q.includes('texas') || q.includes(' tx '))
    return "**Texas Moving Image Industry Incentive Program**\n\nTexas offers a **grant program** (not a tax credit) on qualified in-state spend.\n\n**Grant rates:**\n- **15% base** on qualified Texas production expenditures\n- **+2.5% bonus** for productions in underrepresented regions\n- **+2.5% workforce bonus** for 70%+ Texas-resident crew\n- **+2.5% TV bonus** for scripted series 30+ minutes per episode\n\n**Minimum spend:** $250k for films; $100k for TV episodes.\n\n**Local stacking:** San Antonio offers an additional **14% local incentive** (opt-in), bringing the combined maximum to 36.5% on fully qualified spend. Houston and Austin have local film commissions with permit support.";
  if (q.includes('san antonio') || q.includes('tx-sa') || q.includes('sanantonio'))
    return "**San Antonio Local Production Incentive**\n\nThe City of San Antonio offers a **14% local production incentive** through Film San Antonio (filmsanantonio.com).\n\n**Stacking with Texas state:**\n- Texas base grant: up to 22.5%\n- San Antonio local: 14%\n- **Combined maximum: 36.5%** on fully qualified spend\n\n*Note: filmsanantonio.com promotes \"up to 45% combined\" — the verified math is 14% + 22.5% = 36.5%. Always use the conservative figure for budgeting.*\n\n**Permit requirement:** Productions shooting on any of 250+ City of San Antonio-owned properties must obtain a film permit through the San Antonio Film Commission.";
  if (q.includes('uk') || q.includes('united kingdom'))
    return "**UK Film Tax Relief**\n\nThe UK offers **25% on qualifying UK production expenditure**.\n\n**Requirements:**\n- Pass the BFI Cultural Test (minimum 18/35 points)\n- At least 10% of core expenditure must be UK spend\n- No minimum spend threshold";
  if (q.includes('stack') || q.includes('federal') || q.includes('181'))
    return "**Stacking Federal + State Incentives**\n\n**Section 181 (Federal):** 100% first-year deduction for productions up to $15M. No application required.\n\n**State credits:** Apply on top of Section 181. The federal deduction reduces taxable income; the state credit directly offsets tax liability.";
  if (q.includes('document') || q.includes('application') || q.includes('require'))
    return "**Standard Application Requirements**\n\n**Pre-production:**\n- Production company registration in the state\n- Estimated budget breakdown\n- Shooting schedule with location days\n\n**Post-production:**\n- Final cost report (CPA-certified)\n- Payroll records with residency verification\n- Vendor invoices for all qualified spend";
  return "**SceneIQ AI Advisor**\n\nI can help you with:\n\n- **Jurisdiction comparisons** — rates across 35+ states and countries\n- **Qualifying expenses** — what counts toward your incentive base\n- **Application requirements** — documentation, timelines, pre-certification\n- **Incentive stacking** — combining federal Section 181 with state credits\n\nTry asking about Georgia, California, New York, Louisiana, Texas, New Mexico, or the UK.";
}

function AIAdvisor() {
  const [messages, setMessages] = useState<Message[]>([{ id: '0', role: 'assistant', content: WELCOME, ts: new Date() }]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [production, setProd] = useState('none');
  const [productions, setProductions] = useState<Production[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => { api.productions.list().then(data => setProductions(Array.isArray(data) ? data : [])).catch(() => {}); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, typing]);

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || typing) return;
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: trimmed, ts: new Date() };
    const historyForApi = [...messages.filter(m => m.id !== '0'), userMsg].map(m => ({ role: m.role, content: m.content }));
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setTyping(true);
    const assistantId = (Date.now() + 1).toString();
    const assistantTs = new Date();
    let content = '';
    let firstChunk = true;
    const abort = new AbortController();
    abortRef.current = abort;
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const response = await fetch(`${API_BASE}/api/${API_VERSION}/advisor/chat`, {
        method: 'POST', signal: abort.signal,
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ messages: historyForApi, production_id: production !== 'none' ? production : undefined }),
      });
      if (!response.ok) { const err = await response.json().catch(() => ({})); throw new Error((err as { detail?: string }).detail ?? `HTTP ${response.status}`); }
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6);
          if (payload === '[DONE]') break;
          try {
            const parsed = JSON.parse(payload) as { delta?: string; error?: string };
            if (parsed.error) throw new Error(parsed.error);
            if (parsed.delta) {
              content += parsed.delta;
              if (firstChunk) { firstChunk = false; setTyping(false); setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content, ts: assistantTs }]); }
              else { setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content } : m)); }
            }
          } catch (parseErr) { if ((parseErr as Error).message !== 'Unexpected end of JSON input') throw parseErr; }
        }
      }
      if (firstChunk) { setTyping(false); setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: getFallbackResponse(trimmed), ts: assistantTs }]); }
    } catch (err: unknown) {
      if ((err as { name?: string }).name === 'AbortError') return;
      setTyping(false);
      setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: getFallbackResponse(trimmed), ts: assistantTs }]);
    } finally { abortRef.current = null; }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }
  function handleClear() { abortRef.current?.abort(); setMessages([{ id: '0', role: 'assistant', content: WELCOME, ts: new Date() }]); setInput(''); setTyping(false); }
  const fmt = (d: Date) => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="flex gap-6 h-full min-h-0">
      <div className="w-72 shrink-0 flex flex-col gap-4">
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-2">Production Context</p>
          <select value={production} onChange={e => setProd(e.target.value)} title="Production context" aria-label="Production context" className="select-arrow w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none">
            <option value="none">No production selected</option>
            {productions.map(p => <option key={p.id} value={p.id}>{p.title}{p.budgetTotal ? ` — $${(p.budgetTotal / 1_000_000).toFixed(1)}M` : ''}</option>)}
          </select>
        </div>
        {production !== 'none' && (() => {
          const selectedProd = productions.find(p => p.id === production);
          if (!selectedProd) return null;
          const ctxPrompts = getContextualPrompts(selectedProd);
          return (
            <div className="bg-blue-50 rounded-2xl border border-blue-100 shadow-sm p-5">
              <p className="text-[11px] font-bold text-blue-400 tracking-widest uppercase mb-3">Production Questions</p>
              <div className="space-y-2">
                {ctxPrompts.map(prompt => (
                  <button key={prompt} type="button" onClick={() => sendMessage(prompt)} disabled={typing} className="w-full text-left text-xs text-blue-700 bg-white hover:bg-blue-600 hover:text-white border border-blue-100 hover:border-blue-600 rounded-lg px-3 py-2.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-relaxed">{prompt}</button>
                ))}
              </div>
            </div>
          );
        })()}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-3">Suggested Questions</p>
          <div className="space-y-2">
            {SUGGESTED_PROMPTS.map(prompt => (
              <button key={prompt} type="button" onClick={() => sendMessage(prompt)} disabled={typing} className="w-full text-left text-xs text-slate-600 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 border border-slate-100 hover:border-blue-200 rounded-lg px-3 py-2.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-relaxed">{prompt}</button>
            ))}
          </div>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed px-1">AI Advisor provides estimates for planning purposes only. Consult a qualified production accountant for final tax decisions.</p>
      </div>
      <div className="flex-1 flex flex-col min-w-0 bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center"><Zap className="w-4 h-4 text-white" strokeWidth={2.5} /></div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">AI Advisor</h2>
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${typing ? 'bg-amber-400 animate-pulse' : 'bg-emerald-500'}`} />
                <span className="text-xs text-slate-400">{typing ? 'Thinking…' : 'Ready'}</span>
              </div>
            </div>
          </div>
          <button type="button" onClick={handleClear} title="Clear conversation" aria-label="Clear conversation" className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            <RotateCcw className="w-3.5 h-3.5" />Clear
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5 min-h-0">
          {messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${msg.role === 'assistant' ? 'bg-blue-600' : 'bg-slate-200'}`}>
                {msg.role === 'assistant' ? <Zap className="w-3.5 h-3.5 text-white" strokeWidth={2.5} /> : <span className="text-[10px] font-bold text-slate-500">YOU</span>}
              </div>
              <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${msg.role === 'assistant' ? 'bg-slate-50 text-slate-800 rounded-tl-sm' : 'bg-blue-600 text-white rounded-tr-sm'}`}>
                {renderMarkdown(msg.content)}
                <p className={`text-[10px] mt-2 ${msg.role === 'assistant' ? 'text-slate-400' : 'text-blue-200'}`}>{fmt(msg.ts)}</p>
              </div>
            </div>
          ))}
          {typing && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center shrink-0 mt-0.5"><Zap className="w-3.5 h-3.5 text-white" strokeWidth={2.5} /></div>
              <div className="bg-slate-50 rounded-2xl rounded-tl-sm px-4 py-3.5 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="px-6 py-4 border-t border-slate-100 shrink-0">
          <div className="flex gap-3 items-end">
            <textarea rows={2} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="Ask about tax incentives, qualifying expenses, jurisdictions…" disabled={typing} className="flex-1 px-4 py-3 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none disabled:opacity-50" />
            <button type="button" onClick={() => sendMessage(input)} disabled={!input.trim() || typing} title="Send message" aria-label="Send message" className="p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"><Send className="w-4 h-4" /></button>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Enter to send · Shift+Enter for new line</p>
        </div>
      </div>
    </div>
  );
}

export default AIAdvisor;
