import { NextRequest, NextResponse } from 'next/server'

// GET /api/events - Fetch events with optional filters
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const range = searchParams.get('range') || 'upcoming' // デフォルトは「これから」
    const prefecture = searchParams.get('prefecture')

    // Demo mode - サンプルデータを返す
    console.log('Demo API called with filters:', { range, prefecture })
    
    // サンプルデータ
    const sampleEvents = [
      {
        id: 'sample-1',
        title: '個展「春のキャンバス」',
        host_name: '山田花子',
        x_url: 'https://x.com/hanako_art',
        ig_url: 'https://instagram.com/hanako_paintings',
        threads_url: null,
        venue: 'ギャラリー青空',
        address: '渋谷区神南1-2-3',
        prefecture: '東京都',
        price: '入場無料',
        start_date: '2025-01-15',
        end_date: '2025-01-28',
        announce_url: 'https://x.com/hanako_art/status/example',
        notes: '新作油彩画20点を展示します。お気軽にお立ち寄りください！',
        status: 'published',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z'
      },
      {
        id: 'sample-2',
        title: 'グループ展「都市の記憶」',
        host_name: '現代美術協会',
        x_url: 'https://x.com/gendai_art',
        ig_url: null,
        threads_url: 'https://threads.net/@gendai_art',
        venue: 'アートスペース新宿',
        address: null,
        prefecture: '東京都',
        price: '大人500円、学生300円',
        start_date: '2025-02-01',
        end_date: '2025-02-14',
        announce_url: 'https://x.com/gendai_art/status/example2',
        notes: '若手アーティスト5名による写真・映像作品展。現代都市をテーマにした力作揃いです。',
        status: 'published',
        created_at: '2025-01-02T00:00:00Z',
        updated_at: '2025-01-02T00:00:00Z'
      },
      {
        id: 'sample-3',
        title: '陶芸展「土の詩」',
        host_name: '佐藤陶房',
        x_url: null,
        ig_url: 'https://instagram.com/sato_pottery',
        threads_url: null,
        venue: '横浜市民ギャラリー',
        address: '横浜市西区宮崎町2-1',
        prefecture: '神奈川県',
        price: '無料',
        start_date: '2025-01-20',
        end_date: '2025-02-05',
        announce_url: 'https://instagram.com/p/example3',
        notes: '備前焼を中心とした陶芸作品約30点。実際に触れる体験コーナーもあります。',
        status: 'published',
        created_at: '2025-01-03T00:00:00Z',
        updated_at: '2025-01-03T00:00:00Z'
      }
    ]

    // 簡単なフィルタリング（デモ用）
    let filteredEvents = sampleEvents

    if (prefecture && prefecture !== 'all') {
      filteredEvents = filteredEvents.filter(event => event.prefecture === prefecture)
    }

    // 日付フィルタは実装済みとして全て返す（デモ用）
    
    return NextResponse.json(filteredEvents, { 
      status: 200,
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      }
    })
  } catch (error) {
    return NextResponse.json([], { status: 200 })
  }
}

// POST /api/events - Create new event  
export async function POST(request: NextRequest) {
  // Demo mode - return success without actually saving
  try {
    const body = await request.json()
    
    // Basic validation
    if (!body.title || !body.venue || !body.start_date || !body.end_date || !body.announce_url) {
      return NextResponse.json(
        { error_code: 'validation_error', message: '必須項目が不足しています' },
        { status: 400 }
      )
    }

    // Demo mode: simulate success
    return NextResponse.json(
      { 
        id: 'demo-' + Date.now(), 
        message: '🎉 デモモードで送信されました！実際には保存されていませんが、Supabaseを設定すると正常に保存されます。' 
      },
      { status: 201 }
    )

  } catch (error) {
    return NextResponse.json(
      { error_code: 'server_error', message: 'Internal server error' },
      { status: 500 }
    )
  }
}