'use client'

import { CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Event } from '@/lib/database.types'
import { ExternalLink, MapPin, Calendar, User, CircleDollarSign } from 'lucide-react'
import Image from 'next/image'
import { trackEventClick } from '@/lib/gtag'
import { handleAddToCalendar } from '@/lib/calendar-utils'

interface EventCardProps {
  event: Event
}

export function EventCard({ event }: EventCardProps) {
  const dateParts = (dateString: string) => {
    const [year, month, day] = dateString.split('-').map(Number)
    return { year, month, day }
  }

  const formatDateRange = (start: string, end: string) => {
    const startDate = dateParts(start)
    const endDate = dateParts(end)
    const formattedStart = `${startDate.year}/${startDate.month}/${startDate.day}`

    if (start === end) {
      return formattedStart
    }

    const formattedEnd = startDate.year === endDate.year
      ? `${endDate.month}/${endDate.day}`
      : `${endDate.year}/${endDate.month}/${endDate.day}`

    return `${formattedStart}〜${formattedEnd}`
  }

  const today = new Date()
  const todayKey = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, '0'),
    String(today.getDate()).padStart(2, '0'),
  ].join('-')

  const isOngoing = () => {
    return event.start_date <= todayKey && event.end_date >= todayKey
  }

  const isUpcoming = () => {
    return todayKey < event.start_date
  }

  const getStatusBadge = () => {
    if (isOngoing()) {
      return (
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium border border-foreground text-foreground">
          開催中
        </span>
      )
    } else if (isUpcoming()) {
      return (
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium border border-border text-muted-foreground">
          開催予定
        </span>
      )
    } else {
      return (
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium border border-border text-muted-foreground">
          終了済み
        </span>
      )
    }
  }

  return (
    <article className="h-full border border-border flex flex-col transition-colors hover:border-foreground/40">
      {/* Card Header */}
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start gap-2">
          <h3 className="text-base font-semibold line-clamp-2 flex-1">
            {event.title}
          </h3>
          {getStatusBadge()}
        </div>

        {event.host_name && (
          <div className="flex items-center text-sm text-muted-foreground">
            <User className="w-4 h-4 mr-1" />
            {event.host_name}
          </div>
        )}
      </CardHeader>

      {/* Card Body */}
      <CardContent className="flex-1 flex flex-col">
        <div className="space-y-3 flex-1">
          {/* Date */}
          <div className="flex items-center text-sm text-muted-foreground">
            <Calendar className="w-4 h-4 mr-2" aria-hidden="true" />
            <time dateTime={event.start_date}>{formatDateRange(event.start_date, event.end_date)}</time>
          </div>

          {/* Venue and Location */}
          <div className="flex items-start text-sm text-muted-foreground">
            <MapPin className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-medium text-foreground">{event.venue}</div>
              <div className="text-xs">{event.prefecture}</div>
              {event.address && (
                <div className="text-xs">{event.address}</div>
              )}
            </div>
          </div>

          {/* Price */}
          {event.price && (
            <div className="flex items-center text-sm text-muted-foreground">
              <CircleDollarSign className="w-4 h-4 mr-2" />
              {event.price}
            </div>
          )}

          {/* Notes */}
          {event.notes && (
            <div className="text-sm text-muted-foreground line-clamp-2">
              {event.notes}
            </div>
          )}
        </div>

        {/* Card Footer - Fixed at bottom */}
        <div className="mt-auto pt-4 space-y-3">
          {/* Social Links + Calendar */}
          <div className="flex justify-between items-center">
            {/* SNS Icons - Left side */}
            <div className="flex flex-wrap gap-2">
              {event.x_url && (
                <Button
                  variant="outline"
                  size="sm"
                  asChild
                  className="text-xs"
                >
                  <a
                    href={event.x_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center"
                    aria-label={`Xの告知を見る: ${event.title}`}
                    onClick={() => trackEventClick(event.id, event.title, 'sns')}
                  >
                    <Image
                      src="/images/logo-black.png"
                      alt="X"
                      width={16}
                      height={16}
                    />
                  </a>
                </Button>
              )}

              {event.ig_url && (
                <Button
                  variant="outline"
                  size="sm"
                  asChild
                  className="text-xs"
                >
                  <a
                    href={event.ig_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center"
                    aria-label={`Instagramの告知を見る: ${event.title}`}
                    onClick={() => trackEventClick(event.id, event.title, 'sns')}
                  >
                    <Image
                      src="/images/Instagram_Glyph_Black.png"
                      alt="Instagram"
                      width={16}
                      height={16}
                    />
                  </a>
                </Button>
              )}

              {event.threads_url && (
                <Button
                  variant="outline"
                  size="sm"
                  asChild
                  className="text-xs"
                >
                  <a
                    href={event.threads_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center"
                    aria-label={`Threadsの告知を見る: ${event.title}`}
                    onClick={() => trackEventClick(event.id, event.title, 'sns')}
                  >
                    <Image
                      src="/images/threads-logo-black-01.png"
                      alt="Threads"
                      width={16}
                      height={16}
                    />
                  </a>
                </Button>
              )}
            </div>

            {/* Calendar Icon - Right side */}
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              aria-label={`カレンダーに追加: ${event.title}`}
              title="カレンダーに追加"
              onClick={() => {
                handleAddToCalendar(event)
                trackEventClick(event.id, event.title, 'calendar')
              }}
            >
              <Image
                src="/images/calendar.png"
                alt="カレンダーに追加"
                width={16}
                height={16}
              />
            </Button>
          </div>

          {/* Main Announce Link */}
          <Button
            asChild
            className="w-full"
            variant="default"
          >
            <a
              href={event.announce_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center"
              aria-label={`詳細を見る: ${event.title}`}
              onClick={() => trackEventClick(event.id, event.title, 'announce')}
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              詳細を見る
            </a>
          </Button>
        </div>
      </CardContent>
    </article>
  )
}
