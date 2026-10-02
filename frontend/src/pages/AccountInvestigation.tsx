import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, AlertCircle, Activity, BarChart, Share2, ShieldAlert, BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';
import { searchAccounts, getAccount, getTransactions, getRisk, getDetections } from '../api';
import type { SearchResult, AccountSummary, Transaction, RiskProfile, Detection } from '../api';
import InvestigationGraphTab from '../components/InvestigationGraphTab';

export default function AccountInvestigation() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  
  const [query, setQuery] = useState(initialQuery);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [account, setAccount] = useState<AccountSummary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [riskProfile, setRiskProfile] = useState<RiskProfile | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [transactionOffset, setTransactionOffset] = useState(0);
  
  const [isLoadingAccount, setIsLoadingAccount] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'overview'|'transactions'|'risk'|'graph'>('overview');

  useEffect(() => {
    const requestedView = searchParams.get('view');
    if (requestedView === 'graph' || requestedView === 'risk' || requestedView === 'transactions' || requestedView === 'overview') {
      setActiveTab(requestedView);
    }
  }, [searchParams]);

  useEffect(() => {
    if (initialQuery && !selectedAccountId) {
      handleSearch(initialQuery);
    }
  }, []);

  const handleSearch = async (searchQuery: string = query) => {
    if (!searchQuery.trim()) return;
    setSearchParams(previous => {
      const next = new URLSearchParams(previous);
      next.set('q', searchQuery);
      return next;
    });
    setIsSearching(true);
    try {
      const results = await searchAccounts(searchQuery);
      setSearchResults(results);
      if (results.length === 0) setError("No account found.");
      else {
        setError(null);
        if (results.length === 1) {
          loadAccount(results[0].account_id);
        }
      }
    } catch (err) {
      setError("TraceX backend is unavailable or search failed.");
    } finally {
      setIsSearching(false);
    }
  };

  const loadAccount = async (accountId: string) => {
    setSelectedAccountId(accountId);
    setIsLoadingAccount(true);
    setError(null);
    try {
      setAccount(null);
      setRiskProfile(null);
      setDetections([]);
      setTransactions([]);
      setTransactionOffset(0);
      const requestedView = searchParams.get('view');
      if (!requestedView) setActiveTab('overview');
      const [accData, riskData, txData, detectionData] = await Promise.all([
        getAccount(accountId),
        getRisk(accountId).catch(() => null),
        getTransactions(accountId, undefined, 50, 0).catch(() => []),
        getDetections(accountId).catch(() => [])
      ]);
      setAccount(accData);
      setRiskProfile(riskData);
      setTransactions(txData);
      setDetections(detectionData);
      setSearchResults([]);
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError("Account not found.");
      } else {
        setError("TraceX backend is unavailable.");
      }
      setAccount(null);
      setRiskProfile(null);
      setTransactions([]);
      setDetections([]);
    } finally {
      setIsLoadingAccount(false);
    }
  };

  return (
    <div className="tracex-investigation-page p-8 max-w-[1400px] mx-auto space-y-6 h-full flex flex-col">
      <div className="flex items-center gap-4">
        <div className="flex-1 relative shadow-sm">
          <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
          <input 
            type="text" 
            className="w-full bg-white border border-gray-300 rounded-lg pl-12 pr-4 py-3 text-sm text-gray-800 focus:outline-none focus:border-[#9f7aea] focus:ring-2 focus:ring-[#9f7aea]/50"
            placeholder="Search by Account ID..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <button 
          onClick={() => handleSearch()}
          className="px-6 py-3 bg-[#9f7aea] text-white text-sm font-semibold rounded-lg shadow-sm hover:bg-[#805ad5] transition-colors"
        >
          {isSearching ? 'Querying...' : 'Investigate'}
        </button>
      </div>

      {searchResults.length > 0 && !selectedAccountId && (
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-sm font-semibold text-gray-600 mb-3">Select an account to investigate:</h3>
          <div className="flex flex-wrap gap-2">
            {searchResults.map(res => (
              <button 
                key={res.account_id}
                onClick={() => loadAccount(res.account_id)}
                className="px-4 py-2 bg-gray-50 border border-gray-200 hover:border-[#9f7aea] text-gray-800 rounded-md text-sm font-semibold shadow-sm transition-colors"
              >
                {res.account_id}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg flex items-center gap-3 text-sm font-semibold shadow-sm">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {isLoadingAccount && (
        <div className="flex-1 flex items-center justify-center text-[#9f7aea] font-semibold text-sm">
          Loading investigation data...
        </div>
      )}

      {!isLoadingAccount && selectedAccountId && account && (
        <div className="flex-1 flex flex-col min-h-0 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="flex border-b border-gray-200 bg-gray-50 shrink-0">
            <button onClick={() => setActiveTab('overview')} className={`flex items-center gap-2 px-6 py-4 text-sm font-semibold transition-colors ${activeTab === 'overview' ? 'border-b-2 border-[#9f7aea] text-[#9f7aea] bg-white' : 'text-gray-500 hover:text-gray-800'}`}>
              <Activity size={16} /> Overview
            </button>
            <button onClick={() => setActiveTab('transactions')} className={`flex items-center gap-2 px-6 py-4 text-sm font-semibold transition-colors ${activeTab === 'transactions' ? 'border-b-2 border-[#9f7aea] text-[#9f7aea] bg-white' : 'text-gray-500 hover:text-gray-800'}`}>
              <BarChart size={16} /> Transactions
            </button>
            <button onClick={() => setActiveTab('risk')} className={`flex items-center gap-2 px-6 py-4 text-sm font-semibold transition-colors ${activeTab === 'risk' ? 'border-b-2 border-[#9f7aea] text-[#9f7aea] bg-white' : 'text-gray-500 hover:text-gray-800'}`}>
              <ShieldAlert size={16} /> Risk & Detections
            </button>
            <button onClick={() => setActiveTab('graph')} className={`flex items-center gap-2 px-6 py-4 text-sm font-semibold transition-colors ${activeTab === 'graph' ? 'border-b-2 border-[#9f7aea] text-[#9f7aea] bg-white' : 'text-gray-500 hover:text-gray-800'}`}>
              <Share2 size={16} /> Graph & Timeline
            </button>
          </div>
          
          <div className="flex-1 overflow-auto p-6 bg-gray-50">
            {activeTab === 'overview' && (
              <div className="space-y-6">
                <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                  <h3 className="text-sm font-bold text-gray-800 mb-4 uppercase tracking-wider">Account Identity</h3>
                  <div className="space-y-4">
                    <div>
                      <div className="text-xs text-gray-500 font-semibold mb-1">ACCOUNT ID</div>
                      <div className="text-lg font-bold text-gray-900">{account.account_id}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 font-semibold mb-1">TRANSACTION ACTIVITY</div>
                      <div className="text-sm text-gray-700">{account.incoming_count} incoming / {account.outgoing_count} outgoing</div>
                      <div className="text-sm text-gray-700">₹{account.incoming_amount.toLocaleString()} received / ₹{account.outgoing_amount.toLocaleString()} sent</div>
                      <div className="text-sm text-gray-700">{account.unique_counterparties} unique counterparties</div>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-white p-4 rounded-lg border border-gray-200"><div className="text-xs text-gray-500">MULE RISK INDEX</div><div className="text-3xl font-bold text-[#9f7aea]">{account.mule_risk_index}</div></div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200"><div className="text-xs text-gray-500">DETECTED SIGNALS</div><div className="text-3xl font-bold text-gray-900">{detections.length}</div></div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200 flex items-center"><Link to={`/diary?account=${encodeURIComponent(account.account_id)}`} className="text-sm font-bold text-[#6b46c1] flex items-center gap-2"><BookOpen size={16} /> Open Case Diary</Link></div>
                </div>
              </div>
            )}

            {activeTab === 'transactions' && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                <table className="w-full min-w-[1050px] text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 text-xs text-gray-500 uppercase tracking-wider">
                      <th className="p-4 font-semibold">Timestamp</th>
                      <th className="p-4 font-semibold">Type</th>
                      <th className="p-4 font-semibold">Amount</th>
                      <th className="p-4 font-semibold">Counterparty</th>
                      <th className="p-4 font-semibold">Mode</th>
                      <th className="p-4 font-semibold">Narration</th>
                      <th className="p-4 font-semibold">IP / Device</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {transactions.map(tx => (
                      <tr key={tx.Transaction_ID} className="hover:bg-gray-50">
                        <td className="p-4 text-sm text-gray-700">{new Date(tx.Timestamp).toLocaleString()}</td>
                        <td className="p-4">
                          <span className={`px-2 py-1 rounded text-xs font-bold ${tx.Sender_Account === selectedAccountId ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
                            {tx.Sender_Account === selectedAccountId ? 'OUTGOING' : 'INCOMING'}
                          </span>
                        </td>
                        <td className={`p-4 text-sm font-bold ${tx.Sender_Account === selectedAccountId ? 'text-red-600' : 'text-emerald-600'}`}>
                          {tx.Sender_Account === selectedAccountId ? '-' : '+'}₹{tx.Amount.toLocaleString()}
                        </td>
                        <td className="p-4 text-sm text-gray-700 font-mono">
                          {tx.Sender_Account === selectedAccountId ? tx.Receiver_Account : tx.Sender_Account}
                        </td>
                        <td className="p-4 text-sm text-gray-700">{tx.Payment_Mode}</td>
                        <td className="p-4 text-sm text-gray-700 max-w-[220px] truncate" title={tx.Narration}>{tx.Narration}</td>
                        <td className="p-4 text-xs text-gray-700">{tx.IP_Address} / {tx.Device_Type}</td>
                      </tr>
                    ))}
                    {transactions.length === 0 && (
                      <tr><td colSpan={7} className="p-8 text-center text-gray-500">No recent transactions found.</td></tr>
                    )}
                  </tbody>
                </table>
                <div className="flex justify-between items-center p-3 border-t border-gray-200 text-xs text-gray-500">
                  <span>Showing {transactions.length} scoped transactions</span>
                  <div className="flex gap-2"><button disabled={transactionOffset === 0} onClick={async () => { const next = Math.max(0, transactionOffset - 50); setTransactionOffset(next); setTransactions(await getTransactions(selectedAccountId, undefined, 50, next)); }} className="px-3 py-1 border rounded disabled:opacity-40">Previous</button><button disabled={transactions.length < 50} onClick={async () => { const next = transactionOffset + 50; setTransactionOffset(next); setTransactions(await getTransactions(selectedAccountId, undefined, 50, next)); }} className="px-3 py-1 border rounded disabled:opacity-40">Next</button></div>
                </div>
              </div>
            )}

            {activeTab === 'risk' && riskProfile && (
              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                <h3 className="text-sm font-bold text-gray-800 mb-6 uppercase tracking-wider">Risk Profile Assessment</h3>
                <div className="flex items-center gap-8 mb-8">
                  <div className="text-center">
                    <div className="text-5xl font-bold text-[#9f7aea] mb-2">{riskProfile.mule_risk_index}</div>
                    <div className="text-xs font-bold text-gray-500 uppercase">Total Risk Score</div>
                  </div>
                </div>
                <h4 className="text-xs font-bold text-gray-500 uppercase mb-4">Detected Signals</h4>
                <ul className="space-y-3">
                  {riskProfile.signals.map((signal, idx) => (
                    <li key={idx} className="flex items-start justify-between gap-3 bg-red-50 text-red-700 p-3 rounded-md text-sm font-semibold border border-red-100">
                      <ShieldAlert size={16} className="mt-0.5 shrink-0" />
                      <span><strong>Detected Signal:</strong> {signal.type}<br /><span className="text-xs font-normal">Evidence contribution: {signal.contribution}</span></span>
                    </li>
                  ))}
                  {detections.length === 0 && <li className="text-sm text-gray-500">No detection signals available for this account.</li>}
                </ul>
              </div>
            )}

            {activeTab === 'risk' && !riskProfile && (
              <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 text-center text-sm text-gray-500">
                Risk information is unavailable for this account.
              </div>
            )}

            {activeTab === 'graph' && (
              <div className="h-full">
                <InvestigationGraphTab initialAccountId={selectedAccountId} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
