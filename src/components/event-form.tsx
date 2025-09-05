'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PREFECTURES } from '@/lib/constants'

// Validation schema based on requirements
const eventSchema = z.object({
  title: z.string().min(1, '展示タイトルは必須です').max(100, 'タイトルは100文字以下で入力してください'),
  host_name: z.string().max(50, '主催者名は50文字以下で入力してください').optional(),
  x_url: z.string().url('有効なURLを入力してください').optional().or(z.literal('')),
  ig_url: z.string().url('有効なURLを入力してください').optional().or(z.literal('')),
  threads_url: z.string().url('有効なURLを入力してください').optional().or(z.literal('')),
  venue: z.string().min(1, '会場名は必須です').max(100, '会場名は100文字以下で入力してください'),
  address: z.string().max(200, '住所は200文字以下で入力してください').optional(),
  prefecture: z.enum(PREFECTURES, { required_error: '都道府県を選択してください' }),
  price: z.string().max(50, '料金情報は50文字以下で入力してください').optional(),
  start_date: z.string().min(1, '開始日は必須です'),
  end_date: z.string().min(1, '終了日は必須です'),
  announce_url: z.string().url('有効なURLを入力してください').min(1, '告知URLは必須です'),
  notes: z.string().max(500, 'メモは500文字以下で入力してください').optional(),
}).refine((data) => {
  // Validate date range
  if (data.start_date && data.end_date) {
    return new Date(data.end_date) >= new Date(data.start_date)
  }
  return true
}, {
  message: '終了日は開始日以降を指定してください',
  path: ['end_date'],
})

type EventFormData = z.infer<typeof eventSchema>

interface EventFormProps {
  onSuccess?: (data: { id: string }) => void
}

export function EventForm({ onSuccess }: EventFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)

  const form = useForm<EventFormData>({
    resolver: zodResolver(eventSchema),
    defaultValues: {
      title: '',
      host_name: '',
      x_url: '',
      ig_url: '',
      threads_url: '',
      venue: '',
      address: '',
      prefecture: undefined,
      price: '',
      start_date: '',
      end_date: '',
      announce_url: '',
      notes: '',
    },
  })

  const onSubmit = async (data: EventFormData) => {
    setIsSubmitting(true)
    setSubmitError(null)
    setSubmitSuccess(null)

    try {
      // Get reCAPTCHA token (placeholder - will implement later)
      const captcha_token = 'placeholder_token'

      const response = await fetch('/api/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...data,
          captcha_token,
        }),
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.message || 'Failed to submit event')
      }

      setSubmitSuccess('イベントを登録しました！')
      form.reset()
      onSuccess?.(result)

    } catch (error) {
      console.error('Form submission error:', error)
      setSubmitError(error instanceof Error ? error.message : 'An error occurred')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>展示情報登録</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">基本情報</h3>
              
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>展示タイトル *</FormLabel>
                    <FormControl>
                      <Input placeholder="例: 個展「春の記憶」" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="host_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>主催者名</FormLabel>
                    <FormControl>
                      <Input placeholder="例: 山田太郎" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="announce_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>告知URL *</FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="https://x.com/username/status/..." 
                        {...field} 
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Social Media Links */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">SNSリンク（任意）</h3>
              
              <FormField
                control={form.control}
                name="x_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>X (Twitter) URL</FormLabel>
                    <FormControl>
                      <Input placeholder="https://x.com/username" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="ig_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Instagram URL</FormLabel>
                    <FormControl>
                      <Input placeholder="https://instagram.com/username" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="threads_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Threads URL</FormLabel>
                    <FormControl>
                      <Input placeholder="https://threads.net/@username" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Venue Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">会場情報</h3>
              
              <FormField
                control={form.control}
                name="venue"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>会場名 *</FormLabel>
                    <FormControl>
                      <Input placeholder="例: ○○ギャラリー" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="prefecture"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>都道府県 *</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="都道府県を選択" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {PREFECTURES.map((prefecture) => (
                          <SelectItem key={prefecture} value={prefecture}>
                            {prefecture}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>住所</FormLabel>
                    <FormControl>
                      <Input placeholder="例: 渋谷区○○1-2-3" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Event Details */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">開催情報</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="start_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>開始日 *</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="end_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>終了日 *</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="price"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>料金</FormLabel>
                    <FormControl>
                      <Input placeholder="例: 無料、500円、学生300円・一般500円" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>一言メッセージ</FormLabel>
                    <FormControl>
                      <Textarea 
                        placeholder="例: 新作油彩画20点を展示します。お気軽にお立ち寄りください！"
                        className="min-h-[100px]"
                        {...field} 
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Error/Success Messages */}
            {submitError && (
              <div className="p-4 text-sm text-red-600 bg-red-50 rounded-md">
                {submitError}
              </div>
            )}

            {submitSuccess && (
              <div className="p-4 text-sm text-green-600 bg-green-50 rounded-md">
                {submitSuccess}
              </div>
            )}

            {/* Submit Button */}
            <Button 
              type="submit" 
              className="w-full" 
              disabled={isSubmitting}
            >
              {isSubmitting ? '登録中...' : '展示情報を登録'}
            </Button>

            <p className="text-sm text-gray-600 text-center">
              登録された情報は公開されます。内容に間違いがないかご確認ください。
            </p>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}