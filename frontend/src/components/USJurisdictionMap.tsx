import { useState, useEffect, useMemo } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';

/**
 * USJurisdictionMap — Interactive tabbed map (US States / Canada / International)
 * color-coded by film incentive program tier.
 *
 * Props:
 *   jurisdictions: array of { id, name, code, country, active, type } from the API
 *   onSelect: callback when a region is clicked, receives the jurisdiction code
 *
 * NOTE: geography names come from third-party map data and may not exactly
 * match the names stored in the database (e.g. "Czech Republic" vs "Czechia").
 * The ALIASES table below handles known mismatches — expand it if a country
 * shows as "No Program" when it shouldn't.
 */

interface Jurisdiction {
  id: string;
  name: string;
  code: string;
  country?: string;
  active?: boolean;
  type?: string;
}

interface Props {
  jurisdictions: Jurisdiction[];
  onSelect?: (code: string) => void;
}

type Region = 'us' | 'canada' | 'international';

const GEO_URLS: Record<Region, string> = {
  us: 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json',
  canada: 'https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/canada.geojson',
  international: 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json',
};

const REGION_LABELS: Record<Region, string> = {
  us: 'US States',
  canada: 'Canada',
  international: 'International',
};

// geoAlbersUsa auto-fits the US, so it needs no manual config. The other two
// projections default to fitting the WHOLE GLOBE, so without an explicit
// scale/center they render as a tiny sliver — these values manually frame
// each region. Treat these numbers as a starting point; they're untested
// against the live viewBox and will likely need a round of visual tuning.
const PROJECTIONS: Record<Region, 'geoAlbersUsa' | 'geoMercator'> = {
  us: 'geoAlbersUsa',
  canada: 'geoMercator',
  international: 'geoMercator',
};

const PROJECTION_CONFIG: Record<Region, { scale: number; center: [number, number] }> = {
  us: { scale: 1000, center: [-96, 38] }, // unused by geoAlbersUsa, harmless
  canada: { scale: 550, center: [-96, 62] },
  international: { scale: 260, center: [15, 15] }, // splits the difference between Europe and South Africa
};

// Countries to highlight on the International tab (EU + South Africa + a couple
// of others already seen in the jurisdiction list). Add more names here as needed —
// names must match how world-atlas labels them (Natural Earth naming conventions).
const INTERNATIONAL_COUNTRIES = new Set([
  'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czechia', 'Denmark',
  'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Ireland',
  'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands', 'Poland',
  'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden',
  'United Kingdom', 'South Africa', 'Australia',
]);

// Known name mismatches between the SceneIQ database and the map's geography data.
// Left side: normalized DB name. Right side: normalized geography name.
const ALIASES: Record<string, string> = {
  'czech republic': 'czechia',
  usa: 'united states of america',
  'united states': 'united states of america',
};

const COLORS = {
  tier1: '#1A1A2E',
  tier2: '#2D4A7A',
  tier3: '#6B8DB9',
  inactive: '#D1D5DB',
  hover: '#C9973A',
  stroke: '#FFFFFF',
};

// Tier assignments for US states based on program strength
const TIER1 = new Set(['CA', 'GA', 'NY', 'NM', 'LA']);
const TIER2 = new Set(['IL', 'TX', 'PA', 'NJ', 'NC', 'CT', 'MA', 'CO', 'OK', 'OR', 'NV', 'MN', 'VA', 'SC', 'TN', 'AL', 'AR', 'MS']);

function normalize(s: string | undefined | null): string {
  return (s ?? '').trim().toLowerCase();
}

function canon(s: string | undefined | null): string {
  const n = normalize(s);
  return ALIASES[n] ?? n;
}

export default function USJurisdictionMap({ jurisdictions, onSelect }: Props) {
  const [region, setRegion] = useState<Region>('us');
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  // Reset hover/selection whenever the tab changes
  useEffect(() => {
    setHovered(null);
    setSelected(null);
  }, [region]);

  // Jurisdictions relevant to the active tab, keyed by canonicalized name
  const jurByName = useMemo(() => {
    const map: Record<string, Jurisdiction> = {};
    for (const j of jurisdictions) {
      const country = normalize(j.country);
      const inTab =
        (region === 'us' && country === 'usa') ||
        (region === 'canada' && country === 'canada') ||
        (region === 'international' && country !== 'usa' && country !== 'canada');
      if (inTab) map[canon(j.name)] = j;
    }
    return map;
  }, [jurisdictions, region]);

  function lookupJur(geoName: string): Jurisdiction | undefined {
    return jurByName[canon(geoName)];
  }

  function getColor(geoName: string): string {
    if (hovered === geoName) return COLORS.hover;
    const j = lookupJur(geoName);
    if (!j || j.active === false) return COLORS.inactive;
    if (TIER1.has(j.code)) return COLORS.tier1;
    if (TIER2.has(j.code)) return COLORS.tier2;
    return COLORS.tier3;
  }

  function handleClick(geoName: string) {
    const j = lookupJur(geoName);
    if (!j) return;
    setSelected(geoName);
    onSelect?.(j.code);
  }

  const selectedJur = selected ? lookupJur(selected) : null;
  const activeCount = Object.keys(jurByName).length;

  return (
    <div style={{ marginBottom: '32px' }}>
      {/* Tabs + Legend */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div style={{ display: 'flex', gap: '4px', background: '#F1F5F9', padding: '4px', borderRadius: '10px' }}>
          {(['us', 'canada', 'international'] as Region[]).map(r => (
            <button
              key={r}
              type="button"
              onClick={() => setRegion(r)}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                background: region === r ? '#1A1A2E' : 'transparent',
                color: region === r ? '#FFFFFF' : '#64748B',
                transition: 'all 0.15s ease',
              }}
            >
              {REGION_LABELS[r]}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', fontSize: '12px' }}>
          <LegendItem color={COLORS.tier1} label="Tier 1 (Major)" />
          <LegendItem color={COLORS.tier2} label="Tier 2 (Solid)" />
          <LegendItem color={COLORS.tier3} label="Tier 3 / Active" />
          <LegendItem color={COLORS.inactive} label="No Program" />
        </div>
      </div>

      <p style={{ fontSize: '13px', color: '#6B7280', margin: '0 0 12px' }}>
        {activeCount} active {REGION_LABELS[region].toLowerCase()} jurisdiction{activeCount === 1 ? '' : 's'}
      </p>

      <div style={{ display: 'flex', gap: '24px' }}>
        {/* Map */}
        <div style={{
          flex: 1,
          background: '#F8FAFC',
          borderRadius: '12px',
          border: '1px solid #E2E8F0',
          padding: '16px',
        }}>
          <ComposableMap
            projection={PROJECTIONS[region]}
            projectionConfig={PROJECTION_CONFIG[region]}
            style={{ width: '100%', height: 'auto', maxHeight: '440px' }}
          >
            <Geographies geography={GEO_URLS[region]}>
              {({ geographies }) =>
                geographies
                  .filter(geo => region !== 'international' || INTERNATIONAL_COUNTRIES.has(geo.properties.name))
                  .map(geo => {
                    const geoName: string = geo.properties.name;
                    const j = lookupJur(geoName);
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        onClick={() => handleClick(geoName)}
                        onMouseEnter={() => setHovered(geoName)}
                        onMouseLeave={() => setHovered(null)}
                        style={{
                          default: {
                            fill: getColor(geoName),
                            stroke: COLORS.stroke,
                            strokeWidth: 0.75,
                            outline: 'none',
                          },
                          hover: {
                            fill: COLORS.hover,
                            stroke: COLORS.stroke,
                            strokeWidth: 0.75,
                            outline: 'none',
                            cursor: j ? 'pointer' : 'default',
                          },
                          pressed: {
                            fill: COLORS.hover,
                            stroke: COLORS.stroke,
                            strokeWidth: 0.75,
                            outline: 'none',
                          },
                        }}
                      />
                    );
                  })
              }
            </Geographies>
          </ComposableMap>
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
              <InfoRow label="Status" value={selectedJur.active === false ? 'Inactive' : 'Active'} />
              <InfoRow
                label="Tier"
                value={
                  TIER1.has(selectedJur.code) ? 'Tier 1 - Major Program'
                  : TIER2.has(selectedJur.code) ? 'Tier 2 - Solid Program'
                  : 'Tier 3 - Active Program'
                }
              />
              <InfoRow label="Region" value={REGION_LABELS[region]} />
              <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.15)' }}>
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
                Select a {region === 'us' ? 'state' : region === 'canada' ? 'province' : 'country'}
              </div>
              <div style={{ fontSize: '12px', marginTop: '4px' }}>
                Click any highlighted region to view incentive program details
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
      <div style={{ width: '14px', height: '14px', borderRadius: '3px', background: color, border: '1px solid #E2E8F0' }} />
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
