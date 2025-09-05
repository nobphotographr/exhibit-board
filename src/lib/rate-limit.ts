// Simple in-memory rate limiting (for development)
// In production, you might want to use Redis or database storage

interface RateLimitEntry {
  count: number
  resetTime: number
}

class InMemoryRateLimit {
  private storage = new Map<string, RateLimitEntry>()
  private readonly windowMs: number
  private readonly maxRequests: number

  constructor(windowMs = 3600000, maxRequests = 5) { // 1 hour, 5 requests
    this.windowMs = windowMs
    this.maxRequests = maxRequests
    
    // Clean up expired entries every hour
    setInterval(() => this.cleanup(), this.windowMs)
  }

  private cleanup() {
    const now = Date.now()
    for (const [key, entry] of this.storage.entries()) {
      if (now > entry.resetTime) {
        this.storage.delete(key)
      }
    }
  }

  check(identifier: string): { allowed: boolean; remaining: number; resetTime: number } {
    const now = Date.now()
    const entry = this.storage.get(identifier)

    if (!entry || now > entry.resetTime) {
      // First request or window expired
      const newEntry: RateLimitEntry = {
        count: 1,
        resetTime: now + this.windowMs
      }
      this.storage.set(identifier, newEntry)
      
      return {
        allowed: true,
        remaining: this.maxRequests - 1,
        resetTime: newEntry.resetTime
      }
    }

    if (entry.count >= this.maxRequests) {
      // Rate limit exceeded
      return {
        allowed: false,
        remaining: 0,
        resetTime: entry.resetTime
      }
    }

    // Increment count and allow
    entry.count++
    this.storage.set(identifier, entry)
    
    return {
      allowed: true,
      remaining: this.maxRequests - entry.count,
      resetTime: entry.resetTime
    }
  }
}

// Singleton instance
const rateLimiter = new InMemoryRateLimit(
  parseInt(process.env.RATE_LIMIT_WINDOW || '3600', 10) * 1000, // Convert to milliseconds
  parseInt(process.env.RATE_LIMIT_MAX || '5', 10)
)

export function checkRateLimit(ip: string) {
  return rateLimiter.check(ip)
}

// Get client IP from request headers
export function getClientIP(request: Request): string {
  // Check common headers for client IP
  const forwarded = request.headers.get('x-forwarded-for')
  const realIp = request.headers.get('x-real-ip')
  const cfConnectingIp = request.headers.get('cf-connecting-ip')
  
  if (forwarded) {
    // x-forwarded-for can contain multiple IPs, get the first one
    return forwarded.split(',')[0].trim()
  }
  
  if (realIp) {
    return realIp
  }
  
  if (cfConnectingIp) {
    return cfConnectingIp
  }
  
  // Fallback
  return 'unknown'
}