import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co'
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder-key'

// Client-side Supabase client (read-only for public access)
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Server-side Supabase client (write access with service role key)
export const supabaseAdmin = () => {
  const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY || 'placeholder-service-key'
  return createClient(supabaseUrl, supabaseServiceKey)
}