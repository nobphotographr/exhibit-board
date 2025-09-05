export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type JpPrefecture =
  | '北海道'
  | '青森県'
  | '岩手県'
  | '宮城県'
  | '秋田県'
  | '山形県'
  | '福島県'
  | '茨城県'
  | '栃木県'
  | '群馬県'
  | '埼玉県'
  | '千葉県'
  | '東京都'
  | '神奈川県'
  | '新潟県'
  | '富山県'
  | '石川県'
  | '福井県'
  | '山梨県'
  | '長野県'
  | '岐阜県'
  | '静岡県'
  | '愛知県'
  | '三重県'
  | '滋賀県'
  | '京都府'
  | '大阪府'
  | '兵庫県'
  | '奈良県'
  | '和歌山県'
  | '鳥取県'
  | '島根県'
  | '岡山県'
  | '広島県'
  | '山口県'
  | '徳島県'
  | '香川県'
  | '愛媛県'
  | '高知県'
  | '福岡県'
  | '佐賀県'
  | '長崎県'
  | '熊本県'
  | '大分県'
  | '宮崎県'
  | '鹿児島県'
  | '沖縄県'

export type EventStatus = 'published' | 'pending' | 'rejected'

export interface Database {
  public: {
    Tables: {
      events: {
        Row: {
          id: string
          title: string
          host_name: string | null
          x_url: string | null
          ig_url: string | null
          threads_url: string | null
          venue: string
          address: string | null
          prefecture: JpPrefecture
          price: string | null
          start_date: string
          end_date: string
          announce_url: string
          notes: string | null
          status: EventStatus
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          title: string
          host_name?: string | null
          x_url?: string | null
          ig_url?: string | null
          threads_url?: string | null
          venue: string
          address?: string | null
          prefecture: JpPrefecture
          price?: string | null
          start_date: string
          end_date: string
          announce_url: string
          notes?: string | null
          status?: EventStatus
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          title?: string
          host_name?: string | null
          x_url?: string | null
          ig_url?: string | null
          threads_url?: string | null
          venue?: string
          address?: string | null
          prefecture?: JpPrefecture
          price?: string | null
          start_date?: string
          end_date?: string
          announce_url?: string
          notes?: string | null
          status?: EventStatus
          created_at?: string
          updated_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      jp_prefecture: JpPrefecture
      event_status: EventStatus
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

export type Event = Database['public']['Tables']['events']['Row']
export type EventInsert = Database['public']['Tables']['events']['Insert']
export type EventUpdate = Database['public']['Tables']['events']['Update']