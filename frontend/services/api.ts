import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface QueryRequest {
  query: string;
}

export interface QueryResponse {
  answer: string;
  sources?: any[]; // We'll type this later when building the Sources panel
  confidence?: number;
}

export const api = {
  /**
   * Send a query to the GraphRAG backend
   */
  async query(data: QueryRequest): Promise<QueryResponse> {
    try {
      const response = await apiClient.post<QueryResponse>('/query', data);
      return response.data;
    } catch (error) {
      console.error('API Error during query:', error);
      throw error;
    }
  },

  // Future endpoints (upload, etc.) will go here
};
