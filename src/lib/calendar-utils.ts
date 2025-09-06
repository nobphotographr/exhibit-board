import { Event } from './database.types'

/**
 * Google カレンダーに予定を追加するURL を生成
 * @param event 展示イベント情報
 * @returns Google カレンダーの追加URL
 */
export const createGoogleCalendarUrl = (event: Event): string => {
  // 日付をGoogleカレンダー形式に変換 (YYYYMMDD)
  const startDate = event.start_date.replace(/-/g, '')
  
  // 終日イベントとして設定 (終了日は翌日)
  const endDatePlusOne = new Date(event.end_date + 'T00:00:00')
  endDatePlusOne.setDate(endDatePlusOne.getDate() + 1)
  const formattedEndDate = endDatePlusOne.toISOString().split('T')[0].replace(/-/g, '')
  
  // 予定の詳細情報を構築
  const title = event.title
  const location = event.address || event.venue
  
  let details = ''
  if (event.venue) {
    details += `会場: ${event.venue}\n`
  }
  if (event.host_name) {
    details += `主催: ${event.host_name}\n`
  }
  if (event.price) {
    details += `料金: ${event.price}\n`
  }
  if (event.notes) {
    details += `\n${event.notes}\n`
  }
  details += `\n詳細情報: ${event.announce_url}`
  
  // URLパラメータを構築
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: title,
    dates: `${startDate}/${formattedEndDate}`,
    details: details,
    location: location,
  })
  
  return `https://calendar.google.com/calendar/render?${params.toString()}`
}

/**
 * カレンダー追加ボタンのクリックハンドラ
 * @param event 展示イベント情報
 */
export const handleAddToCalendar = (event: Event) => {
  const calendarUrl = createGoogleCalendarUrl(event)
  window.open(calendarUrl, '_blank', 'noopener,noreferrer')
}