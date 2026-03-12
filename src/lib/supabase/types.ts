export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.4"
  }
  public: {
    Tables: {
      agent_logs: {
        Row: {
          agent_name: string
          cost_usd: number | null
          created_at: string
          duration_ms: number | null
          error_message: string | null
          event_type: string
          id: string
          payload: Json | null
          run_id: string
          token_input: number | null
          token_output: number | null
        }
        Insert: {
          agent_name: string
          cost_usd?: number | null
          created_at?: string
          duration_ms?: number | null
          error_message?: string | null
          event_type: string
          id?: string
          payload?: Json | null
          run_id: string
          token_input?: number | null
          token_output?: number | null
        }
        Update: {
          agent_name?: string
          cost_usd?: number | null
          created_at?: string
          duration_ms?: number | null
          error_message?: string | null
          event_type?: string
          id?: string
          payload?: Json | null
          run_id?: string
          token_input?: number | null
          token_output?: number | null
        }
        Relationships: []
      }
      article_claims: {
        Row: {
          article_id: string
          claim_id: string
          position: number
        }
        Insert: {
          article_id: string
          claim_id: string
          position: number
        }
        Update: {
          article_id?: string
          claim_id?: string
          position?: number
        }
        Relationships: [
          {
            foreignKeyName: "article_claims_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "article_claims_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "claims"
            referencedColumns: ["id"]
          },
        ]
      }
      articles: {
        Row: {
          area: string
          body: string
          body_html: string | null
          certainty_score: number
          claim_review_json: Json | null
          created_at: string
          deleted_at: string | null
          embedding: string | null
          id: string
          impact_score: number | null
          language: string
          lead: string | null
          published_at: string | null
          review_notes: string | null
          reviewed_by: string | null
          slug: string
          status: string
          subtitle: string | null
          tags: string[] | null
          title: string
          updated_at: string
        }
        Insert: {
          area: string
          body: string
          body_html?: string | null
          certainty_score: number
          claim_review_json?: Json | null
          created_at?: string
          deleted_at?: string | null
          embedding?: string | null
          id?: string
          impact_score?: number | null
          language?: string
          lead?: string | null
          published_at?: string | null
          review_notes?: string | null
          reviewed_by?: string | null
          slug: string
          status?: string
          subtitle?: string | null
          tags?: string[] | null
          title: string
          updated_at?: string
        }
        Update: {
          area?: string
          body?: string
          body_html?: string | null
          certainty_score?: number
          claim_review_json?: Json | null
          created_at?: string
          deleted_at?: string | null
          embedding?: string | null
          id?: string
          impact_score?: number | null
          language?: string
          lead?: string | null
          published_at?: string | null
          review_notes?: string | null
          reviewed_by?: string | null
          slug?: string
          status?: string
          subtitle?: string | null
          tags?: string[] | null
          title?: string
          updated_at?: string
        }
        Relationships: []
      }
      claim_sources: {
        Row: {
          claim_id: string
          created_at: string
          excerpt: string | null
          source_id: string
          supports: boolean
        }
        Insert: {
          claim_id: string
          created_at?: string
          excerpt?: string | null
          source_id: string
          supports: boolean
        }
        Update: {
          claim_id?: string
          created_at?: string
          excerpt?: string | null
          source_id?: string
          supports?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "claim_sources_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "claims"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "claim_sources_source_id_fkey"
            columns: ["source_id"]
            isOneToOne: false
            referencedRelation: "sources"
            referencedColumns: ["id"]
          },
        ]
      }
      claims: {
        Row: {
          auditor_score: number | null
          claim_date: string | null
          confidence_score: number | null
          created_at: string
          embedding: string | null
          id: string
          object: string
          original_text: string
          predicate: string
          subject: string
          updated_at: string
          verification_status: string
        }
        Insert: {
          auditor_score?: number | null
          claim_date?: string | null
          confidence_score?: number | null
          created_at?: string
          embedding?: string | null
          id?: string
          object: string
          original_text: string
          predicate: string
          subject: string
          updated_at?: string
          verification_status?: string
        }
        Update: {
          auditor_score?: number | null
          claim_date?: string | null
          confidence_score?: number | null
          created_at?: string
          embedding?: string | null
          id?: string
          object?: string
          original_text?: string
          predicate?: string
          subject?: string
          updated_at?: string
          verification_status?: string
        }
        Relationships: []
      }
      counterfactual_cache: {
        Row: {
          article_id: string
          computed_at: string
          excluded_source_id: string
          explanation: string
          id: string
          revised_certainty: number
          revised_claims: Json
        }
        Insert: {
          article_id: string
          computed_at?: string
          excluded_source_id: string
          explanation: string
          id?: string
          revised_certainty: number
          revised_claims: Json
        }
        Update: {
          article_id?: string
          computed_at?: string
          excluded_source_id?: string
          explanation?: string
          id?: string
          revised_certainty?: number
          revised_claims?: Json
        }
        Relationships: [
          {
            foreignKeyName: "counterfactual_cache_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "counterfactual_cache_excluded_source_id_fkey"
            columns: ["excluded_source_id"]
            isOneToOne: false
            referencedRelation: "sources"
            referencedColumns: ["id"]
          },
        ]
      }
      hitl_reviews: {
        Row: {
          article_id: string
          confidence_at_trigger: number
          created_at: string
          id: string
          notified_at: string | null
          notified_via: string[] | null
          reason: string
          resolved_at: string | null
          reviewer_id: string | null
          reviewer_notes: string | null
          status: string
        }
        Insert: {
          article_id: string
          confidence_at_trigger: number
          created_at?: string
          id?: string
          notified_at?: string | null
          notified_via?: string[] | null
          reason: string
          resolved_at?: string | null
          reviewer_id?: string | null
          reviewer_notes?: string | null
          status?: string
        }
        Update: {
          article_id?: string
          confidence_at_trigger?: number
          created_at?: string
          id?: string
          notified_at?: string | null
          notified_via?: string[] | null
          reason?: string
          resolved_at?: string | null
          reviewer_id?: string | null
          reviewer_notes?: string | null
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "hitl_reviews_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
        ]
      }
      rationale_chains: {
        Row: {
          agent_name: string
          article_id: string | null
          claim_id: string | null
          created_at: string
          duration_ms: number | null
          id: string
          input_data: Json | null
          output_data: Json | null
          reasoning_text: string
          sources_used: string[] | null
          step_order: number
          token_count: number | null
        }
        Insert: {
          agent_name: string
          article_id?: string | null
          claim_id?: string | null
          created_at?: string
          duration_ms?: number | null
          id?: string
          input_data?: Json | null
          output_data?: Json | null
          reasoning_text: string
          sources_used?: string[] | null
          step_order: number
          token_count?: number | null
        }
        Update: {
          agent_name?: string
          article_id?: string | null
          claim_id?: string | null
          created_at?: string
          duration_ms?: number | null
          id?: string
          input_data?: Json | null
          output_data?: Json | null
          reasoning_text?: string
          sources_used?: string[] | null
          step_order?: number
          token_count?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "rationale_chains_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "rationale_chains_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "claims"
            referencedColumns: ["id"]
          },
        ]
      }
      sources: {
        Row: {
          content_hash: string
          created_at: string
          domain: string
          embedding: string | null
          fetched_at: string
          id: string
          metadata: Json | null
          raw_content: string | null
          reliability_score: number | null
          source_type: string
          title: string | null
          url: string
        }
        Insert: {
          content_hash: string
          created_at?: string
          domain: string
          embedding?: string | null
          fetched_at?: string
          id?: string
          metadata?: Json | null
          raw_content?: string | null
          reliability_score?: number | null
          source_type: string
          title?: string | null
          url: string
        }
        Update: {
          content_hash?: string
          created_at?: string
          domain?: string
          embedding?: string | null
          fetched_at?: string
          id?: string
          metadata?: Json | null
          raw_content?: string | null
          reliability_score?: number | null
          source_type?: string
          title?: string | null
          url?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      show_limit: { Args: never; Returns: number }
      show_trgm: { Args: { "": string }; Returns: string[] }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
