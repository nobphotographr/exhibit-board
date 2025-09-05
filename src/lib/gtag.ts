// Google Analytics 4 Configuration
export const GA_TRACKING_ID = process.env.NEXT_PUBLIC_GA_ID

// Check if GA_TRACKING_ID exists
export const isProduction = process.env.NODE_ENV === 'production'
export const isGAEnabled = isProduction && GA_TRACKING_ID

// https://developers.google.com/analytics/devguides/collection/gtagjs/pages
export const pageview = (url: URL) => {
  if (!isGAEnabled) return
  
  window.gtag('config', GA_TRACKING_ID, {
    page_location: url.href,
    page_title: document.title,
  })
}

// https://developers.google.com/analytics/devguides/collection/gtagjs/events
export const event = (
  action: string, 
  {
    event_category,
    event_label,
    value,
  }: {
    event_category?: string
    event_label?: string
    value?: number
  }
) => {
  if (!isGAEnabled) return

  window.gtag('event', action, {
    event_category,
    event_label,
    value,
  })
}

// Custom events for Exhibit Board
export const trackEventView = (eventId: string, eventTitle: string) => {
  event('view_event', {
    event_category: 'Event',
    event_label: `${eventId}: ${eventTitle}`,
  })
}

export const trackEventClick = (eventId: string, eventTitle: string, linkType: 'announce' | 'sns') => {
  event('click_event_link', {
    event_category: 'Event',
    event_label: `${linkType}: ${eventId}: ${eventTitle}`,
  })
}

export const trackEventSubmission = (eventTitle: string) => {
  event('submit_event', {
    event_category: 'Form',
    event_label: eventTitle,
  })
}

export const trackFilterUsage = (filterType: string, filterValue: string) => {
  event('use_filter', {
    event_category: 'Filter',
    event_label: `${filterType}: ${filterValue}`,
  })
}