'use client'

import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Event } from '@/lib/database.types'
import { ExternalLink, MapPin, Calendar, User, CircleDollarSign } from 'lucide-react'
import Image from 'next/image'

interface EventCardProps {
  event: Event
}

export function EventCard({ event }: EventCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
    })
  }

  const formatDateRange = (start: string, end: string) => {
    if (start === end) {
      return formatDate(start)
    }
    return `${formatDate(start)} - ${formatDate(end)}`
  }

  const isOngoing = () => {
    const today = new Date()
    const startDate = new Date(event.start_date)
    const endDate = new Date(event.end_date)
    return today >= startDate && today <= endDate
  }

  const isUpcoming = () => {
    const today = new Date()
    const startDate = new Date(event.start_date)
    return today < startDate
  }

  const getStatusBadge = () => {
    if (isOngoing()) {
      return (
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
          開催中
        </span>
      )
    } else if (isUpcoming()) {
      return (
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
          開催予定
        </span>
      )
    } else {
      return (
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
          終了済み
        </span>
      )
    }
  }

  return (
    <Card className="h-full hover:shadow-lg transition-shadow duration-300 flex flex-col">
      {/* Card Header */}
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start">
          <h3 className="text-lg font-semibold line-clamp-2 flex-1">
            {event.title}
          </h3>
          {getStatusBadge()}
        </div>
        
        {event.host_name && (
          <div className="flex items-center text-sm text-gray-600">
            <User className="w-4 h-4 mr-1" />
            {event.host_name}
          </div>
        )}
      </CardHeader>
      
      {/* Card Body */}
      <CardContent className="flex-1 flex flex-col">
        <div className="space-y-3 flex-1">
          {/* Date */}
          <div className="flex items-center text-sm text-gray-600">
            <Calendar className="w-4 h-4 mr-2" />
            {formatDateRange(event.start_date, event.end_date)}
          </div>

          {/* Venue and Location */}
          <div className="flex items-start text-sm text-gray-600">
            <MapPin className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-medium">{event.venue}</div>
              <div className="text-xs">{event.prefecture}</div>
              {event.address && (
                <div className="text-xs text-gray-500">{event.address}</div>
              )}
            </div>
          </div>

          {/* Price */}
          {event.price && (
            <div className="flex items-center text-sm text-gray-600">
              <CircleDollarSign className="w-4 h-4 mr-2" />
              {event.price}
            </div>
          )}

          {/* Notes */}
          {event.notes && (
            <div className="text-sm text-gray-600 line-clamp-2">
              {event.notes}
            </div>
          )}
        </div>

        {/* Card Footer - Fixed at bottom */}
        <div className="mt-auto pt-4 space-y-3">
          {/* Social Links */}
          {(event.x_url || event.ig_url || event.threads_url) && (
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
          )}

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
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              詳細を見る
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}