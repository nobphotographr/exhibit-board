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
      // Return dummy data for layout testing
      const dummyEvents = [
        {
          id: '1',
          title: '白昼夢の憂鬱',
          host_name: '外山中美佳様',
          venue: 'ルーニィ247ファインアーツ',
          prefecture: '東京都',
          address: '東京都中央区日本橋小伝馬町17-9 さとうビルB階4F',
          start_date: '2025-09-04',
          end_date: '2025-09-14',
          price: null,
          announce_url: 'https://note.com/example1',
          x_url: 'https://x.com/example1',
          ig_url: null,
          threads_url: null,
          notes: '日常の中に潜む静寂な美しさを描いた作品展です。',
          status: 'published',
          created_at: '2025-09-01T00:00:00Z'
        },
        {
          id: '2',  
          title: 'TIMELESS',
          host_name: '森谷修様・久保元幸様',
          venue: 'ギャラリー冬青',
          prefecture: '東京都',
          address: '東京都中野区中央5-18-20',
          start_date: '2025-09-05',
          end_date: '2025-09-27',
          price: '無料',
          announce_url: 'https://gallery-touseisha.com/example',
          x_url: 'https://x.com/example2',
          ig_url: 'https://instagram.com/example2',
          threads_url: 'https://threads.com/example2',
          notes: '時を超えた美の探求をテーマに、二人の作家による共同展示を開催いたします。11:00〜19:00 日曜・月曜・祝日休廊',
          status: 'published',
          created_at: '2025-09-01T00:00:00Z'
        },
        {
          id: '3',
          title: '帰ってきた国産二眼レフ写真展',
          host_name: 'あめちゃん様',
          venue: 'フォトカノン戸越銀座',
          prefecture: '東京都', 
          address: '東京都品川区戸越2丁目1-3',
          start_date: '2025-09-12',
          end_date: '2025-09-24',
          price: null,
          announce_url: 'https://photokanon.example.com',
          x_url: 'https://x.com/example3',
          ig_url: null,
          threads_url: null,
          notes: 'スクエアフォーマット好きの国産二眼レフ好き34人による二眼レフ好きのためのグループ展',
          status: 'published',
          created_at: '2025-09-01T00:00:00Z'
        }
      ]
      
      return NextResponse.json(dummyEvents, { 
        status: 200,
        headers: {
          'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
        }
      })
    }

    // Build filters object
    const filters: { range?: FilterRange; prefecture?: string } = {}
    
    if (rangeParam && rangeParam !== 'all' && (rangeParam === 'upcoming' || rangeParam === 'thisMonth' || rangeParam === 'next30')) {
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