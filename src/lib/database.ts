import { supabase, supabaseAdmin } from './supabase'
import { Event, EventInsert } from './database.types'
import { isMajorEvent } from './venue-classifier'

export type FilterRange = 'upcoming' | 'ongoing' | 'thisWeek' | 'thisMonth'
export type VenueType = 'all' | 'major' | 'independent'

export interface EventFilters {
  range?: FilterRange
  prefecture?: string
  venueType?: VenueType
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
          
        case 'ongoing':
          // Events currently happening (today is within the event period)
          query = query.lte('start_date', today).gte('end_date', today)
          break
          
        case 'thisWeek':
          // Events happening this week (overlapping with current week AND not ended yet)
          const startOfWeek = new Date(now)
          startOfWeek.setDate(now.getDate() - now.getDay()) // Go to Sunday
          const endOfWeek = new Date(startOfWeek)
          endOfWeek.setDate(startOfWeek.getDate() + 6) // Go to Saturday
          
          const weekStart = startOfWeek.toISOString().split('T')[0]
          const weekEnd = endOfWeek.toISOString().split('T')[0]
          
          // Event overlaps with this week AND hasn't ended yet
          query = query.lte('start_date', weekEnd).gte('end_date', weekStart).gte('end_date', today)
          break
          
        case 'thisMonth':
          // Events happening this month (overlapping with current month AND not ended yet)
          const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0]
          const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0]
          
          // Event overlaps with this month AND hasn't ended yet
          query = query.lte('start_date', monthEnd).gte('end_date', monthStart).gte('end_date', today)
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

    let events = data || []

    // Apply venue type filter (client-side filtering due to venue name patterns)
    if (filters?.venueType && filters.venueType !== 'all') {
      events = events.filter(event => {
        const isMajor = isMajorEvent(event.venue, event.title, event.host_name)
        return filters.venueType === 'major' ? isMajor : !isMajor
      })
    }

    return events
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
          return domain === 'threads.com' || domain === 'www.threads.com'
        case 'announce':
          // For announce URL, be more flexible - accept most legitimate domains
          // Block only obviously suspicious patterns
          const blockedPatterns = [
            /localhost/,
            /127\.0\.0\.1/,
            /\d+\.\d+\.\d+\.\d+/, // IP addresses
            /\.test$/,
            /\.local$/,
            /\.internal$/
          ]
          
          // Check if domain matches blocked patterns
          for (const pattern of blockedPatterns) {
            if (pattern.test(domain)) {
              return false
            }
          }
          
          // Allow legitimate domains with proper structure
          // Must have at least one dot and end with valid TLD
          const domainParts = domain.split('.')
          if (domainParts.length < 2) return false
          
          // Check each part is valid (alphanumeric and hyphens, not starting/ending with hyphen)
          for (const part of domainParts) {
            if (!part || !/^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$/.test(part)) {
              return false
            }
          }
          
          // Check TLD is at least 2 characters and alphabetic
          const tld = domainParts[domainParts.length - 1]
          return /^[a-zA-Z]{2,}$/.test(tld)
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