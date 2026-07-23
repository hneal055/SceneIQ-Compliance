import { useState, useMemo } from 'react';

/**
 * USJurisdictionMap — Interactive US map color-coded by film incentive programs.
 *
 * Props:
 *   jurisdictions: array of { id, name, code, active, type } from the API
 *   onSelect: callback when a state is clicked, receives the jurisdiction code
 *
 * States with active incentives are colored by tier:
 *   Tier 1 (strong programs): CA, GA, NY, NM, LA — dark blue
 *   Tier 2 (solid programs): IL, TX, PA, NJ, NC, etc. — medium blue
 *   Tier 3 (available programs): remaining active states — light blue
 *   No program: gray
 */

interface Jurisdiction {
  id: string;
  name: string;
  code: string;
  active?: boolean;
  type?: string;
}

interface Props {
  jurisdictions: Jurisdiction[];
  onSelect?: (code: string) => void;
}

// Tier assignments based on program strength
const TIER1 = new Set(['CA', 'GA', 'NY', 'NM', 'LA']);
const TIER2 = new Set(['IL', 'TX', 'PA', 'NJ', 'NC', 'CT', 'MA', 'CO', 'OK', 'OR', 'NV', 'MN', 'VA', 'SC', 'TN', 'AL', 'AR', 'MS']);
// Everything else active = Tier 3

const COLORS = {
  tier1: '#1A1A2E',    // SceneIQ dark
  tier2: '#2D4A7A',    // medium blue
  tier3: '#6B8DB9',    // light blue
  inactive: '#D1D5DB', // gray
  hover: '#C9973A',    // SceneIQ gold
  stroke: '#FFFFFF',
  text: '#FFFFFF',
};

// Simplified SVG paths for US states (viewBox 0 0 960 600)
const STATE_PATHS: Record<string, { d: string; labelX: number; labelY: number }> = {
  AL: { d: 'M628,425 L628,468 L616,489 L621,495 L641,494 L647,466 L651,425Z', labelX: 635, labelY: 455 },
  AK: { d: 'M161,485 L131,540 L182,565 L230,540 L230,510 L200,485Z', labelX: 180, labelY: 520 },
  AZ: { d: 'M205,410 L205,490 L265,490 L275,445 L260,395 L215,395Z', labelX: 238, labelY: 445 },
  AR: { d: 'M565,430 L565,470 L618,470 L618,425 L580,420Z', labelX: 590, labelY: 447 },
  CA: { d: 'M110,280 L100,350 L120,420 L150,470 L195,480 L205,410 L200,340 L175,270 L145,250Z', labelX: 148, labelY: 370 },
  CO: { d: 'M280,310 L280,370 L370,370 L370,310Z', labelX: 325, labelY: 342 },
  CT: { d: 'M845,195 L845,215 L870,210 L870,195Z', labelX: 855, labelY: 205 },
  DE: { d: 'M810,280 L810,305 L820,305 L825,285Z', labelX: 815, labelY: 295 },
  FL: { d: 'M660,490 L660,510 L680,560 L710,575 L730,550 L725,505 L700,490 L675,490Z', labelX: 700, labelY: 530 },
  GA: { d: 'M660,415 L650,425 L647,466 L641,494 L660,490 L700,490 L700,440 L685,415Z', labelX: 672, labelY: 455 },
  HI: { d: 'M270,510 L270,540 L310,540 L310,520 L290,510Z', labelX: 290, labelY: 525 },
  ID: { d: 'M215,145 L200,210 L210,270 L245,280 L260,230 L255,170 L235,130Z', labelX: 230, labelY: 210 },
  IL: { d: 'M580,265 L570,290 L565,340 L580,380 L600,380 L610,345 L610,290 L600,265Z', labelX: 587, labelY: 325 },
  IN: { d: 'M610,275 L610,345 L640,350 L650,310 L640,275Z', labelX: 628, labelY: 312 },
  IA: { d: 'M510,250 L510,300 L575,300 L580,265 L555,245 L525,240Z', labelX: 542, labelY: 270 },
  KS: { d: 'M400,340 L400,390 L510,390 L510,340Z', labelX: 455, labelY: 367 },
  KY: { d: 'M610,345 L605,375 L630,395 L685,380 L700,355 L660,340 L640,350Z', labelX: 650, labelY: 367 },
  LA: { d: 'M565,470 L565,520 L610,530 L620,500 L618,470Z', labelX: 590, labelY: 500 },
  ME: { d: 'M880,95 L870,120 L885,160 L900,140 L905,110Z', labelX: 888, labelY: 130 },
  MD: { d: 'M780,280 L780,305 L810,305 L810,280 L795,270Z', labelX: 795, labelY: 292 },
  MA: { d: 'M845,180 L845,195 L885,190 L885,175Z', labelX: 862, labelY: 187 },
  MI: { d: 'M600,180 L585,210 L590,255 L620,260 L650,230 L640,190 L620,175Z', labelX: 618, labelY: 225 },
  MN: { d: 'M480,120 L480,210 L540,210 L545,170 L530,120Z', labelX: 510, labelY: 165 },
  MS: { d: 'M596,430 L596,490 L616,489 L618,470 L618,425 L610,420Z', labelX: 608, labelY: 460 },
  MO: { d: 'M510,325 L510,390 L565,395 L580,380 L565,340 L545,315Z', labelX: 542, labelY: 362 },
  MT: { d: 'M255,100 L255,170 L370,170 L375,120 L340,100Z', labelX: 312, labelY: 135 },
  NE: { d: 'M370,270 L370,310 L480,310 L490,280 L440,265Z', labelX: 430, labelY: 290 },
  NV: { d: 'M175,250 L170,330 L200,380 L210,340 L215,270 L200,250Z', labelX: 192, labelY: 310 },
  NH: { d: 'M865,120 L860,160 L875,165 L880,130Z', labelX: 870, labelY: 145 },
  NJ: { d: 'M820,235 L815,265 L825,285 L835,265 L830,240Z', labelX: 825, labelY: 260 },
  NM: { d: 'M260,395 L260,480 L350,480 L355,395Z', labelX: 305, labelY: 440 },
  NY: { d: 'M780,165 L775,200 L810,220 L845,195 L845,180 L820,165Z', labelX: 810, labelY: 195 },
  NC: { d: 'M685,370 L685,400 L770,395 L790,375 L760,365 L720,365Z', labelX: 735, labelY: 383 },
  ND: { d: 'M375,120 L375,170 L480,170 L480,120Z', labelX: 427, labelY: 147 },
  OH: { d: 'M650,265 L640,310 L660,340 L700,335 L710,300 L695,265Z', labelX: 672, labelY: 300 },
  OK: { d: 'M370,390 L370,430 L420,445 L510,445 L510,390Z', labelX: 450, labelY: 420 },
  OR: { d: 'M110,145 L105,210 L170,220 L200,210 L215,165 L180,130 L140,130Z', labelX: 155, labelY: 175 },
  PA: { d: 'M720,230 L720,275 L810,275 L815,250 L810,225 L760,225Z', labelX: 765, labelY: 252 },
  RI: { d: 'M870,200 L870,213 L880,210 L878,198Z', labelX: 874, labelY: 207 },
  SC: { d: 'M700,400 L690,430 L720,445 L750,420 L740,395Z', labelX: 720, labelY: 420 },
  SD: { d: 'M375,170 L375,230 L480,230 L480,170Z', labelX: 427, labelY: 200 },
  TN: { d: 'M605,380 L605,410 L700,400 L700,370 L685,380 L630,395Z', labelX: 652, labelY: 395 },
  TX: { d: 'M350,420 L340,490 L370,540 L420,560 L480,540 L510,490 L510,445 L420,445 L370,430Z', labelX: 430, labelY: 490 },
  UT: { d: 'M230,270 L225,350 L280,355 L280,310 L260,270Z', labelX: 252, labelY: 315 },
  VT: { d: 'M845,120 L840,160 L860,160 L865,120Z', labelX: 852, labelY: 140 },
  VA: { d: 'M700,310 L700,355 L720,365 L760,365 L790,340 L780,310 L740,310Z', labelX: 740, labelY: 338 },
  WA: { d: 'M135,70 L130,130 L195,145 L215,145 L210,110 L175,70Z', labelX: 170, labelY: 110 },
  WV: { d: 'M710,290 L700,310 L710,340 L740,345 L750,320 L730,290Z', labelX: 725, labelY: 318 },
  WI: { d: 'M540,160 L530,210 L570,225 L590,210 L600,175 L575,155Z', labelX: 565, labelY: 190 },
  WY: { d: 'M260,190 L255,260 L355,265 L360,195 L320,185Z', labelX: 308, labelY: 228 },
};

export default function USJurisdictionMap({ jurisdictions, onSelect }: Props) {
  const [hoveredState, setHoveredState] = useState<string | null>(null);
  const [selectedState, setSelectedState] = useState<string | null>(null);

  // Build code -> jurisdiction lookup
  const jurMap = useMemo(() => {
    const map: Record<string, Jurisdiction> = {};
    for (const j of jurisdictions) {
      if (j.code && j.type === 'state') {
        map[j.code] = j;
      }
    }
    return map;
  }, [jurisdictions]);

  // Active state codes from platform
  const activeCodes = useMemo(() => {
    return new Set(jurisdictions.filter(j => j.type === 'state' && j.active !== false).map(j => j.code));
  }, [jurisdictions]);

  function getColor(code: string): string {
    if (hoveredState === code) return COLORS.hover;
    if (!activeCodes.has(code)) return COLORS.inactive;
    if (TIER1.has(code)) return COLORS.tier1;
    if (TIER2.has(code)) return COLORS.tier2;
    return COLORS.tier3;
  }

  function handleClick(code: string) {
    setSelectedState(code);
    onSelect?.(code);
  }

  const selectedJur = selectedState ? jurMap[selectedState] : null;

  return (
    <div style={{ marginBottom: '32px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
      }}>
        <div>
          <h2 style={{
            fontSize: '20px',
            fontWeight: 700,
            color: '#1A1A2E',
            margin: 0,
          }}>
            Jurisdiction Intelligence
          </h2>
          <p style={{
            fontSize: '13px',
            color: '#6B7280',
            margin: '4px 0 0',
          }}>
            US film incentive coverage across {activeCodes.size} active jurisdictions
          </p>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', fontSize: '12px' }}>
          <LegendItem color={COLORS.tier1} label="Tier 1 (Major)" />
          <LegendItem color={COLORS.tier2} label="Tier 2 (Solid)" />
          <LegendItem color={COLORS.tier3} label="Tier 3 (Active)" />
          <LegendItem color={COLORS.inactive} label="No Program" />
        </div>
      </div>

      <div style={{ display: 'flex', gap: '24px' }}>
        {/* Map */}
        <div style={{
          flex: 1,
          background: '#F8FAFC',
          borderRadius: '12px',
          border: '1px solid #E2E8F0',
          padding: '16px',
          position: 'relative',
        }}>
          <svg
            viewBox="80 60 860 540"
            style={{ width: '100%', height: 'auto', maxHeight: '440px' }}
            xmlns="http://www.w3.org/2000/svg"
          >
            {Object.entries(STATE_PATHS).map(([code, { d, labelX, labelY }]) => (
              <g
                key={code}
                onClick={() => handleClick(code)}
                onMouseEnter={() => setHoveredState(code)}
                onMouseLeave={() => setHoveredState(null)}
                style={{ cursor: activeCodes.has(code) ? 'pointer' : 'default' }}
              >
                <path
                  d={d}
                  fill={getColor(code)}
                  stroke={COLORS.stroke}
                  strokeWidth={selectedState === code ? 2.5 : 1}
                  style={{
                    transition: 'fill 0.2s ease, stroke-width 0.15s ease',
                    opacity: selectedState && selectedState !== code ? 0.6 : 1,
                  }}
                />
                <text
                  x={labelX}
                  y={labelY}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill={activeCodes.has(code) ? '#FFFFFF' : '#6B7280'}
                  fontSize="11"
                  fontWeight="600"
                  fontFamily="Calibri, Arial, sans-serif"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {code}
                </text>
              </g>
            ))}
          </svg>
        </div>

        {/* Info Panel */}
        <div style={{
          width: '260px',
          background: selectedJur ? '#1A1A2E' : '#F8FAFC',
          borderRadius: '12px',
          border: `1px solid ${selectedJur ? '#1A1A2E' : '#E2E8F0'}`,
          padding: '20px',
          color: selectedJur ? '#FFFFFF' : '#6B7280',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: selectedJur ? 'flex-start' : 'center',
          alignItems: selectedJur ? 'stretch' : 'center',
          textAlign: selectedJur ? 'left' : 'center',
          minHeight: '300px',
        }}>
          {selectedJur ? (
            <>
              <div style={{ fontSize: '13px', color: '#C9973A', fontWeight: 600, marginBottom: '4px' }}>
                {selectedJur.code}
              </div>
              <div style={{ fontSize: '18px', fontWeight: 700, marginBottom: '16px' }}>
                {selectedJur.name}
              </div>
              <InfoRow label="Status" value={activeCodes.has(selectedJur.code) ? 'Active' : 'Inactive'} />
              <InfoRow
                label="Tier"
                value={
                  TIER1.has(selectedJur.code) ? 'Tier 1 - Major Program'
                  : TIER2.has(selectedJur.code) ? 'Tier 2 - Solid Program'
                  : 'Tier 3 - Active Program'
                }
              />
              <InfoRow label="Type" value="State" />
              <div style={{
                marginTop: '16px',
                paddingTop: '16px',
                borderTop: '1px solid rgba(255,255,255,0.15)',
              }}>
                <button
                  onClick={() => onSelect?.(selectedJur.code)}
                  style={{
                    width: '100%',
                    padding: '10px',
                    background: '#C9973A',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '8px',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: 'pointer',
                  }}
                >
                  View Incentive Details
                </button>
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: '40px', marginBottom: '8px' }}>&#127909;</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#374151' }}>
                Select a state
              </div>
              <div style={{ fontSize: '12px', marginTop: '4px' }}>
                Click any state to view incentive program details
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <div style={{
        width: '14px',
        height: '14px',
        borderRadius: '3px',
        background: color,
        border: '1px solid #E2E8F0',
      }} />
      <span style={{ color: '#4B5563' }}>{label}</span>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ marginBottom: '10px' }}>
      <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {label}
      </div>
      <div style={{ fontSize: '14px', fontWeight: 500, marginTop: '2px' }}>
        {value}
      </div>
    </div>
  );
}
