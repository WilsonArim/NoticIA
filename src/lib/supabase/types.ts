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
          bias_analysis: Json | null
          bias_score: number | null
          body: string
          body_html: string | null
          certainty_score: number
          claim_review_json: Json | null
          created_at: string
          deleted_at: string | null
          debunk_note: string | null
          embedding: string | null
          id: string
          impact_score: number | null
          language: string
          lead: string | null
          priority: string | null
          published_at: string | null
          review_notes: string | null
          reviewed_by: string | null
          slug: string
          status: string
          subtitle: string | null
          tags: string[] | null
          title: string
          updated_at: string
          verification_changed_at: string | null
          verification_status: string
        }
        Insert: {
          area: string
          bias_analysis?: Json | null
          bias_score?: number | null
          body: string
          body_html?: string | null
          certainty_score: number
          claim_review_json?: Json | null
          created_at?: string
          deleted_at?: string | null
          debunk_note?: string | null
          embedding?: string | null
          id?: string
          impact_score?: number | null
          language?: string
          lead?: string | null
          priority?: string | null
          published_at?: string | null
          review_notes?: string | null
          reviewed_by?: string | null
          slug: string
          status?: string
          subtitle?: string | null
          tags?: string[] | null
          title: string
          updated_at?: string
          verification_changed_at?: string | null
          verification_status?: string
        }
        Update: {
          area?: string
          bias_analysis?: Json | null
          bias_score?: number | null
          body?: string
          body_html?: string | null
          certainty_score?: number
          claim_review_json?: Json | null
          created_at?: string
          deleted_at?: string | null
          debunk_note?: string | null
          embedding?: string | null
          id?: string
          impact_score?: number | null
          language?: string
          lead?: string | null
          priority?: string | null
          published_at?: string | null
          review_notes?: string | null
          reviewed_by?: string | null
          slug?: string
          status?: string
          subtitle?: string | null
          tags?: string[] | null
          title?: string
          updated_at?: string
          verification_changed_at?: string | null
          verification_status?: string
        }
        Relationships: []
      }
      claim_embeddings: {
        Row: {
          claim_text: string
          confidence_score: number | null
          embedding: string | null
          expires_at: string | null
          id: string
          rationale_chain: Json | null
          sources_checked: string[] | null
          verdict: string | null
          verified_at: string | null
        }
        Insert: {
          claim_text: string
          confidence_score?: number | null
          embedding?: string | null
          expires_at?: string | null
          id?: string
          rationale_chain?: Json | null
          sources_checked?: string[] | null
          verdict?: string | null
          verified_at?: string | null
        }
        Update: {
          claim_text?: string
          confidence_score?: number | null
          embedding?: string | null
          expires_at?: string | null
          id?: string
          rationale_chain?: Json | null
          sources_checked?: string[] | null
          verdict?: string | null
          verified_at?: string | null
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
      collector_configs: {
        Row: {
          collector_name: string
          config: Json
          created_at: string | null
          enabled: boolean | null
          id: string
          interval_minutes: number
          last_run_at: string | null
          last_run_events: number | null
          last_run_status: string | null
        }
        Insert: {
          collector_name: string
          config?: Json
          created_at?: string | null
          enabled?: boolean | null
          id?: string
          interval_minutes: number
          last_run_at?: string | null
          last_run_events?: number | null
          last_run_status?: string | null
        }
        Update: {
          collector_name?: string
          config?: Json
          created_at?: string | null
          enabled?: boolean | null
          id?: string
          interval_minutes?: number
          last_run_at?: string | null
          last_run_events?: number | null
          last_run_status?: string | null
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
      fact_checker_configs: {
        Row: {
          check_type: string
          checker_name: string
          created_at: string | null
          enabled: boolean | null
          grok_system_prompt: string | null
          id: string
          skill_version: string | null
          tools_config: Json | null
          updated_at: string | null
        }
        Insert: {
          check_type: string
          checker_name: string
          created_at?: string | null
          enabled?: boolean | null
          grok_system_prompt?: string | null
          id?: string
          skill_version?: string | null
          tools_config?: Json | null
          updated_at?: string | null
        }
        Update: {
          check_type?: string
          checker_name?: string
          created_at?: string | null
          enabled?: boolean | null
          grok_system_prompt?: string | null
          id?: string
          skill_version?: string | null
          tools_config?: Json | null
          updated_at?: string | null
        }
        Relationships: []
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
      intake_queue: {
        Row: {
          area: string
          auditor_result: Json | null
          auditor_score: number | null
          claims: Json | null
          content: string
          created_at: string
          editor_decision: string | null
          editor_scores: Json | null
          error_message: string | null
          fact_check_summary: Json | null
          id: string
          language: string
          metadata: Json | null
          priority: string | null
          processed_article_id: string | null
          processed_at: string | null
          rationale: Json | null
          received_at: string
          score: number
          source_event_id: string | null
          sources: Json | null
          status: string
          title: string
          url: string | null
        }
        Insert: {
          area: string
          auditor_result?: Json | null
          auditor_score?: number | null
          claims?: Json | null
          content: string
          created_at?: string
          editor_decision?: string | null
          editor_scores?: Json | null
          error_message?: string | null
          fact_check_summary?: Json | null
          id?: string
          language?: string
          metadata?: Json | null
          priority?: string | null
          processed_article_id?: string | null
          processed_at?: string | null
          rationale?: Json | null
          received_at?: string
          score?: number
          source_event_id?: string | null
          sources?: Json | null
          status?: string
          title: string
          url?: string | null
        }
        Update: {
          area?: string
          auditor_result?: Json | null
          auditor_score?: number | null
          claims?: Json | null
          content?: string
          created_at?: string
          editor_decision?: string | null
          editor_scores?: Json | null
          error_message?: string | null
          fact_check_summary?: Json | null
          id?: string
          language?: string
          metadata?: Json | null
          priority?: string | null
          processed_article_id?: string | null
          processed_at?: string | null
          rationale?: Json | null
          received_at?: string
          score?: number
          source_event_id?: string | null
          sources?: Json | null
          status?: string
          title?: string
          url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "intake_queue_processed_article_id_fkey"
            columns: ["processed_article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
        ]
      }
      pipeline_runs: {
        Row: {
          completed_at: string | null
          cost_usd: number | null
          created_at: string | null
          error_message: string | null
          events_in: number | null
          events_out: number | null
          id: string
          metadata: Json | null
          stage: string
          started_at: string | null
          status: string
          token_input: number | null
          token_output: number | null
        }
        Insert: {
          completed_at?: string | null
          cost_usd?: number | null
          created_at?: string | null
          error_message?: string | null
          events_in?: number | null
          events_out?: number | null
          id?: string
          metadata?: Json | null
          stage: string
          started_at?: string | null
          status?: string
          token_input?: number | null
          token_output?: number | null
        }
        Update: {
          completed_at?: string | null
          cost_usd?: number | null
          created_at?: string | null
          error_message?: string | null
          events_in?: number | null
          events_out?: number | null
          id?: string
          metadata?: Json | null
          stage?: string
          started_at?: string | null
          status?: string
          token_input?: number | null
          token_output?: number | null
        }
        Relationships: []
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
      raw_events: {
        Row: {
          content: string
          created_at: string | null
          event_hash: string
          fetched_at: string | null
          id: string
          processed: boolean | null
          published_at: string | null
          raw_metadata: Json | null
          source_collector: string
          title: string
          url: string | null
        }
        Insert: {
          content: string
          created_at?: string | null
          event_hash: string
          fetched_at?: string | null
          id?: string
          processed?: boolean | null
          published_at?: string | null
          raw_metadata?: Json | null
          source_collector: string
          title: string
          url?: string | null
        }
        Update: {
          content?: string
          created_at?: string | null
          event_hash?: string
          fetched_at?: string | null
          id?: string
          processed?: boolean | null
          published_at?: string | null
          raw_metadata?: Json | null
          source_collector?: string
          title?: string
          url?: string | null
        }
        Relationships: []
      }
      reporter_configs: {
        Row: {
          area: string
          created_at: string | null
          enabled: boolean | null
          grok_system_prompt: string | null
          id: string
          keywords: string[]
          max_per_batch: number | null
          priority_collectors: string[]
          skill_version: string | null
          threshold: number
          updated_at: string | null
        }
        Insert: {
          area: string
          created_at?: string | null
          enabled?: boolean | null
          grok_system_prompt?: string | null
          id?: string
          keywords: string[]
          max_per_batch?: number | null
          priority_collectors: string[]
          skill_version?: string | null
          threshold?: number
          updated_at?: string | null
        }
        Update: {
          area?: string
          created_at?: string | null
          enabled?: boolean | null
          grok_system_prompt?: string | null
          id?: string
          keywords?: string[]
          max_per_batch?: number | null
          priority_collectors?: string[]
          skill_version?: string | null
          threshold?: number
          updated_at?: string | null
        }
        Relationships: []
      }
      scored_events: {
        Row: {
          area: string
          created_at: string | null
          curated: boolean | null
          curator_batch_id: string | null
          curator_rank: number | null
          id: string
          matched_keywords: string[] | null
          raw_event_id: string
          reporter_score: number
        }
        Insert: {
          area: string
          created_at?: string | null
          curated?: boolean | null
          curator_batch_id?: string | null
          curator_rank?: number | null
          id?: string
          matched_keywords?: string[] | null
          raw_event_id: string
          reporter_score: number
        }
        Update: {
          area?: string
          created_at?: string | null
          curated?: boolean | null
          curator_batch_id?: string | null
          curator_rank?: number | null
          id?: string
          matched_keywords?: string[] | null
          raw_event_id?: string
          reporter_score?: number
        }
        Relationships: [
          {
            foreignKeyName: "scored_events_raw_event_id_fkey"
            columns: ["raw_event_id"]
            isOneToOne: false
            referencedRelation: "raw_events"
            referencedColumns: ["id"]
          },
        ]
      }
      source_credibility: {
        Row: {
          bias_direction: string | null
          bias_flags: string[] | null
          category: string | null
          created_at: string | null
          domain: string
          id: string
          name: string
          notes: string | null
          tier: number
          updated_at: string | null
          weight: number
        }
        Insert: {
          bias_direction?: string | null
          bias_flags?: string[] | null
          category?: string | null
          created_at?: string | null
          domain: string
          id?: string
          name: string
          notes?: string | null
          tier: number
          updated_at?: string | null
          weight: number
        }
        Update: {
          bias_direction?: string | null
          bias_flags?: string[] | null
          category?: string | null
          created_at?: string | null
          domain?: string
          id?: string
          name?: string
          notes?: string | null
          tier?: number
          updated_at?: string | null
          weight?: number
        }
        Relationships: []
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
      token_logs: {
        Row: {
          cached_tokens: number | null
          call_name: string
          cost_usd: number | null
          id: string
          input_tokens: number | null
          model: string | null
          output_tokens: number | null
          priority: string | null
          timestamp: string | null
        }
        Insert: {
          cached_tokens?: number | null
          call_name: string
          cost_usd?: number | null
          id?: string
          input_tokens?: number | null
          model?: string | null
          output_tokens?: number | null
          priority?: string | null
          timestamp?: string | null
        }
        Update: {
          cached_tokens?: number | null
          call_name?: string
          cost_usd?: number | null
          id?: string
          input_tokens?: number | null
          model?: string | null
          output_tokens?: number | null
          priority?: string | null
          timestamp?: string | null
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
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
