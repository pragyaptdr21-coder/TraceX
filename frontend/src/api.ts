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

// Detection evaluation (precision / recall).
//
// The response carries metric fields ONLY when official ground truth exists.
// `metrics_available: false` means no precision/recall figure may be rendered.
export interface EvaluationPayload {
  status: string;
  metrics_available: boolean;
  message?: string;
  notes?: string[];
  ground_truth: {
    status: string;
    usable: boolean;
    path?: string;
    ground_truth_accounts: number;
    mule_accounts: number;
    regular_accounts: number;
    expected_mule_accounts: number;
    expected_regular_accounts: number;
    duplicate_accounts: string[];
    invalid_labels: string[];
    missing_labels: string[];
    unknown_accounts: string[];
    issues: { code: string; message: string; count: number; samples: string[] }[];
  };
  population_validated?: boolean;
  ground_truth_accounts?: number;
  mule_accounts?: number;
  regular_accounts?: number;
  predicted_mules?: number;
  risk_threshold?: number;
  true_positives?: number;
  false_positives?: number;
  true_negatives?: number;
  false_negatives?: number;
  precision?: number | null;
  recall?: number | null;
  f1?: number | null;
  false_positive_rate?: number | null;
  false_negative_rate?: number | null;
  accuracy?: number | null;
  per_detector?: Record<string, any> | null;
  false_positive_analysis?: any;
  threshold_comparison?: any[];
}

export const getPrecisionRecall = async (): Promise<EvaluationPayload> => {
  const res = await api.get('/api/evaluation/precision-recall');
  return res.data.data;
};

export const downloadEvaluationReport = async (): Promise<Blob> => {
  const res = await api.get('/api/evaluation/report', { responseType: 'blob' });
  return res.data;
};

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

export const generateSection91Notice = async (evidenceData: any) => {
  const response = await api.post('/api/section-91-notice/generate', { evidence_data: evidenceData });
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

export const exportSection91Notice = async (title: string, content: string) => {
  const response = await api.post('/api/section-91-notice/export', { title, content }, { responseType: 'blob' });
  return response.data;
};
