'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { Event } from '@/lib/database.types'
import { EventCard } from './event-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PREFECTURES, FILTER_RANGES, VENUE_TYPES } from '@/lib/constants'
type FilterRange = 'upcoming' | 'ongoing' | 'thisWeek' | 'thisMonth'
type VenueType = 'all' | 'major' | 'independent' | 'festival'
import { Loader2, RefreshCw, Search, ChevronDown } from 'lucide-react'
import { trackFilterUsage } from '@/lib/gtag'

const PAGE_SIZE = 24

interface EventListProps {
  initialEvents?: Event[]
}

export function EventList({ initialEvents = [] }: EventListProps) {
  const [events, setEvents] = useState<Event[]>(initialEvents)
  const [loading, setLoading] = useState(initialEvents.length === 0)
  const [error, setError] = useState<string | null>(null)

  const [selectedRange, setSelectedRange] = useState<FilterRange | 'all'>('upcoming')
  const [selectedPrefecture, setSelectedPrefecture] = useState<string>('all')
  const [selectedVenueType, setSelectedVenueType] = useState<VenueType>('all')
  const [query, setQuery] = useState('')
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)

  const fetchEvents = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams()
      if (selectedRange && selectedRange !== 'all') params.append('range', selectedRange)
      if (selectedPrefecture && selectedPrefecture !== 'all') params.append('prefecture', selectedPrefecture)
      if (selectedVenueType && selectedVenueType !== 'all') params.append('venueType', selectedVenueType)

      const response = await fetch(`/api/events?${params.toString()}`)

      if (!response.ok) {
        throw new Error('展示情報を取得できませんでした。時間をおいて再度お試しください。')
      }

      const data = await response.json()
      setEvents(data)
    } catch (err) {
      console.error('Error fetching events:', err)
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }, [selectedRange, selectedPrefecture, selectedVenueType])

  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  const clearFilters = () => {
    setSelectedRange('upcoming')
    setSelectedPrefecture('all')
    setSelectedVenueType('all')
    setQuery('')
  }

  const hasActiveFilters = selectedRange !== 'upcoming' || selectedPrefecture !== 'all' || selectedVenueType !== 'all' || query.trim() !== ''

  useEffect(() => {
    setVisibleCount(PAGE_SIZE)
  }, [selectedRange, selectedPrefecture, selectedVenueType, query])

  const filteredEvents = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('ja')
    const today = new Date()
    const todayKey = [
      today.getFullYear(),
      String(today.getMonth() + 1).padStart(2, '0'),
      String(today.getDate()).padStart(2, '0'),
    ].join('-')

    const matches = normalizedQuery
      ? events.filter((event) => [
          event.title,
          event.host_name,
          event.venue,
          event.prefecture,
          event.address,
          event.notes,
        ].some((value) => value?.toLocaleLowerCase('ja').includes(normalizedQuery)))
      : [...events]

    const statusRank = (event: Event) => {
      if (event.start_date <= todayKey && event.end_date >= todayKey) return 0
      if (event.start_date > todayKey) return 1
      return 2
    }

    return matches.sort((a, b) => {
      const rankDifference = statusRank(a) - statusRank(b)
      if (rankDifference !== 0) return rankDifference

      const dateComparison = statusRank(a) === 0
        ? a.end_date.localeCompare(b.end_date)
        : a.start_date.localeCompare(b.start_date)

      return dateComparison || a.title.localeCompare(b.title, 'ja')
    })
  }, [events, query])

  const displayedEvents = filteredEvents.slice(0, visibleCount)

  return (
    <div className="space-y-8">
      {/* Filter Controls */}
      <div className="border border-border p-6">
        <div className="flex items-center justify-between gap-4 mb-5">
          <h3 className="text-sm font-medium">展示を絞り込む</h3>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} disabled={loading}>
              条件をリセット
            </Button>
          )}
        </div>

        <div className="mb-4">
          <label htmlFor="event-search" className="block text-sm text-muted-foreground mb-2">
            キーワード
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input
              id="event-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="展示名・作家名・会場名で検索"
              className="pl-9"
            />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          {/* Date Range Filter */}
          <div className="flex-1">
            <label htmlFor="range-filter" className="block text-sm text-muted-foreground mb-2">期間</label>
            <Select
              value={selectedRange}
              onValueChange={(value) => {
                setSelectedRange(value as FilterRange | 'all')
                trackFilterUsage('range', value)
              }}
            >
              <SelectTrigger id="range-filter">
                <SelectValue placeholder="期間を選択" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  value="all"
                >
                  すべての期間
                </SelectItem>
                {FILTER_RANGES.map((range) => (
                  <SelectItem
                    key={range.value}
                    value={range.value}
                  >
                    {range.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Prefecture Filter */}
          <div className="flex-1">
            <label htmlFor="prefecture-filter" className="block text-sm text-muted-foreground mb-2">都道府県</label>
            <Select
              value={selectedPrefecture}
              onValueChange={(value) => {
                setSelectedPrefecture(value)
                trackFilterUsage('prefecture', value)
              }}
            >
              <SelectTrigger id="prefecture-filter">
                <SelectValue placeholder="都道府県を選択" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">すべての地域</SelectItem>
                {PREFECTURES.map((prefecture) => (
                  <SelectItem key={prefecture} value={prefecture}>
                    {prefecture}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Exhibition Type Filter */}
          <div className="flex-1">
            <label htmlFor="venue-type-filter" className="block text-sm text-muted-foreground mb-2">展示タイプ</label>
            <Select
              value={selectedVenueType}
              onValueChange={(value) => {
                setSelectedVenueType(value as VenueType)
                trackFilterUsage('event_type', value)
              }}
            >
              <SelectTrigger id="venue-type-filter">
                <SelectValue placeholder="展示タイプを選択" />
              </SelectTrigger>
              <SelectContent>
                {VENUE_TYPES.map((venueType) => (
                  <SelectItem key={venueType.value} value={venueType.value}>
                    {venueType.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Control Buttons */}
          <div className="flex gap-2 items-end">
            <Button
              variant="outline"
              size="icon"
              onClick={fetchEvents}
              disabled={loading}
              aria-label="展示情報を再読み込み"
              title="展示情報を再読み込み"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Active Filters Display */}
        {hasActiveFilters && (
          <div className="mt-4 flex flex-wrap gap-2">
            {query.trim() && (
              <span className="inline-flex items-center px-2 py-1 text-xs border border-border text-muted-foreground">
                「{query.trim()}」
              </span>
            )}
            {selectedRange !== 'upcoming' && (
              <span className="inline-flex items-center px-2 py-1 text-xs border border-border text-muted-foreground">
                {selectedRange === 'all' ? 'すべての期間' : FILTER_RANGES.find(r => r.value === selectedRange)?.label}
              </span>
            )}
            {selectedPrefecture && selectedPrefecture !== 'all' && (
              <span className="inline-flex items-center px-2 py-1 text-xs border border-border text-muted-foreground">
                {selectedPrefecture}
              </span>
            )}
            {selectedVenueType && selectedVenueType !== 'all' && (
              <span className="inline-flex items-center px-2 py-1 text-xs border border-border text-muted-foreground">
                {VENUE_TYPES.find(v => v.value === selectedVenueType)?.label}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="border border-destructive p-6">
          <p className="text-destructive text-sm">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && events.length === 0 && (
        <div className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      )}

      {/* Events Grid */}
      {!loading && filteredEvents.length === 0 ? (
        <div className="border border-border p-6">
          <div className="text-center py-8">
            <p className="text-muted-foreground">
              {hasActiveFilters
                ? '条件に一致する展示が見つかりませんでした。'
                : '展示情報がありません。'
              }
            </p>
            {hasActiveFilters && (
              <Button
                variant="outline"
                onClick={clearFilters}
                className="mt-4"
              >
                フィルタをクリア
              </Button>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* Results Count */}
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground" aria-live="polite">
            {loading ? (
              '読み込み中...'
            ) : (
              <>
                <span>{filteredEvents.length}件の展示{hasActiveFilters ? '（条件適用済み）' : ''}</span>
                <span>{Math.min(displayedEvents.length, filteredEvents.length)}件を表示中</span>
              </>
            )}
          </div>

          {/* Events Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {displayedEvents.map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>

          {visibleCount < filteredEvents.length && (
            <div className="flex justify-center pt-2">
              <Button
                variant="outline"
                onClick={() => setVisibleCount((count) => count + PAGE_SIZE)}
                className="min-w-48"
              >
                <ChevronDown className="w-4 h-4 mr-2" aria-hidden="true" />
                さらに表示
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
