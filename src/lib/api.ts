/**
 * ESG Dashboard API Client
 * Connects React frontend to FastAPI backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Types
export interface SearchResult {
    rank: number;
    distance: number;
    company_name: string;
    report_year: string;
    page_no: number;
    chunk_index: number;
    content_preview: string;
    doc_id: string;
}

export interface SearchResponse {
    query: string;
    total_results: number;
    results: SearchResult[];
}

export interface StatsResponse {
    total_chunks: number;
    total_companies: number;
    companies: string[];
    years: string[];
}

export interface CompaniesResponse {
    companies: string[];
}

export interface HealthResponse {
    status: string;
    message: string;
}

export interface ChatSource {
    company: string;
    year: string;
    page: number;
    content_preview: string;
}

export interface ChatResponse {
    answer: string;
    sources: ChatSource[];
    query: string;
}

// API Functions

/**
 * Check API health
 */
export async function checkHealth(): Promise<HealthResponse> {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    if (!response.ok) {
        throw new Error(`Health check failed: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Search ESG documents
 * @param query - Search query string
 * @param topK - Number of results (1-20, default: 5)
 */
export async function searchDocuments(
    query: string,
    topK: number = 5
): Promise<SearchResponse> {
    const params = new URLSearchParams({
        query,
        top_k: topK.toString(),
    });

    const response = await fetch(`${API_BASE_URL}/api/search?${params}`);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Search failed');
    }

    return response.json();
}

/**
 * Get list of companies in the database
 */
export async function getCompanies(): Promise<CompaniesResponse> {
    const response = await fetch(`${API_BASE_URL}/api/companies`);
    if (!response.ok) {
        throw new Error(`Failed to get companies: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get database statistics
 */
export async function getStats(): Promise<StatsResponse> {
    const response = await fetch(`${API_BASE_URL}/api/stats`);
    if (!response.ok) {
        throw new Error(`Failed to get stats: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Send chat message to RAG-based AI assistant
 * @param message - User's question about ESG
 * @param topK - Number of documents to retrieve for context (default: 3)
 */
export async function sendChatMessage(
    message: string,
    topK: number = 3
): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message,
            top_k: topK,
        }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Chat failed');
    }

    return response.json();
}

// Export all as default object
export default {
    checkHealth,
    searchDocuments,
    getCompanies,
    getStats,
    sendChatMessage,
    API_BASE_URL,
};
