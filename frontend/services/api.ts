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
  confidence: number;
  hallucination_score: number;
  supported: boolean;
  sources: Array<{
    source_name?: string;
    text_snippet?: string;
    score?: number;
    [key: string]: any;
  }>;
  graph_paths: string[];
  retrieval_stats: Record<string, any>;
  interaction_id?: number; // generated on frontend for matching feedback
}

export interface UploadResponse {
  filename: string;
  chunks_indexed: number;
  entities_found: number;
  relationships_found: number;
  graph_nodes_created: number;
  duration_seconds: number;
  success: boolean;
  error?: string | null;
}

export interface GraphNode {
  name: string;
  labels: string[];
}

export interface GraphRelationship {
  source: string;
  relation: string;
  target: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  total_nodes: number;
  total_relationships: number;
}

export interface FeedbackResponse {
  success: boolean;
  message: string;
}

export interface AnalyticsResponse {
  total_interactions: number;
  hallucination_rate: number;
  avg_confidence: number;
  user_satisfaction_rate: number;
  low_performing_queries: Array<Record<string, any>>;
}

export interface Interaction {
  id?: string | number;
  query: string;
  answer: string;
  confidence: number;
  hallucination_score: number;
  feedback?: string;
  timestamp?: string;
}

export const api = {
  /**
   * Send a query to the GraphRAG backend
   */
  async query(data: QueryRequest): Promise<QueryResponse> {
    try {
      const response = await apiClient.post<QueryResponse>('/query', data);
      // Backend doesn't return interaction_id in JSON directly, let's assign one based on time
      const interaction_id = Math.floor(Math.random() * 10000000) + 1;
      return {
        ...response.data,
        interaction_id,
      };
    } catch (error) {
      console.error('API Error during query:', error);
      throw error;
    }
  },

  /**
   * Upload PDF research papers
   */
  async upload(file: File): Promise<UploadResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await apiClient.post<UploadResponse>('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('API Error during upload:', error);
      throw error;
    }
  },

  /**
   * Fetch the full knowledge graph from Neo4j
   */
  async getGraph(): Promise<GraphResponse> {
    try {
      const response = await apiClient.get<GraphResponse>('/graph');
      return response.data;
    } catch (error) {
      console.error('API Error fetching graph:', error);
      throw error;
    }
  },

  /**
   * Submit helpfulness rating feedback for an answer
   */
  async submitFeedback(interactionId: number, rating: 'helpful' | 'inaccurate' | 'hallucinated'): Promise<FeedbackResponse> {
    try {
      const response = await apiClient.post<FeedbackResponse>('/feedback', {
        interaction_id: interactionId,
        rating,
      });
      return response.data;
    } catch (error) {
      console.error('API Error submitting feedback:', error);
      throw error;
    }
  },

  /**
   * Get RAG performance and evaluation analytics
   */
  async getAnalytics(): Promise<AnalyticsResponse> {
    try {
      const response = await apiClient.get<AnalyticsResponse>('/analytics');
      return response.data;
    } catch (error) {
      console.error('API Error fetching analytics:', error);
      throw error;
    }
  },

  /**
   * Fetch recent query interactions
   */
  async getInteractions(limit: number = 20): Promise<Interaction[]> {
    try {
      const response = await apiClient.get<Interaction[]>(`/interactions?limit=${limit}`);
      return response.data;
    } catch (error) {
      console.error('API Error fetching interactions:', error);
      throw error;
    }
  },
};
