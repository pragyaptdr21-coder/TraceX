import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ShieldAlert, BookOpen, FileText, Download, Activity, CheckCircle, Crosshair } from 'lucide-react';
import { getTrail, getAccount, generateCaseSummary, generateFreezeRequisition, generateSection91Notice, exportCaseDiary, exportFreezeRequisition, exportSection91Notice } from '../api';

export default function CaseDiary() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialAccount = searchParams.get('account') || '';

  const [accountId, setAccountId] = useState(initialAccount);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [evidenceData, setEvidenceData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'section91' | 'freeze'>('summary');
  
  const [caseSummary, setCaseSummary] = useState<string | null>(null);
  const [freezeRequisition, setFreezeRequisition] = useState<string | null>(null);
  const [section91Notice, setSection91Notice] = useState<string | null>(null);

  const [reviewMode, setReviewMode] = useState(false);
  const [editableText, setEditableText] = useState("");

  const loadEvidence = async () => {
    if (!accountId) return;
    setIsLoading(true);
    setError(null);
    setCaseSummary(null);
    setFreezeRequisition(null);
    setSection91Notice(null);
    setReviewMode(false);
    
    try {
      const [trailRes, accRes] = await Promise.all([
        getTrail(accountId, 2),
        getAccount(accountId).catch(() => null)
      ]);
      
      setEvidenceData({
        source_account: accountId,
        risk_information: accRes || {},
        trail_information: {
           node_count: trailRes.nodes.length,
           edge_count: trailRes.edges.length
        },
        transactions: trailRes.edges.slice(0, 50)
      });
      setSearchParams({ account: accountId });
    } catch (err) {
      setError("Unable to load evidence for this account.");
      setEvidenceData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!evidenceData) return;
    setIsLoading(true);
    setError(null);
    try {
      const summary = await generateCaseSummary(evidenceData);
      setCaseSummary(summary);
      setReviewMode(true);
      setEditableText(summary);
      setActiveTab('summary');
    } catch (err) {
      setError("AI service unavailable.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateFreeze = async () => {
    if (!evidenceData) return;
    setIsLoading(true);
    setError(null);
    try {
      const draft = await generateFreezeRequisition(evidenceData);
      setFreezeRequisition(draft);
      setReviewMode(true);
      setEditableText(draft);
      setActiveTab('freeze');
    } catch (err) {
      setError("AI service unavailable.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateSection91 = async () => {
    if (!evidenceData) return;
    setIsLoading(true);
    setError(null);
    try {
      const draft = await generateSection91Notice(evidenceData);
      setSection91Notice(draft);
      setReviewMode(true);
      setEditableText(draft);
      setActiveTab('section91');
    } catch (err) {
      setError("Unable to generate Section 91 draft.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = () => {
    if (activeTab === 'summary') {
      setCaseSummary(editableText);
    } else if (activeTab === 'section91') {
      setSection91Notice(editableText);
    } else {
      setFreezeRequisition(editableText);
    }
    setReviewMode(false);
  };

  const handleExport = async () => {
    try {
      if (activeTab === 'summary' && caseSummary) {
        const blob = await exportCaseDiary(`Case Diary: ${accountId}`, caseSummary);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Case_Diary_${accountId}.pdf`;
        a.click();
      } else if (activeTab === 'section91' && section91Notice) {
        const blob = await exportSection91Notice(`Section 91 Notice: ${accountId}`, section91Notice);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Section_91_Notice_${accountId}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      } else if (activeTab === 'freeze' && freezeRequisition) {
        const blob = await exportFreezeRequisition(`Draft Freeze Requisition: ${accountId}`, freezeRequisition);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Freeze_Requisition_${accountId}.pdf`;
        a.click();
      }
    } catch(e) {
      setError("Export failed.");
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 text-gray-800 p-8 max-w-[1400px] mx-auto space-y-6">
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h2 className="text-2xl font-bold flex items-center gap-3 mb-6 text-gray-900">
          <BookOpen className="text-[#9f7aea]" /> Case Diary & Anti-Hallucination AI
        </h2>
        
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <input 
              type="text" 
              className="w-full bg-white border border-gray-300 rounded-lg pl-4 pr-4 py-3 text-sm focus:outline-none focus:border-[#9f7aea] focus:ring-2 focus:ring-[#9f7aea]/50 shadow-sm"
              placeholder="Account ID (e.g. HDFC10017550)"
              value={accountId}
              onChange={e => setAccountId(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && loadEvidence()}
            />
          </div>
          <button onClick={loadEvidence} className="px-6 py-3 bg-[#9f7aea] text-white text-sm font-semibold rounded-lg shadow-sm hover:bg-[#805ad5] transition-colors">
            Load Evidence
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden">
        {isLoading && (
          <div className="flex flex-col items-center justify-center h-full">
            <Activity size={32} className="text-[#9f7aea] animate-spin mb-4" />
            <div className="text-sm font-bold text-[#9f7aea]">Processing...</div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg flex items-center gap-3 text-sm font-semibold shadow-sm">
            <ShieldAlert size={18} />
            {error}
          </div>
        )}

        {evidenceData && !isLoading && (
          <div className="grid grid-cols-3 gap-6 h-full">
            
            {/* Left Column: TraceX Evidence */}
            <div className="col-span-1 flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
               <div className="p-4 border-b border-gray-200 bg-gray-50 flex items-center gap-2">
                 <Crosshair size={16} className="text-[#9f7aea]" />
                 <span className="font-bold uppercase tracking-wider text-xs text-gray-700">TraceX Evidence Facts</span>
               </div>
               <div className="p-6 flex-1 overflow-y-auto text-sm space-y-6">
                  <div>
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-2">Source Account</div>
                    <div className="font-mono font-bold text-[#9f7aea] bg-[#9f7aea]/10 border border-[#9f7aea]/20 px-3 py-1.5 rounded-md inline-block">{evidenceData.source_account}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-2">Risk Profile</div>
                    {evidenceData.risk_information?.mule_risk_index ? (
                       <div className="font-bold text-gray-800 bg-gray-50 px-3 py-1.5 rounded-md border border-gray-100 inline-block">Index: {evidenceData.risk_information.mule_risk_index}</div>
                    ) : (
                       <div className="text-gray-400">No specific risk profile.</div>
                    )}
                  </div>
                  {evidenceData.risk_information?.signals && evidenceData.risk_information.signals.length > 0 && (
                     <div>
                       <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-2">Detections</div>
                       <ul className="flex flex-wrap gap-2">
                          {evidenceData.risk_information.signals.map((s: any, i: number) => (
                             <li key={i} className="text-[10px] bg-red-50 text-red-700 border border-red-200 px-2 py-1 rounded-md font-bold">{s.type}</li>
                          ))}
                       </ul>
                     </div>
                  )}
                  <div>
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-2">Trail Data</div>
                    <div className="font-bold text-gray-800 bg-gray-50 px-3 py-1.5 rounded-md border border-gray-100 inline-block">{evidenceData.trail_information.node_count} Accounts, {evidenceData.trail_information.edge_count} Transactions</div>
                  </div>
               </div>
               <div className="p-4 border-t border-gray-200 bg-gray-50 space-y-3">
                  <button onClick={handleGenerateSummary} className="w-full px-4 py-3 bg-gray-800 text-white text-sm font-semibold rounded-lg shadow-sm hover:bg-gray-700 flex items-center justify-center gap-2 transition-colors">
                     <FileText size={16} /> Generate Case Summary
                  </button>
                  <button onClick={handleGenerateFreeze} className="w-full px-4 py-3 border border-red-200 text-red-600 bg-white text-sm font-semibold rounded-lg shadow-sm hover:bg-red-50 flex items-center justify-center gap-2 transition-colors">
                     <ShieldAlert size={16} /> Generate Freeze Requisition
                  </button>
                  <button onClick={handleGenerateSection91} className="w-full px-4 py-3 border border-blue-200 text-blue-700 bg-white text-sm font-semibold rounded-lg shadow-sm hover:bg-blue-50 flex items-center justify-center gap-2 transition-colors">
                    <FileText size={16} /> Generate Section 91 Notice
                  </button>
               </div>
            </div>

            {/* Right Column: AI Draft & Review */}
            <div className="col-span-2 flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
               <div className="flex border-b border-gray-200 bg-gray-50 shrink-0">
                  <button onClick={() => setActiveTab('summary')} className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 text-sm font-semibold transition-colors ${activeTab === 'summary' ? 'border-b-2 border-[#9f7aea] text-[#9f7aea] bg-white' : 'text-gray-500 hover:text-gray-800'}`}>
                    Case Summary
                  </button>
                  <button onClick={() => setActiveTab('section91')} className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 text-sm font-semibold transition-colors ${activeTab === 'section91' ? 'border-b-2 border-[#2563eb] text-[#2563eb] bg-white' : 'text-gray-500 hover:text-gray-800'}`}>
                    Section 91 Notice
                  </button>
                  <button onClick={() => setActiveTab('freeze')} className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 text-sm font-semibold transition-colors ${activeTab === 'freeze' ? 'border-b-2 border-[#9f7aea] text-[#9f7aea] bg-white' : 'text-gray-500 hover:text-gray-800'}`}>
                    Freeze Requisition
                  </button>
                  {((activeTab === 'summary' && caseSummary) || (activeTab === 'section91' && section91Notice) || (activeTab === 'freeze' && freezeRequisition)) && !reviewMode && (
                     <div className="px-4 py-2 flex items-center border-l border-gray-200">
                        <button onClick={handleExport} className="px-4 py-2 bg-[#9f7aea] text-white text-xs font-bold rounded-md shadow-sm hover:bg-[#805ad5] flex items-center gap-2 transition-colors">
                           <Download size={14} /> Export PDF
                        </button>
                     </div>
                  )}
               </div>

               <div className="flex-1 p-6 overflow-y-auto">
                 {reviewMode ? (
                   <div className="h-full flex flex-col">
                      <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 p-4 rounded-lg text-xs font-bold mb-4 flex items-center gap-2 shadow-sm">
                         <ShieldAlert size={16} /> AI GENERATED DRAFT - REQUIRES HUMAN REVIEW
                      </div>
                      <textarea 
                         className="flex-1 w-full bg-gray-50 border border-gray-200 rounded-lg p-6 text-sm font-mono focus:outline-none focus:border-[#9f7aea] focus:ring-2 focus:ring-[#9f7aea]/50 shadow-inner resize-none text-gray-700"
                         value={editableText}
                         onChange={(e) => setEditableText(e.target.value)}
                      />
                      <div className="mt-6 flex justify-end gap-3">
                         <button onClick={() => setReviewMode(false)} className="px-6 py-2 border border-gray-200 text-gray-600 text-sm font-bold rounded-lg shadow-sm hover:bg-gray-50 transition-colors">Cancel</button>
                         <button onClick={handleApprove} className="px-6 py-2 bg-emerald-600 text-white text-sm font-bold rounded-lg shadow-sm hover:bg-emerald-700 flex items-center gap-2 transition-colors">
                            <CheckCircle size={16} /> Approve & Finalize
                         </button>
                      </div>
                   </div>
                 ) : (
                   <div className="prose prose-sm max-w-none text-gray-700">
                     {activeTab === 'summary' && (
                        caseSummary ? (
                           <pre className="whitespace-pre-wrap font-sans text-sm bg-gray-50 p-6 rounded-lg border border-gray-100">{caseSummary}</pre>
                        ) : (
                           <div className="text-gray-400 text-center mt-20 flex flex-col items-center">
                             <FileText size={48} className="mb-4 text-gray-200" />
                             Click "Generate Case Summary" to analyze the evidence.
                           </div>
                        )
                     )}
                     {activeTab === 'section91' && (
                        section91Notice ? (
                           <>
                             <div className="bg-blue-50 border border-blue-200 text-blue-700 p-4 rounded-lg text-xs font-bold mb-4 flex items-center gap-2 shadow-sm">
                               <FileText size={16} /> DRAFT SECTION 94 BNSS / SECTION 91 CrPC CORRESPONDING NOTICE - REQUIRES HUMAN REVIEW
                             </div>
                             <pre className="whitespace-pre-wrap font-sans text-sm bg-gray-50 p-6 rounded-lg border border-gray-100">{section91Notice}</pre>
                           </>
                        ) : (
                           <div className="text-gray-400 text-center mt-20 flex flex-col items-center">
                             <FileText size={48} className="mb-4 text-gray-200" />
                             Generate a Section 91 draft from the loaded evidence.
                           </div>
                        )
                     )}
                     {activeTab === 'freeze' && (
                        freezeRequisition ? (
                           <>
                             <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg text-xs font-bold mb-4 flex items-center gap-2 shadow-sm">
                               <ShieldAlert size={16} /> DRAFT DOCUMENT - DOES NOT AUTOMATICALLY EXECUTE FREEZE
                             </div>
                             <pre className="whitespace-pre-wrap font-sans text-sm bg-gray-50 p-6 rounded-lg border border-gray-100">{freezeRequisition}</pre>
                           </>
                        ) : (
                           <div className="text-gray-400 text-center mt-20 flex flex-col items-center">
                             <ShieldAlert size={48} className="mb-4 text-gray-200" />
                             Click "Generate Freeze Requisition" to draft the document.
                           </div>
                        )
                     )}
                   </div>
                 )}
               </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
