import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { supabaseAdmin } from '@/lib/supabase'
import type { Json } from '@/lib/database.types'

const extractedSchema = z.object({
  title: z.string().trim().min(1).max(300).nullable(),
  host_name: z.string().trim().max(200).nullable().optional(),
  venue: z.string().trim().max(300).nullable(),
  address: z.string().trim().max(500).nullable().optional(),
  prefecture: z.string().trim().max(10).nullable(),
  price: z.string().trim().max(100).nullable().optional(),
  start_date: z.string().date().nullable(),
  end_date: z.string().date().nullable(),
  notes: z.string().trim().max(1000).nullable().optional(),
})

const candidateSchema = z.object({
  event_fingerprint: z.string().regex(/^[a-f0-9]{64}$/),
  confidence: z.number().min(0).max(1),
  extracted: extractedSchema,
  source: z.object({
    type: z.enum(['x', 'website', 'manual']),
    key: z.string().trim().min(1).max(500),
    url: z.string().url().max(2000),
    name: z.string().trim().max(200).nullable().optional(),
    author_handle: z.string().trim().max(100).nullable().optional(),
    content_hash: z.string().regex(/^[a-f0-9]{64}$/).nullable().optional(),
  }),
})

function authorized(request: NextRequest): boolean {
  const expected = process.env.COLLECTOR_API_KEY
  if (!expected) return false
  return request.headers.get('authorization') === `Bearer ${expected}`
}

export async function POST(request: NextRequest) {
  if (!authorized(request)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const parsed = candidateSchema.safeParse(await request.json())
  if (!parsed.success) {
    return NextResponse.json(
      { error: 'Invalid candidate', details: parsed.error.flatten() },
      { status: 400 },
    )
  }

  const payload = parsed.data
  const admin = supabaseAdmin()
  const now = new Date().toISOString()

  const { data: existing, error: lookupError } = await admin
    .from('event_candidates')
    .select('id,status,confidence')
    .eq('event_fingerprint', payload.event_fingerprint)
    .maybeSingle()

  if (lookupError) {
    console.error('Candidate lookup failed:', lookupError)
    return NextResponse.json({ error: 'Candidate lookup failed' }, { status: 500 })
  }

  let candidateId: string

  if (existing) {
    candidateId = existing.id

    // A collector may refresh pending metadata, but must never reset a human decision.
    const update = existing.status === 'pending'
      ? {
          extracted: payload.extracted as Json,
          confidence: Math.max(Number(existing.confidence), payload.confidence),
          last_seen_at: now,
        }
      : { last_seen_at: now }

    const { error } = await admin
      .from('event_candidates')
      .update(update)
      .eq('id', candidateId)

    if (error) {
      console.error('Candidate update failed:', error)
      return NextResponse.json({ error: 'Candidate update failed' }, { status: 500 })
    }
  } else {
    const { data, error } = await admin
      .from('event_candidates')
      .insert({
        event_fingerprint: payload.event_fingerprint,
        extracted: payload.extracted as Json,
        confidence: payload.confidence,
        status: 'pending',
        first_seen_at: now,
        last_seen_at: now,
      })
      .select('id')
      .single()

    if (error || !data) {
      console.error('Candidate insert failed:', error)
      return NextResponse.json({ error: 'Candidate insert failed' }, { status: 500 })
    }

    candidateId = data.id
  }

  const { error: sourceError } = await admin
    .from('candidate_sources')
    .upsert(
      {
        candidate_id: candidateId,
        source_type: payload.source.type,
        source_key: payload.source.key,
        source_url: payload.source.url,
        source_name: payload.source.name ?? null,
        author_handle: payload.source.author_handle ?? null,
        content_hash: payload.source.content_hash ?? null,
        last_seen_at: now,
      },
      { onConflict: 'source_type,source_key' },
    )

  if (sourceError) {
    console.error('Candidate source upsert failed:', sourceError)
    return NextResponse.json({ error: 'Candidate source upsert failed' }, { status: 500 })
  }

  return NextResponse.json({ id: candidateId, status: existing ? 'updated' : 'created' })
}
