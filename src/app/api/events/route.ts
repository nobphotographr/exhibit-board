import { NextRequest, NextResponse } from 'next/server'
import { DatabaseService, EventValidator, type FilterRange } from '@/lib/database'

// GET /api/events - Fetch events with optional filters
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const range = searchParams.get('range') as FilterRange || 'upcoming'
    const prefecture = searchParams.get('prefecture')

    // Build filters object
    const filters: { range?: FilterRange; prefecture?: string } = {}
    
    if (range && range !== 'all') {
      filters.range = range
    }
    
    if (prefecture && prefecture !== 'all') {
      filters.prefecture = prefecture
    }

    // Fetch events from database
    const events = await DatabaseService.getEvents(filters)
    
    return NextResponse.json(events, { 
      status: 200,
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      }
    })
  } catch (error) {
    console.error('GET /api/events error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch events' }, 
      { status: 500 }
    )
  }
}

// POST /api/events - Create new event  
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Validate required fields
    const validation = EventValidator.validateEvent(body)
    if (!validation.valid) {
      return NextResponse.json(
        { 
          error_code: 'validation_error', 
          message: validation.errors.join(', '),
          errors: validation.errors
        },
        { status: 400 }
      )
    }

    // Check for duplicate announce URL
    const isDuplicate = await DatabaseService.checkDuplicateUrl(body.announce_url)
    if (isDuplicate) {
      return NextResponse.json(
        { 
          error_code: 'duplicate_url', 
          message: 'この告知URLは既に登録されています' 
        },
        { status: 409 }
      )
    }

    // Create the event
    const result = await DatabaseService.createEvent({
      title: body.title,
      host_name: body.host_name || null,
      x_url: body.x_url || null,
      ig_url: body.ig_url || null,
      threads_url: body.threads_url || null,
      venue: body.venue,
      address: body.address || null,
      prefecture: body.prefecture,
      price: body.price || null,
      start_date: body.start_date,
      end_date: body.end_date,
      announce_url: body.announce_url,
      notes: body.notes || null,
      status: 'published'
    })

    return NextResponse.json(result, { status: 201 })

  } catch (error) {
    console.error('POST /api/events error:', error)
    
    if (error instanceof Error) {
      return NextResponse.json(
        { 
          error_code: 'server_error', 
          message: error.message 
        },
        { status: 500 }
      )
    }
    
    return NextResponse.json(
      { 
        error_code: 'server_error', 
        message: 'Internal server error' 
      },
      { status: 500 }
    )
  }
}