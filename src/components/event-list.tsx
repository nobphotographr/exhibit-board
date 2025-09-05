'use client'

import { useState, useEffect, useCallback } from 'react'
import { Event } from '@/lib/database.types'
import { EventCard } from './event-card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PREFECTURES, FILTER_RANGES } from '@/lib/constants'
type FilterRange = 'upcoming' | 'thisMonth' | 'next30'
import { Loader2, RefreshCw } from 'lucide-react'
import { trackFilterUsage } from '@/lib/gtag'

interface EventListProps {
  initialEvents?: Event[]
}

export function EventList({ initialEvents = [] }: EventListProps) {
  const [events, setEvents] = useState<Event[]>(initialEvents)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Filter states
  const [selectedRange, setSelectedRange] = useState<FilterRange | 'all'>('upcoming')
  const [selectedPrefecture, setSelectedPrefecture] = useState<string>('all')

  const fetchEvents = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams()
      if (selectedRange && selectedRange !== 'all') params.append('range', selectedRange)
      if (selectedPrefecture && selectedPrefecture !== 'all') params.append('prefecture', selectedPrefecture)

      const response = await fetch(`/api/events?${params.toString()}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch events')
      }

      const data = await response.json()
      setEvents(data)
    } catch (err) {
      console.error('Error fetching events:', err)
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }, [selectedRange, selectedPrefecture])

  // Fetch events when filters change
  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  const clearFilters = () => {
    setSelectedRange('upcoming')
    setSelectedPrefecture('all')
  }

  const hasActiveFilters = selectedRange !== 'upcoming' || selectedPrefecture !== 'all'

  return (
    <div className="space-y-6">
      {/* Filter Controls */}
      <Card>
        <CardHeader>
          <CardTitle>フィルタ</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Date Range Filter */}
            <div className="flex-1">
              <Select 
                value={selectedRange} 
                onValueChange={(value) => setSelectedRange(value as FilterRange | 'all')}
              >
                <SelectTrigger>
                  <SelectValue placeholder="期間を選択" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem 
                    value="all"
                    onSelect={() => trackFilterUsage('range', 'all')}
                  >
                    すべての期間
                  </SelectItem>
                  {FILTER_RANGES.map((range) => (
                    <SelectItem 
                      key={range.value} 
                      value={range.value}
                      onSelect={() => trackFilterUsage('range', range.value)}
                    >
                      {range.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Prefecture Filter */}
            <div className="flex-1">
              <Select 
                value={selectedPrefecture} 
                onValueChange={setSelectedPrefecture}
              >
                <SelectTrigger>
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

            {/* Control Buttons */}
            <div className="flex gap-2">
              {hasActiveFilters && (
                <Button 
                  variant="outline" 
                  onClick={clearFilters}
                  disabled={loading}
                >
                  クリア
                </Button>
              )}
              
              <Button 
                variant="outline" 
                size="icon"
                onClick={fetchEvents}
                disabled={loading}
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
            <div className="mt-3 flex flex-wrap gap-2">
              {selectedRange && (
                <span className="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                  {FILTER_RANGES.find(r => r.value === selectedRange)?.label}
                </span>
              )}
              {selectedPrefecture && (
                <span className="inline-flex items-center px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">
                  {selectedPrefecture}
                </span>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-600 text-sm">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {loading && events.length === 0 && (
        <div className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      )}

      {/* Events Grid */}
      {!loading && events.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <p className="text-gray-500">
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
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Results Count */}
          <div className="text-sm text-gray-600">
            {loading ? (
              '読み込み中...'
            ) : (
              `${events.length}件の展示${hasActiveFilters ? '（フィルタ適用済み）' : ''}`
            )}
          </div>

          {/* Events Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" style={{gridAutoRows: '1fr'}}>
            {events.map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}