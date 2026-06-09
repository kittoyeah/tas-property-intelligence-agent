"use client";

import { useState, useEffect, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Mode = "buyer" | "construction" | "da_owner";
type Intent = "just_checking" | "granny_flat" | "extension" | "additional_storey" | "new_dwelling" | "outbuilding";

const MODE_LABELS: Record<Mode, string> = {
  buyer: "Property Buyer / Investor",
  construction: "Tradie / Builder",
  da_owner: "DA Owner / Developer",
};

const INTENT_LABELS: Record<Intent, string> = {
  just_checking: "Just checking / General query",
  granny_flat: "Granny flat / secondary dwelling",
  extension: "Extension / home renovation",
  additional_storey: "Adding an additional storey",
  new_dwelling: "New dwelling / main build",
  outbuilding: "Outbuilding / shed / garage / carport",
};

interface Overlay {
  code?: string;
  ov_name?: string;
  ov_cat?: string;
  descript?: string;
  lps?: string;
  lps_ref?: string;
  layer?: number;
}

interface CheckResult {
  address: string;
  mode: Mode;
  intent: Intent;
  council?: { name: string; lga_code: number };
  zone?: { zone: string; zone_abb?: string; lps?: string; lps_ref?: string };
  overlays: Overlay[];
  response: string;
  kingborough_interim?: boolean;
  error?: string;
}

interface ClauseGuide {
  id: string;
  title: string;
  code: string;
  purpose: string;
  implications: string;
  icon: string;
}

const PLANNING_GUIDES: ClauseGuide[] = [
  {
    id: "heritage",
    title: "C6.0 Local Historic Heritage Code",
    code: "C6.0",
    purpose: "To protect and conserve the heritage values of local heritage places, heritage precincts, local historic landscape precincts, and significant trees.",
    implications: "Any development or external works (such as alterations or building extensions) within a heritage precinct cannot be approved as Permitted development and will require a discretionary application. A Heritage Impact Statement is typically required.",
    icon: "🏛️"
  },
  {
    id: "flood",
    title: "C12.0 Flood-Prone Areas Hazard Code",
    code: "C12.0",
    purpose: "To protect people, property, and infrastructure from flood hazard and ensure that development does not increase flood risk elsewhere.",
    implications: "New structures or extensions in a mapped flood-prone area require a hydraulic engineer's assessment. Floor levels must be elevated above the defined flood level (typically 1% AEP + freeboard).",
    icon: "🌊"
  },
  {
    id: "bushfire",
    title: "C13.0 Bushfire-Prone Areas Code",
    code: "C13.0",
    purpose: "To ensure that use and development is appropriately designed, located, and serviced to minimize the risk to human life and property from bushfire.",
    implications: "All new habitable buildings in bushfire-prone areas require a BAL (Bushfire Attack Level) assessment by an accredited bushfire practitioner. Higher BAL ratings require fire-resistant building materials and dedicated water storage.",
    icon: "🔥"
  },
  {
    id: "landslip",
    title: "C15.0 Landslip Hazard Code",
    code: "C15.0",
    purpose: "To manage use and development on land subject to landslip hazard to ensure it does not increase risk to life or property.",
    implications: "Depending on the landslip hazard band (Low, Medium, High), a geotechnical report prepared by a qualified geophysicist or engineer is required to prove the site is stable and specify foundation engineering.",
    icon: "⛰️"
  }
];

// Document database for the side-by-side viewer
interface SourceDoc {
  title: string;
  code: string;
  url?: string;
  description: string;
  clauses: { title: string; content: string }[];
}

const SOURCE_DOCS: Record<string, SourceDoc> = {
  "C6.0": {
    title: "State Planning Provisions — Local Historic Heritage Code",
    code: "C6.0",
    url: "https://planningschemes.tas.gov.au/__data/assets/pdf_file/0009/726849/State-Planning-Provisions-operative-25-December-2024.pdf",
    description: "This code applies to development on land within local heritage precincts or containing local heritage places.",
    clauses: [
      { title: "C6.2.1 Precinct standards", content: "Development must conserve the architectural, historic, and spatial character of the precinct. New building heights, setbacks, and roof pitches must align with traditional forms in the streetscape." },
      { title: "C6.2.2 Acceptable Solutions", content: "No alterations or demolition of original heritage fabrics is permitted unless under a professional Heritage Impact Statement proving no net loss of heritage value." }
    ]
  },
  "HOB-C6.2.1": {
    title: "Hobart Local Provisions Schedule — Local Heritage Precinct",
    code: "HOB-C6.2.1",
    url: "https://planningschemes.tas.gov.au/__data/assets/pdf_file/0006/727773/Hobart-LPS-operative-22-October-2025.pdf",
    description: "Battery Point local heritage precinct rules. Applies specifically to property structures and landscaping in the Battery Point heritage zone.",
    clauses: [
      { title: "HOB-C6.2.1.1 Character statement", content: "Battery Point is characterized by mid-to-late 19th-century maritime cottages and grand Victorian estates. Development must maintain traditional front setback lines (typically 0m to 2m) and utilize pitched roofs (30 to 45 degrees)." },
      { title: "HOB-C6.2.1.2 External finishes", content: "External materials must consist of painted weatherboards, rendered masonry, or sandstone. Corrugated iron or zinc-coated roofing is preferred. Face brickwork or concrete blocks are prohibited." }
    ]
  },
  "C12.0": {
    title: "State Planning Provisions — Flood-Prone Areas Hazard Code",
    code: "C12.0",
    url: "https://planningschemes.tas.gov.au/__data/assets/pdf_file/0009/726849/State-Planning-Provisions-operative-25-December-2024.pdf",
    description: "Regulates use and development on land subject to flooding to prevent risk to life and assets.",
    clauses: [
      { title: "C12.5.1 Building floor levels", content: "Floor levels of all habitable rooms must be at least 300mm above the 1% Annual Exceedance Probability (AEP) flood level as determined by a certified hydraulic engineer's model." },
      { title: "C12.5.2 Flood hazard protection", content: "Electrical components and plumbing vents must be located above the flood hazard level. Foundations must be engineered to withstand hydrostatic and hydrodynamic forces of floodwaters." }
    ]
  },
  "C13.0": {
    title: "State Planning Provisions — Bushfire-Prone Areas Code",
    code: "C13.0",
    url: "https://planningschemes.tas.gov.au/__data/assets/pdf_file/0009/726849/State-Planning-Provisions-operative-25-December-2024.pdf",
    description: "Applied to ensure safety margins for properties located near high-risk vegetation areas.",
    clauses: [
      { title: "C13.5.1 Emergency access", content: "Access roads and driveways must provide safe, all-weather passing bays and turning circles for fire engines. Water supply for firefighting (e.g. a dedicated 10,000L tank with matching couplings) must be installed." },
      { title: "C13.5.2 Building construction standard", content: "Habitable buildings must be designed to Australian Standard AS 3959 (Construction of buildings in bushfire-prone areas) corresponding to the BAL assessment rating (BAL-12.5 to BAL-40)." }
    ]
  },
  "C15.0": {
    title: "State Planning Provisions — Landslip Hazard Code",
    code: "C15.0",
    url: "https://planningschemes.tas.gov.au/__data/assets/pdf_file/0009/726849/State-Planning-Provisions-operative-25-December-2024.pdf",
    description: "Ensures that slope stability is maintained during earthworks and foundation engineering.",
    clauses: [
      { title: "C15.5.1 Geotechnical assessment", content: "A comprehensive geotechnical report is required for any excavation, filling, or building load additions in Medium or High Landslip Hazard bands. The report must prove a factor of safety > 1.5 against failure." },
      { title: "C15.5.2 Drainage and stormwater", content: "All concentrated stormwater and household greywater must be piped directly to the legal street point of discharge. Surface water ponding or absorption trenches are strictly prohibited to avoid saturating subsoils." }
    ]
  },
  "HOB-S7.0": {
    title: "Hobart Local Provisions Schedule — Battery Point Specific Area Plan",
    code: "HOB-S7.0",
    url: "https://planningschemes.tas.gov.au/__data/assets/pdf_file/0006/727773/Hobart-LPS-operative-22-October-2025.pdf",
    description: "Specific Area Plan detailing preservation and development standards inside Battery Point.",
    clauses: [
      { title: "HOB-S7.5.1 Building height standards", content: "The maximum building height for a new dwelling or extension is 7.5m. Height must not exceed the average height of existing dwellings on adjoining sites by more than 10%." },
      { title: "HOB-S7.5.2 Setbacks and orientation", content: "The front setback must match the average front setback of the adjacent properties. Side setbacks must be zero where a boundary wall is traditional, or at least 1.5m to allow pedestrian side passage." }
    ]
  }
};


export default function Home() {
  const [address, setAddress] = useState("");
  const [mode, setMode] = useState<Mode>("buyer");
  const [intent, setIntent] = useState<Intent>("just_checking");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Autocomplete suggestions states
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [loaderStep, setLoaderStep] = useState("");
  const [streamedResponse, setStreamedResponse] = useState("");
  const [expandedGuide, setExpandedGuide] = useState<string | null>(null);
  
  // Side-by-side Document panel state (now holds multiple active sources)
  const [activeSources, setActiveSources] = useState<string[]>([]);
  const [highlightedSource, setHighlightedSource] = useState<string | null>(null);

  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const streamingTimer = useRef<NodeJS.Timeout | null>(null);
  const loaderTimer = useRef<NodeJS.Timeout | null>(null);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      if (streamingTimer.current) clearInterval(streamingTimer.current);
      if (loaderTimer.current) clearTimeout(loaderTimer.current);
    };
  }, []);

  // Handle autocomplete address typing
  const handleAddressChange = (val: string) => {
    setAddress(val);
    setCoords(null);

    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    if (val.trim().length < 3) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    debounceTimer.current = setTimeout(async () => {
      try {
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(val)}&format=json&limit=5&countrycodes=au&viewbox=143.82,-39.57,148.35,-43.65&bounded=1`;
        const res = await fetch(url, {
          headers: { "User-Agent": "SiteCheck/1.0" }
        });
        if (res.ok) {
          const data = await res.json();
          setSuggestions(data);
          setShowSuggestions(true);
        }
      } catch (err) {
        console.error("Autocomplete error:", err);
      }
    }, 350);
  };

  // Handle Autocomplete suggestion selection
  const handleSelectSuggestion = (sug: any) => {
    setAddress(sug.display_name);
    setCoords({ lat: parseFloat(sug.lat), lng: parseFloat(sug.lon) });
    setSuggestions([]);
    setShowSuggestions(false);
  };

  // Step-by-step progress logging trigger
  const startLoaderProgression = () => {
    setLoaderStep("Geocoding address in Tasmania (OpenStreetMap)...");
    
    const step2 = setTimeout(() => {
      setLoaderStep("Querying Tasmanian Government spatial overlays (theLIST)...");
    }, 1500);
    
    const step3 = setTimeout(() => {
      setLoaderStep("Searching local planning regulations (MongoDB Atlas)...");
    }, 3500);
    
    const step4 = setTimeout(() => {
      setLoaderStep("Generating plain-English summary (Groq Llama 4)...");
    }, 5500);

    loaderTimer.current = setTimeout(() => {
      setLoaderStep("Finalizing analysis report...");
    }, 8000);

    return {
      clear: () => {
        clearTimeout(step2);
        clearTimeout(step3);
        clearTimeout(step4);
        if (loaderTimer.current) clearTimeout(loaderTimer.current);
      }
    };
  };

  // Simulate word-by-word streaming effect on frontend
  const streamText = (fullText: string) => {
    setStreamedResponse("");
    if (streamingTimer.current) clearInterval(streamingTimer.current);

    const words = fullText.split(" ");
    let currentText = "";
    let i = 0;

    streamingTimer.current = setInterval(() => {
      if (i >= words.length) {
        if (streamingTimer.current) clearInterval(streamingTimer.current);
        setStreamedResponse(fullText);
        return;
      }
      currentText += (i === 0 ? "" : " ") + words[i];
      setStreamedResponse(currentText);
      i++;
    }, 30);
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);
    setStreamedResponse("");
    setExpandedGuide(null);
    setActiveSources([]);
    setHighlightedSource(null);

    const progressLoader = startLoaderProgression();

    try {
      let activeCoords = coords;
      
      if (!activeCoords) {
        try {
          const geoRes = await fetch(
            `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(address)}, Tasmania, Australia&format=json&limit=1&countrycodes=au`,
            { headers: { "User-Agent": "SiteCheck/1.0" } }
          );
          const geoData = await geoRes.json();
          if (geoData && geoData.length > 0) {
            activeCoords = { lat: parseFloat(geoData[0].lat), lng: parseFloat(geoData[0].lon) };
            setCoords(activeCoords);
          }
        } catch (e) {
          console.warn("Manual geocoding fallback failed:", e);
        }
      }

      const res = await fetch(`${API_URL}/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address, mode, intent }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(detail.detail ?? `HTTP ${res.status}`);
      }

      const data: CheckResult = await res.json();
      
      setResult(data);
      streamText(data.response);


      const hazards = checkHazards(data.overlays);
      if (hazards.hasFlood) setExpandedGuide("flood");
      else if (hazards.hasBushfire) setExpandedGuide("bushfire");
      else if (hazards.hasLandslip) setExpandedGuide("landslip");
      else if (hazards.hasHeritage) setExpandedGuide("heritage");

    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
      progressLoader.clear();
    }
  }

  // Parses response text to make headings bold and render citations as interactive buttons
  function renderResponseSection(text: string) {
    if (!text) return null;
    const lines = text.split("\n");
    return lines.map((line, idx) => {
      const citationRegex = /\[([^\]]+)\]/g;
      const parts = [];
      let lastIndex = 0;
      let match;

      while ((match = citationRegex.exec(line)) !== null) {
        if (match.index > lastIndex) {
          parts.push(line.substring(lastIndex, match.index));
        }
        
        const citationRaw = match[1];
        const citationLower = citationRaw.toLowerCase();

        if (
          citationLower.includes("no relevant") ||
          citationLower.includes("n/a") ||
          citationLower.includes("none") ||
          citationLower.includes("confirm") ||
          citationLower.trim() === ""
        ) {
          // Do not render anything
        } else {
          const citationCode = citationRaw.split(" ")[0].trim();
          const isHighlighted = highlightedSource === citationCode;

          parts.push(
            <button
              key={match.index}
              type="button"
              onClick={() => {
                // Ensure it is in active sources list, then highlight it
                if (!activeSources.includes(citationCode)) {
                  setActiveSources(prev => [...prev, citationCode]);
                }
                setHighlightedSource(citationCode);
              }}
              className={`inline-flex items-center gap-0.5 border rounded px-1.5 py-0.5 text-[10px] font-mono font-bold mx-1 cursor-pointer transition-all duration-200 shadow-sm ${
                isHighlighted 
                  ? "bg-cta text-white border-cta scale-105 ring-2 ring-brand-primary/20"
                  : "bg-brand-tint hover:bg-brand-primary/20 text-brand-primary border-brand-primary/25"
              }`}
            >
              {citationRaw} 📖
            </button>
          );
        }
        lastIndex = citationRegex.lastIndex;
      }

      if (lastIndex < line.length) {
        parts.push(line.substring(lastIndex));
      }

      return (
        <p key={idx} className="mb-2 text-slate-700 leading-relaxed text-sm last:mb-0">
          {parts.length > 0 ? parts : line}
        </p>
      );
    });
  }


  // Calculate Complexity Score and labels
  const getComplexityMetrics = (result: CheckResult) => {
    const overlayCount = result.overlays?.length ?? 0;
    let score = 1;
    let label = "Low Complexity";
    let desc = "Simple site rules apply. Standard permitted pathways likely.";
    let strokeClass = "stroke-green-500";
    let bgClass = "bg-green-50/50";
    let borderClass = "border-green-200";
    let textClass = "text-green-700";

    if (overlayCount === 1) {
      score = 3;
      label = "Moderate Complexity";
      desc = "Single overlay mapped. Planning approval or minor reports likely required.";
      strokeClass = "stroke-amber-500";
      bgClass = "bg-amber-50/50";
      borderClass = "border-amber-200";
      textClass = "text-amber-700";
    } else if (overlayCount > 1) {
      score = 5;
      label = "High Complexity";
      desc = "Multiple overlays present. Council review required, professional design support recommended.";
      strokeClass = "stroke-red-500";
      bgClass = "bg-red-50/50";
      borderClass = "border-red-200";
      textClass = "text-red-700";
    }

    return { score, label, desc, strokeClass, bgClass, borderClass, textClass };
  };

  // Check which of the 4 core hazards are active
  const checkHazards = (overlays: Overlay[]) => {
    const hasFlood = overlays.some(o => o.code?.toLowerCase().includes("flood") || o.ov_name?.toLowerCase().includes("flood") || o.code?.includes("C12"));
    const hasBushfire = overlays.some(o => o.code?.toLowerCase().includes("bushfire") || o.ov_name?.toLowerCase().includes("bushfire") || o.code?.includes("C13"));
    const hasLandslip = overlays.some(o => o.code?.toLowerCase().includes("landslip") || o.ov_name?.toLowerCase().includes("landslip") || o.code?.includes("C15"));
    const hasHeritage = overlays.some(
      o => o.code?.toLowerCase().includes("heritage") || o.ov_name?.toLowerCase().includes("heritage") || o.code?.toLowerCase().includes("historic") || o.code?.includes("C6")
    );

    return { hasFlood, hasBushfire, hasLandslip, hasHeritage };
  };

  // Get Mode-specific timeline steps
  const getTimelineSteps = (mode: Mode, intent: Intent, isComplex: boolean) => {
    const defaultDuration = isComplex ? "42+ Days (Discretionary)" : "14 Days (Permitted)";
    
    switch (mode) {
      case "buyer":
        return [
          {
            title: "Inspect Mapped Hazards",
            desc: "Verify boundaries of active overlays (like Heritage or Flood-prone bands) relative to building envelopes.",
            icon: "🔍"
          },
          {
            title: "Assess Build Limitations",
            desc: "Understand zoning limitations. Heritage overlay means extensions may need custom design features.",
            icon: "📐"
          },
          {
            title: "Insert Protective Clauses",
            desc: "Before signing, ensure the contract is subject to satisfactory zoning approval/soil and design testing.",
            icon: "📝"
          }
        ];
      case "construction":
        return [
          {
            title: "Determine Required Reports",
            desc: "Identify whether engineering (hydraulic/landslip) or bushfire risk assessments (BAL) are needed.",
            icon: "📋"
          },
          {
            title: "Scope Specialist Fees",
            desc: "Obtain fixed quotes for specialist planning reports before submitting your final construction price.",
            icon: "💰"
          },
          {
            title: "Adjust Timeline Buffer",
            desc: `Expect a ${defaultDuration} timeline for council processing. Factor this into your contract start date.`,
            icon: "📅"
          }
        ];
      case "da_owner":
        return [
          {
            title: "Commission Specialist Plans",
            desc: "Hire a consultant to draft a Bushfire Management Plan or a Heritage Impact Statement as required.",
            icon: "✒️"
          },
          {
            title: "Prepare Planning Drawings",
            desc: "Draft detail plans highlighting the exact locations of the proposed work in relation to overlay lines.",
            icon: "📐"
          },
          {
            title: "Lodge Application with Council",
            desc: `Submit your DA. Standard review periods: ${defaultDuration} statutory time limit.`,
            icon: "🏛️"
          }
        ];
    }
  };

  // Get Custom Color styles for active overlay chips
  const getOverlayChipColor = (overlay: Overlay) => {
    const code = (overlay.code ?? "").toLowerCase();
    const name = (overlay.ov_name ?? "").toLowerCase();
    
    if (code.includes("c12") || name.includes("flood") || code.includes("c13") || name.includes("bushfire") || code.includes("c15") || name.includes("landslip") || name.includes("erosion") || name.includes("inundation")) {
      return "bg-red-50 text-red-800 border-red-200";
    }
    if (code.includes("c6") || name.includes("heritage") || name.includes("historic")) {
      return "bg-amber-50 text-amber-800 border-amber-200";
    }
    return "bg-blue-50 text-blue-800 border-blue-200";
  };

  // Fetch planning document data for the side panel
  const getSourceDoc = (ref: string) => {
    const normalized = ref.trim().toUpperCase();
    
    if (SOURCE_DOCS[normalized]) return SOURCE_DOCS[normalized];
    
    const matchesBase = normalized.includes("C6") ? "C6.0" :
                        normalized.includes("C12") ? "C12.0" :
                        normalized.includes("C13") ? "C13.0" :
                        normalized.includes("C15") ? "C15.0" : null;
                        
    if (matchesBase && SOURCE_DOCS[matchesBase]) {
      return {
        ...SOURCE_DOCS[matchesBase],
        code: normalized,
        title: normalized.startsWith("HOB-") ? `Hobart LPS — ${SOURCE_DOCS[matchesBase].title}` : SOURCE_DOCS[matchesBase].title
      };
    }
    
    return {
      title: normalized.startsWith("HOB-") ? "Hobart Local Provisions Schedule" : "Tasmanian State Planning Provisions",
      code: normalized,
      url: normalized.startsWith("HOB-") 
        ? "https://planningschemes.tas.gov.au/__data/assets/pdf_file/0006/727773/Hobart-LPS-operative-22-October-2025.pdf"
        : "https://planningschemes.tas.gov.au/__data/assets/pdf_file/0009/726849/State-Planning-Provisions-operative-25-December-2024.pdf",
      description: `Official planning scheme regulations for overlay reference code: ${normalized}.`,
      clauses: [
        { title: `${normalized} — General Overlay Standard`, content: "This section regulates development within the mapped overlay bounds. Development must ensure that the proposed work does not increase environmental, hazard, or heritage risks, and satisfies acceptable design parameters." },
        { title: "Required Assessments", content: "Development in this zone may trigger discretionary review and require specialized professional drawings and impact statements. Consult your local council planner for details." }
      ]
    };
  };


  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      
      {/* Government Header Bar */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 border-r border-slate-300 pr-3">
              <svg width="24" height="24" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-slate-800">
                <circle cx="50" cy="50" r="45" stroke="currentColor" strokeWidth="10" />
                <path d="M30 65 L50 30 L70 65 Z" fill="currentColor" />
              </svg>
              <div className="text-[10px] font-bold uppercase tracking-wider leading-none text-slate-700 hidden sm:block text-left">
                Tasmanian<br />Government
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-brand-primary rounded-lg flex items-center justify-center text-white font-bold text-sm shadow-inner">
                SC
              </div>
              <div>
                <h1 className="text-base font-bold text-slate-900 tracking-tight leading-none text-left">SiteCheck</h1>
                <p className="text-[10px] text-slate-500 font-medium">Tasmania Property Intelligence</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="https://www.planbuild.tas.gov.au/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-brand-primary font-medium hover:underline flex items-center gap-1"
            >
              PlanBuild Portal 
              <span className="text-[10px]">↗</span>
            </a>
          </div>
        </div>
      </div>

      {/* Styled PlanBuild Banner */}
      <div className="bg-brand-primary text-white py-12 px-4 shadow-md relative overflow-hidden">
        <div className="absolute inset-0 opacity-10 pointer-events-none bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:16px_16px]"></div>
        <div className="max-w-4xl mx-auto text-center space-y-3 relative z-10">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Know your land before you buy, build, or apply.
          </h2>
          <p className="text-slate-200 text-sm max-w-xl mx-auto leading-relaxed">
            Get a plain-English summary of zoning rules, hazard overlays, and council assessments in 30 seconds using the LIST live Tasmanian spatial datasets.
          </p>
        </div>
      </div>

      {/* Main Grid Viewport Layout (Swaps dynamically to 2-columns if activeSources populated) */}
      <div className={`flex-grow grid grid-cols-1 ${activeSources.length > 0 ? "lg:grid-cols-12 max-w-7xl" : "max-w-3xl"} mx-auto w-full px-4 py-8 gap-6 transition-all duration-300`}>
        
        {/* Left Column: Form & Results */}
        <div className={`${activeSources.length > 0 ? "lg:col-span-7" : "col-span-full"} space-y-6`}>
          
          {/* Input Form with Inset Outline Card */}
          <div className="relative">
            <form onSubmit={handleSubmit} className="planbuild-card p-6 space-y-5 rounded-xl border border-slate-200 shadow-sm animate-fade-in relative z-20">
              <div className="relative">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 text-left">
                  Property Address
                </label>
                <input
                  type="text"
                  required
                  value={address}
                  onChange={e => handleAddressChange(e.target.value)}
                  placeholder="e.g. 1 Napoleon Street Battery Point TAS 7004"
                  className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none bg-white planbuild-input text-slate-800"
                />
                
                {/* Autocomplete Dropdown List */}
                {showSuggestions && suggestions.length > 0 && (
                  <ul className="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-56 overflow-y-auto z-50 text-left divide-y divide-slate-100 text-xs">
                    {suggestions.map((sug, i) => (
                      <li key={i}>
                        <button
                          type="button"
                          onClick={() => handleSelectSuggestion(sug)}
                          className="w-full px-4 py-2.5 hover:bg-slate-50 transition-colors text-left text-slate-700 truncate block cursor-pointer"
                        >
                          {sug.display_name}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 text-left">
                    My Situation
                  </label>
                  <select
                    value={mode}
                    onChange={e => setMode(e.target.value as Mode)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none bg-white planbuild-input text-slate-800"
                  >
                    {(Object.entries(MODE_LABELS) as [Mode, string][]).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5 text-left">
                    Proposed Activity
                  </label>
                  <select
                    value={intent}
                    onChange={e => setIntent(e.target.value as Intent)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none bg-white planbuild-input text-slate-800"
                  >
                    {(Object.entries(INTENT_LABELS) as [Intent, string][]).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !address.trim()}
                className="w-full bg-brand-primary hover:bg-brand-hover active:bg-brand-primary disabled:bg-slate-200 disabled:text-slate-400 text-white font-semibold py-3 px-4 rounded-lg text-sm transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>{loaderStep}</span>
                  </>
                ) : (
                  <>Check property restrictions</>
                )}
              </button>
            </form>
          </div>

          {/* Loading Pulse Placeholder */}
          {loading && (
            <div className="space-y-4 animate-pulse-slow mt-6">
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm h-32"></div>
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm h-64"></div>
            </div>
          )}

          {/* Error Alert */}
          {error && (
            <div className="planbuild-hazard-blockquote flex gap-3 items-start animate-fade-in text-left mt-6">
              <div className="w-5 h-5 rounded-full bg-accent-red text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">!</div>
              <div>
                <h4 className="text-sm font-bold text-accent-red uppercase tracking-wider mb-1">Query Failed</h4>
                <p className="text-sm text-slate-700">{error}</p>
              </div>
            </div>
          )}

          {/* Results Details */}
          {result && (
            <div className="space-y-6 animate-slide-up text-left">
              
              {/* Visual Map Pin showing location */}
              {coords && (
                <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Property Map Location</h3>
                  <div className="w-full h-64 rounded-lg overflow-hidden border border-slate-200 shadow-inner relative">
                    <iframe
                      title="OSM Property Map Location"
                      width="100%"
                      height="100%"
                      frameBorder="0"
                      marginHeight={0}
                      marginWidth={0}
                      src={`https://www.openstreetmap.org/export/embed.html?bbox=${coords.lng - 0.002}%2C${coords.lat - 0.002}%2C${coords.lng + 0.002}%2C${coords.lat + 0.002}&layer=mapnik&marker=${coords.lat}%2C${coords.lng}`}
                      className="absolute inset-0"
                    />
                  </div>
                </div>
              )}

              {/* Visual KPI Planning Dashboard */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                {/* Complexity Gauge Widget */}
                {(() => {
                  const metrics = getComplexityMetrics(result);
                  return (
                    <div className={`border rounded-xl p-5 shadow-sm flex flex-col justify-between ${metrics.bgClass} ${metrics.borderClass} md:col-span-1`}>
                      <div>
                        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Site Complexity</h3>
                        <div className={`text-base font-bold ${metrics.textClass} mb-1`}>{metrics.label}</div>
                        <p className="text-[11px] text-slate-600 leading-normal mb-3">{metrics.desc}</p>
                      </div>
                      <div className="flex justify-center items-center mt-auto">
                        <svg className="w-28 h-16" viewBox="0 0 100 60">
                          <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#e2e8f0" strokeWidth="8" strokeLinecap="round" />
                          <path
                            d="M 10 50 A 40 40 0 0 1 90 50"
                            fill="none"
                            className={`${metrics.strokeClass} transition-all duration-1000`}
                            strokeWidth="8"
                            strokeDasharray={126}
                            strokeDashoffset={126 - (126 * (metrics.score / 5))}
                            strokeLinecap="round"
                          />
                          <text x="50" y="47" textAnchor="middle" className="font-bold text-xs fill-slate-800">
                            {metrics.score} / 5
                          </text>
                        </svg>
                      </div>
                    </div>
                  );
                })()}

                {/* Mapped Hazards Risk Grid */}
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm md:col-span-2 space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Overlay Hazard Matrix</h3>
                  {(() => {
                    const hazards = checkHazards(result.overlays);
                    return (
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div className={`p-2.5 rounded-lg border flex items-center gap-2.5 ${hazards.hasFlood ? 'bg-red-50 border-red-200 text-red-800' : 'bg-green-50/50 border-green-100 text-green-800'}`}>
                          <span className="text-lg">🌊</span>
                          <div>
                            <div className="font-bold">Flood Risk</div>
                            <div className="text-[10px] font-medium opacity-85">{hazards.hasFlood ? "MAPPED HAZARD" : "Clear / Low Risk"}</div>
                          </div>
                        </div>
                        <div className={`p-2.5 rounded-lg border flex items-center gap-2.5 ${hazards.hasBushfire ? 'bg-red-50 border-red-200 text-red-800' : 'bg-green-50/50 border-green-100 text-green-800'}`}>
                          <span className="text-lg">🔥</span>
                          <div>
                            <div className="font-bold">Bushfire Risk</div>
                            <div className="text-[10px] font-medium opacity-85">{hazards.hasBushfire ? "BUSHFIRE PRONE" : "Clear / Low Risk"}</div>
                          </div>
                        </div>
                        <div className={`p-2.5 rounded-lg border flex items-center gap-2.5 ${hazards.hasLandslip ? 'bg-red-50 border-red-200 text-red-800' : 'bg-green-50/50 border-green-100 text-green-800'}`}>
                          <span className="text-lg">⛰️</span>
                          <div>
                            <div className="font-bold">Landslip Risk</div>
                            <div className="text-[10px] font-medium opacity-85">{hazards.hasLandslip ? "MAPPED HAZARD" : "Clear / Low Risk"}</div>
                          </div>
                        </div>
                        <div className={`p-2.5 rounded-lg border flex items-center gap-2.5 ${hazards.hasHeritage ? 'bg-amber-50 border-amber-200 text-amber-900' : 'bg-green-50/50 border-green-100 text-green-800'}`}>
                          <span className="text-lg">🏛️</span>
                          <div>
                            <div className="font-bold">Heritage Overlay</div>
                            <div className="text-[10px] font-medium opacity-85">{hazards.hasHeritage ? "HERITAGE AREA" : "Clear / Low Risk"}</div>
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>

              </div>
              
              {/* Spatial Context Details */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Location Context</h3>
                <div className="flex flex-wrap gap-2">
                  {result.council && (
                    <span className="inline-flex items-center gap-1.5 bg-brand-primary/10 text-brand-primary px-3 py-1 rounded-full text-xs font-bold">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                      {result.council.name} Council
                    </span>
                  )}
                  {result.zone && (
                    <span className="inline-flex items-center gap-1.5 bg-blue-50 text-blue-800 border border-blue-200 px-3 py-1 rounded-full text-xs font-bold">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      </svg>
                      Zone: {result.zone.zone} ({result.zone.zone_abb ?? "LPS"})
                    </span>
                  )}
                  {result.overlays?.length > 0 ? (
                    result.overlays.map((o, i) => (
                      <span key={i} className={`inline-flex items-center gap-1 border px-3 py-1 rounded-full text-xs font-bold ${getOverlayChipColor(o)}`}>
                        ⚠️ {o.ov_name ?? o.code}
                      </span>
                    ))
                  ) : (
                    <span className="inline-flex items-center gap-1.5 bg-green-50 text-green-800 border border-green-200 px-3 py-1 rounded-full text-xs font-bold">
                      ✅ No Overlays Mapped
                    </span>
                  )}
                </div>
                
                {/* Kingborough Fallback Notice */}
                {result.kingborough_interim && (
                  <div className="planbuild-blockquote mt-3 py-2.5 px-4 text-xs text-amber-800">
                    ⚠️ <strong>Kingborough Fallback active:</strong> This property was checked using legacy Layer 3 Interim Planning Scheme overlays. Verify details directly with the council.
                  </div>
                )}
              </div>

              {/* Interactive Timeline Flowchart */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Recommended Action Steps</h3>
                  <p className="text-[11px] text-slate-500 mt-0.5">Tailored workflow for {MODE_LABELS[result.mode]}</p>
                </div>
                <div className="relative border-l border-slate-200 pl-6 ml-3 space-y-5 py-1">
                  {getTimelineSteps(result.mode, result.intent, result.overlays.length > 0).map((step, idx) => (
                    <div key={idx} className="relative">
                      <span className="absolute -left-[37px] top-0.5 bg-white border border-slate-300 w-6 h-6 rounded-full flex items-center justify-center text-xs shadow-sm font-semibold">
                        {idx + 1}
                      </span>
                      <div className="space-y-0.5">
                        <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                          <span>{step.icon}</span>
                          {step.title}
                        </div>
                        <p className="text-[11px] text-slate-600 leading-relaxed">{step.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Collapsible Planning Scheme Reference Accordion */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Planning Scheme Reference Guide</h3>
                <div className="space-y-2">
                  {PLANNING_GUIDES.map((guide) => {
                    const isActive =
                      (guide.id === "flood" && checkHazards(result.overlays).hasFlood) ||
                      (guide.id === "bushfire" && checkHazards(result.overlays).hasBushfire) ||
                      (guide.id === "landslip" && checkHazards(result.overlays).hasLandslip) ||
                      (guide.id === "heritage" && checkHazards(result.overlays).hasHeritage);

                    const isExpanded = expandedGuide === guide.id;

                    return (
                      <div
                        key={guide.id}
                        className={`border rounded-lg transition-all duration-200 overflow-hidden ${
                          isActive ? "border-brand-primary/45 bg-slate-50/40" : "border-slate-200"
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => setExpandedGuide(isExpanded ? null : guide.id)}
                          className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-slate-50/80 transition-colors"
                        >
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
                            <span>{guide.icon}</span>
                            <span>{guide.title}</span>
                            {isActive && (
                              <span className="bg-brand-primary/10 text-brand-primary text-[9px] font-bold px-1.5 py-0.5 rounded-full ml-1.5 uppercase">
                                Active on site
                              </span>
                            )}
                          </div>
                          <span className="text-slate-400 text-xs font-bold">{isExpanded ? "▲" : "▼"}</span>
                        </button>
                        
                        {isExpanded && (
                          <div className="px-4 pb-4 pt-1 border-t border-slate-100 text-[11px] text-slate-600 space-y-2 animate-fade-in leading-relaxed">
                            <div>
                              <strong className="text-slate-700 block uppercase tracking-wider text-[9px] mb-0.5">Scheme Purpose:</strong>
                              <p>{guide.purpose}</p>
                            </div>
                            <div>
                              <strong className="text-slate-700 block uppercase tracking-wider text-[9px] mb-0.5">Development Implications:</strong>
                              <p className="font-medium text-slate-800">{guide.implications}</p>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                if (!activeSources.includes(guide.code)) {
                                  setActiveSources(prev => [...prev, guide.code]);
                                }
                                setHighlightedSource(guide.code);
                              }}
                              className="mt-2 text-[10px] text-brand-primary font-bold hover:underline flex items-center gap-1 cursor-pointer"
                            >
                              Open Full Document Details 📖
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Warning blockquotes for overlays */}
              {result.overlays?.length > 0 && (
                <div className="space-y-3">
                  {result.overlays.map((overlay, idx) => {
                    const isHazard =
                      overlay.code?.toLowerCase().includes("flood") ||
                      overlay.code?.toLowerCase().includes("landslip") ||
                      overlay.code?.toLowerCase().includes("bushfire") ||
                      overlay.code?.includes("C12") ||
                      overlay.code?.includes("C13") ||
                      overlay.code?.includes("C15");

                    const lpsRef = overlay.lps_ref ?? "";

                    return (
                      <div
                        key={idx}
                        className={isHazard ? "planbuild-hazard-blockquote animate-fade-in" : "planbuild-blockquote animate-fade-in"}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex gap-2">
                            <span className="text-base">{isHazard ? "🔥" : "🏛️"}</span>
                            <div>
                              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                                {overlay.code} ({overlay.lps_ref})
                              </h4>
                              <p className="text-sm font-semibold text-slate-800 mt-0.5">
                                {overlay.ov_name}
                              </p>
                              {overlay.descript && overlay.descript.trim() !== "" && (
                                <p className="text-xs text-slate-500 mt-1">
                                  <strong>Designation:</strong> {overlay.descript}
                                </p>
                              )}
                            </div>
                          </div>
                          {lpsRef && (
                            <button
                              type="button"
                              onClick={() => {
                                if (!activeSources.includes(lpsRef)) {
                                  setActiveSources(prev => [...prev, lpsRef]);
                                }
                                setHighlightedSource(lpsRef);
                              }}
                              className="text-[10px] font-bold text-brand-primary border border-brand-primary/20 bg-brand-primary/5 hover:bg-brand-primary/10 rounded px-2.5 py-1 transition-colors cursor-pointer shadow-sm ml-2 self-center shrink-0"
                            >
                              View Source 📖
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* SiteCheck Analysis Summary Card */}
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4 animate-slide-up">
                
                {/* Unified Header */}
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 bg-brand-primary rounded-lg flex items-center justify-center text-white font-bold text-xs shadow-inner">
                      SC
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 tracking-tight leading-none text-left">SiteCheck Analysis Summary</h3>
                      <p className="text-[10px] text-slate-500 font-medium mt-1">Generated property planning assessment & guidelines</p>
                    </div>
                  </div>
                </div>

                <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-wrap leading-relaxed text-left text-sm">
                  {renderResponseSection(streamedResponse)}
                </div>

                {/* Disclaimer */}
                <p className="text-[10px] text-slate-400 text-center px-4 leading-normal pt-3 border-t border-slate-100">
                  Disclaimer: This AI agent is an interpretation tool designed for informational purposes and is not a replacement for legal, engineering, or official council advice. All planning claims should be verified directly on PlanBuild Tasmania or with your local council before commencing any works.
                </p>
              </div>

            </div>
          )}
        </div>

        {/* Right Column: Sticky Stacked Document Viewer (Autopopulates stacked details) */}
        {activeSources.length > 0 && (
          <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-5 shadow-md self-start sticky top-6 animate-slide-in-right text-left space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">📖</span>
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Source Document References</span>
              </div>
              <button
                type="button"
                onClick={() => setActiveSources([])}
                className="text-[10px] font-bold text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
              >
                Clear all
              </button>
            </div>
            
            <div className="space-y-5">
              {activeSources.map((ref, idx) => {
                const doc = getSourceDoc(ref);
                const isHighlighted = highlightedSource === ref;
                
                return (
                  <div 
                    key={idx} 
                    className={`p-4 rounded-xl border transition-all duration-300 space-y-3 relative ${
                      isHighlighted 
                        ? "bg-brand-tint border-brand-primary shadow-sm ring-2 ring-brand-primary/20"
                        : "bg-slate-50/20 border-slate-200"
                    }`}
                  >
                    {isHighlighted && (
                      <span className="absolute top-2 right-2 bg-cta text-white text-[8px] font-bold px-1.5 py-0.5 rounded-full uppercase">
                        Selected
                      </span>
                    )}
                    <div>
                      <span className="bg-brand-primary/10 text-brand-primary text-[9px] font-mono font-bold px-2 py-0.5 rounded-full">
                        {doc.code}
                      </span>
                      <h3 className="text-xs font-bold text-slate-800 mt-2 leading-snug">{doc.title}</h3>
                      <p className="text-[10px] text-slate-500 mt-1 leading-normal">{doc.description}</p>
                    </div>
                    
                    <div className="space-y-2.5 border-t border-slate-100 pt-3">
                      {doc.clauses.map((clause, cIdx) => (
                        <div key={cIdx} className="space-y-0.5 bg-white p-2.5 rounded-lg border border-slate-150">
                          <strong className="text-[11px] font-bold text-slate-800 block">{clause.title}</strong>
                          <p className="text-[10px] text-slate-600 leading-normal">{clause.content}</p>
                        </div>
                      ))}
                    </div>

                    {doc.url && (
                      <div className="border-t border-slate-100 pt-3 flex">
                        <a
                          href={doc.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="w-full bg-brand-primary hover:bg-brand-hover text-white text-center font-bold text-[10px] py-2 px-3 rounded-lg transition-colors inline-block"
                        >
                          Download Reference PDF ↗
                        </a>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>

      {/* Government Footer */}
      <footer className="bg-brand-secondary text-white text-xs py-8 px-4 mt-12 border-t border-slate-900 shadow-inner">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center sm:text-left">
            <div className="font-semibold text-sm">SiteCheck Tasmania</div>
            <p className="text-slate-400 leading-normal">
              An AI-assisted planning screener utilizing CC BY 3.0 AU spatial overlays from theLIST.
            </p>
          </div>
          <div className="flex flex-col items-center sm:items-end gap-3">
            <div className="flex items-center gap-2 opacity-80">
              <svg width="24" height="24" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-white">
                <circle cx="50" cy="50" r="45" stroke="currentColor" strokeWidth="10" />
                <path d="M30 65 L50 30 L70 65 Z" fill="currentColor" />
              </svg>
              <div className="text-[9px] font-bold uppercase tracking-wider leading-none text-white text-left">
                Tasmanian<br />Government
              </div>
            </div>
            <div className="flex flex-wrap justify-center sm:justify-end gap-3 text-slate-400">
              <a href="https://www.planbuild.tas.gov.au/sitemap" className="hover:underline">Sitemap</a>
              <span>•</span>
              <a href="https://www.planbuild.tas.gov.au/accessibility" className="hover:underline">Accessibility</a>
              <span>•</span>
              <a href="https://www.tas.gov.au/stds/codi.htm" className="hover:underline">Disclaimer</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
