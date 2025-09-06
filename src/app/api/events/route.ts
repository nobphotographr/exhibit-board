import { NextRequest, NextResponse } from 'next/server'
import { DatabaseService, EventValidator, type FilterRange } from '@/lib/database'

// GET /api/events - Fetch events with optional filters
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const rangeParam = searchParams.get('range')
    const prefecture = searchParams.get('prefecture')

    // Check if running in development mode without Supabase
    const isDemoMode = !process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.NODE_ENV === 'development'
    
    if (isDemoMode) {
      // Create dummy data with varied dates for testing filters
      const now = new Date()
      const today = now.toISOString().split('T')[0]
      
      // Yesterday (ended)
      const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      // Tomorrow (starting soon)  
      const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      // Next week
      const nextWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      // Next month
      const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 15).toISOString().split('T')[0]
      
      let dummyEvents = [
        {
          id: '1',
          title: '開催中の展示',
          host_name: '外山中美佳様',
          venue: 'ルーニィ247ファインアーツ',
          prefecture: '東京都',
          address: '東京都中央区日本橋小伝馬町17-9 さとうビルB階4F',
          start_date: yesterday,
          end_date: tomorrow,
          price: null,
          announce_url: 'https://note.com/example1',
          x_url: 'https://x.com/example1',
          ig_url: null,
          threads_url: null,
          notes: '現在開催中の展示です。',
          status: 'published',
          created_at: '2025-09-01T00:00:00Z'
        },
        {
          id: '2',  
          title: '今週の展示',
          host_name: '森谷修様・久保元幸様',
          venue: 'ギャラリー冬青',
          prefecture: '東京都',
          address: '東京都中野区中央5-18-20',
          start_date: today,
          end_date: nextWeek,
          price: '無料',
          announce_url: 'https://gallery-touseisha.com/example',
          x_url: 'https://x.com/example2',
          ig_url: 'https://instagram.com/example2',
          threads_url: 'https://threads.com/example2',
          notes: '今週開催の展示です。',
          status: 'published',
          created_at: '2025-09-01T00:00:00Z'
        },
        {
          id: '3',
          title: '来月の展示',
          host_name: 'あめちゃん様',
          venue: 'フォトカノン戸越銀座',
          prefecture: '東京都', 
          address: '東京都品川区戸越2丁目1-3',
          start_date: nextMonth,
          end_date: new Date(now.getFullYear(), now.getMonth() + 1, 28).toISOString().split('T')[0],
          price: null,
          announce_url: 'https://photokanon.example.com',
          x_url: 'https://x.com/example3',
          ig_url: null,
          threads_url: null,
          notes: '来月開催予定の展示です。',
          status: 'published',
          created_at: '2025-09-01T00:00:00Z'
        },
        {
          id: '4',
          title: '終了済みの展示',
          host_name: 'テスト様',
          venue: 'テストギャラリー',
          prefecture: '大阪府',
          address: '大阪府大阪市中央区',
          start_date: new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end_date: yesterday,
          price: '500円',
          announce_url: 'https://test.example.com',
          x_url: null,
          ig_url: null,
          threads_url: null,
          notes: '既に終了した展示です。',
          status: 'published',
          created_at: '2025-08-01T00:00:00Z'
        }
      ]

      // Apply same filtering logic as real data
      const filters: { range?: FilterRange; prefecture?: string } = {}
      
      if (rangeParam && rangeParam !== 'all' && (rangeParam === 'upcoming' || rangeParam === 'ongoing' || rangeParam === 'thisWeek' || rangeParam === 'thisMonth')) {
        filters.range = rangeParam as FilterRange
      } else if (!rangeParam || rangeParam === 'all') {
        filters.range = 'upcoming'
      }
      
      if (prefecture && prefecture !== 'all') {
        filters.prefecture = prefecture
      }

      // Filter dummy data
      if (filters.range) {
        dummyEvents = dummyEvents.filter(event => {
          const eventStart = new Date(event.start_date)
          const eventEnd = new Date(event.end_date)
          
          switch (filters.range) {
            case 'upcoming':
              return eventEnd >= new Date(today)
              
            case 'ongoing':
              return eventStart <= new Date(today) && eventEnd >= new Date(today)
              
            case 'thisWeek':
              const startOfWeek = new Date(now)
              startOfWeek.setDate(now.getDate() - now.getDay())
              const endOfWeek = new Date(startOfWeek)
              endOfWeek.setDate(startOfWeek.getDate() + 6)
              // Event overlaps with this week AND hasn't ended yet
              return eventStart <= endOfWeek && eventEnd >= startOfWeek && eventEnd >= new Date(today)
              
            case 'thisMonth':
              const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)
              const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0)
              // Event overlaps with this month AND hasn't ended yet
              return eventStart <= monthEnd && eventEnd >= monthStart && eventEnd >= new Date(today)
              
            default:
              return true
          }
        })
      }

      // Filter by prefecture
      if (filters.prefecture) {
        dummyEvents = dummyEvents.filter(event => event.prefecture === filters.prefecture)
      }
      
      return NextResponse.json(dummyEvents, { 
        status: 200,
        headers: {
          'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
        }
      })
    }

    // Build filters object
    const filters: { range?: FilterRange; prefecture?: string } = {}
    
    if (rangeParam && rangeParam !== 'all' && (rangeParam === 'upcoming' || rangeParam === 'ongoing' || rangeParam === 'thisWeek' || rangeParam === 'thisMonth')) {
      filters.range = rangeParam as FilterRange
    } else if (!rangeParam || rangeParam === 'all') {
      // Default to upcoming if no range specified or 'all'
      filters.range = 'upcoming'
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