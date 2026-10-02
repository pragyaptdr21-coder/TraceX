import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export interface HealthStatus {
  status: 'ok' | 'error';
  message?: string;
}

export const getHealth = async (): Promise<HealthStatus> => {
  const res = await api.get('/health');
  return res.data;
};

export interface SearchResult {
  account_id: string;
}

export interface AccountSummary {
  account_id: string;
  incoming_count: number;
  incoming_amount: number;
  outgoing_count: number;
  outgoing_amount: number;
  total_transactions: number;
  unique_counterparties: number;
  mule_risk_index: number;
  signals: { type: string; contribution: number }[];
}

export interface Transaction {
  internal_id?: number;
  Transaction_ID: string;
  Sender_Account: string;
  Receiver_Account: string;
  Amount: number;
  Timestamp: string;
  Payment_Mode: string;
  Narration: string;
  IP_Address: string;
  Device_Type: string;
}

export interface RiskProfile {
  account_id: string;
  mule_risk_index: number;
  signals: { type: string; contribution: number }[];
  evidence_summary: any[];
}

export interface Detection {
  account_id: string;
  detection_type: string;
  score_contribution: number;
  evidence: Record<string, unknown>;
}

export const searchAccounts = async (query: string): Promise<SearchResult[]> => {
  const res = await api.get('/api/accounts/search', { params: { q: query } });
  return res.data.data;
};

export const getAccount = async (accountId: string): Promise<AccountSummary> => {
  const res = await api.get(`/api/accounts/${accountId}`);
  return res.data.data;
};

export const getTransactions = async (accountId: string, direction?: string, limit = 100, offset = 0): Promise<Transaction[]> => {
  const res = await api.get(`/api/accounts/${accountId}/transactions`, {
    params: { direction, limit, offset },
  });
  return res.data.data;
};

export const getRisk = async (accountId: string): Promise<RiskProfile> => {
  const res = await api.get(`/api/accounts/${accountId}/risk`);
  return res.data.data;
};

export const getDetections = async (accountId: string): Promise<Detection[]> => {
  const res = await api.get(`/api/accounts/${accountId}/detections`);
  return res.data.data;
};

// Ready for next phases
export const getTrail = async (accountId: string, hops = 4) => {
  const res = await api.get(`/api/accounts/${accountId}/trail`, { params: { hops, max_edges: 1500 } });
  return res.data.data;
};

export const getTimeline = async (accountId: string) => {
  const res = await api.get(`/api/accounts/${accountId}/timeline`);
  return res.data.data;
};

export const exportSubdataset = async (transactionIds: string[], metadata?: any) => {
  const response = await api.post('/api/investigations/export', {
    transaction_ids: transactionIds,
    metadata
  }, { responseType: 'blob' });
  return response.data;
};

export const generateCaseSummary = async (evidenceData: any) => {
  const response = await api.post('/api/case-diary/generate', { evidence_data: evidenceData });
  return response.data.data;
};

export const generateFreezeRequisition = async (evidenceData: any) => {
  const response = await api.post('/api/freeze-requisition/generate', { evidence_data: evidenceData });
  return response.data.data;
};

export const exportCaseDiary = async (title: string, content: string) => {
  const response = await api.post('/api/case-diary/export', { title, content }, { responseType: 'blob' });
  return response.data;
};

export const exportFreezeRequisition = async (title: string, content: string) => {
  const response = await api.post('/api/freeze-requisition/export', { title, content }, { responseType: 'blob' });
  return response.data;
};
