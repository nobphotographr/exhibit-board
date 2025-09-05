import { supabase, supabaseAdmin } from './supabase'
import { Event, EventInsert } from './database.types'

export type FilterRange = 'upcoming' | 'thisMonth' | 'next30'

export interface EventFilters {
  range?: FilterRange
  prefecture?: string
}

export class DatabaseService {
  // Get events with filters
  static async getEvents(filters?: EventFilters): Promise<Event[]> {
    let query = supabase
      .from('events')
      .select('*')
      .eq('status', 'published')
      .order('start_date', { ascending: true })

    // Apply date range filter
    if (filters?.range) {
      const now = new Date()
      const today = now.toISOString().split('T')[0]
      
      switch (filters.range) {
        case 'upcoming':
          // Events that haven't ended yet
          query = query.gte('end_date', today)
          break
        case 'thisMonth':
          // Events in current month
          const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0]
          const thisMonthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0]
          query = query.gte('start_date', thisMonthStart).lte('start_date', thisMonthEnd)
          break
        case 'next30':
          // Events starting within next 30 days
          const next30Days = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
          query = query.gte('start_date', today).lte('start_date', next30Days)
          break
      }
    }

    // Apply prefecture filter
    if (filters?.prefecture) {
      query = query.eq('prefecture', filters.prefecture)
    }

    const { data, error } = await query

    if (error) {
      console.error('Error fetching events:', error)
      throw new Error(`Failed to fetch events: ${error.message}`)
    }

    return data || []
  }

  // Create a new event (server-side only)
  static async createEvent(eventData: EventInsert): Promise<{ id: string }> {
    const adminClient = supabaseAdmin()
    
    const { data, error } = await adminClient
      .from('events')
      .insert(eventData)
      .select('id')
      .single()

    if (error) {
      console.error('Error creating event:', error)
      throw new Error(`Failed to create event: ${error.message}`)
    }

    if (!data) {
      throw new Error('No data returned from event creation')
    }

    return { id: data.id }
  }

  // Check if announce URL already exists
  static async checkDuplicateUrl(announceUrl: string): Promise<boolean> {
    const { data, error } = await supabase
      .from('events')
      .select('id')
      .eq('announce_url', announceUrl)
      .maybeSingle()

    if (error) {
      console.error('Error checking duplicate URL:', error)
      throw new Error(`Failed to check duplicate URL: ${error.message}`)
    }

    return !!data
  }
}

// Event validation utilities
export class EventValidator {
  // Validate URLs based on allowed domains
  static validateUrl(url: string, type: 'x' | 'instagram' | 'threads' | 'announce'): boolean {
    if (!url) return true // Optional fields are valid when empty
    
    try {
      const urlObj = new URL(url)
      const domain = urlObj.hostname.toLowerCase()
      
      switch (type) {
        case 'x':
          return domain === 'x.com' || domain === 'twitter.com'
        case 'instagram':
          return domain === 'instagram.com' || domain === 'www.instagram.com'
        case 'threads':
          return domain === 'threads.net' || domain === 'www.threads.net'
        case 'announce':
          // For announce URL, we can be more flexible but should validate it's a real URL
          return ['x.com', 'twitter.com', 'instagram.com', 'www.instagram.com', 'threads.net', 'www.threads.net'].includes(domain)
        default:
          return false
      }
    } catch {
      return false
    }
  }

  // Validate date range
  static validateDateRange(startDate: string, endDate: string): boolean {
    const start = new Date(startDate)
    const end = new Date(endDate)
    return end >= start
  }

  // Validate required fields
  static validateRequiredFields(eventData: EventInsert): string[] {
    const errors: string[] = []
    
    if (!eventData.title?.trim()) errors.push('Title is required')
    if (!eventData.venue?.trim()) errors.push('Venue is required')
    if (!eventData.prefecture) errors.push('Prefecture is required')
    if (!eventData.start_date) errors.push('Start date is required')
    if (!eventData.end_date) errors.push('End date is required')
    if (!eventData.announce_url?.trim()) errors.push('Announce URL is required')
    
    return errors
  }

  // Comprehensive validation
  static validateEvent(eventData: EventInsert): { valid: boolean; errors: string[] } {
    const errors: string[] = []
    
    // Check required fields
    errors.push(...this.validateRequiredFields(eventData))
    
    // Validate URLs
    if (eventData.x_url && !this.validateUrl(eventData.x_url, 'x')) {
      errors.push('Invalid X/Twitter URL')
    }
    if (eventData.ig_url && !this.validateUrl(eventData.ig_url, 'instagram')) {
      errors.push('Invalid Instagram URL')
    }
    if (eventData.threads_url && !this.validateUrl(eventData.threads_url, 'threads')) {
      errors.push('Invalid Threads URL')
    }
    if (eventData.announce_url && !this.validateUrl(eventData.announce_url, 'announce')) {
      errors.push('Invalid announce URL domain')
    }
    
    // Validate date range
    if (eventData.start_date && eventData.end_date && 
        !this.validateDateRange(eventData.start_date, eventData.end_date)) {
      errors.push('End date must be on or after start date')
    }
    
    return {
      valid: errors.length === 0,
      errors
    }
  }
}